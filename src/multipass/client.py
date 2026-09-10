"""High-level client for driving the multipass CLI."""

from __future__ import annotations

import contextlib
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml
from haikunator import Haikunator

from ._backend import CommandBackend, CommandResult, SubprocessBackend
from .exceptions import MultipassCommandError, VmNotFoundError
from .models import (
    AliasInfo,
    ImageInfo,
    NetworkInfo,
    VersionInfo,
    VmConfig,
    VmInfo,
    VmState,
)
from .vm import MultipassVM


def _check(result: CommandResult) -> None:
    if not result.success:
        raise MultipassCommandError(
            result.args, result.returncode, result.stdout, result.stderr
        )


class MultipassClient:
    """Synchronous client for the multipass CLI."""

    def __init__(
        self,
        cmd: str = "multipass",
        backend: CommandBackend | None = None,
    ) -> None:
        """Create a client. ``backend`` overrides how commands are executed."""
        self._cmd = cmd
        self._backend: CommandBackend = backend or SubprocessBackend()

    def _run(self, *args: str) -> CommandResult:
        result = self._backend.run([self._cmd, *args])
        _check(result)
        return result

    def _run_json(self, *args: str) -> dict:
        return json.loads(self._run(*args).stdout)

    def get_vm(self, name: str) -> MultipassVM:
        """Return a handle for the named VM to issue further operations on."""
        return MultipassVM(name, self._cmd, self._backend)

    def launch(
        self,
        name: str | VmConfig | None = None,
        image: str | None = None,
        *,
        cpus: int = 1,
        memory: str = "1G",
        disk: str = "5G",
        cloud_init: str | None = None,
        cloud_init_config: dict | str | None = None,
    ) -> MultipassVM:
        """Launch a new VM.

        Accepts either a VmConfig object or inline parameters::

            vm = client.launch("my-vm", cpus=4, memory="8G")
            vm = client.launch(VmConfig(name="my-vm", cpus=4, memory="8G"))
        """
        if isinstance(name, VmConfig):
            cfg = name
            name = cfg.name
            image = cfg.image
            cpus = cfg.cpus
            memory = cfg.memory
            disk = cfg.disk
            cloud_init = cfg.cloud_init
            cloud_init_config = cfg.cloud_init_config

        if name is None:
            name = Haikunator().haikunate(token_length=0)
        cmd = ["launch", "-n", name, "-c", str(cpus), "-m", memory, "-d", disk]
        if cloud_init:
            cmd += ["--cloud-init", cloud_init]
        if image and image != "ubuntu-lts":
            cmd.append(image)
        if cloud_init_config is not None:
            if isinstance(cloud_init_config, dict):
                content = "#cloud-config\n" + yaml.dump(
                    cloud_init_config, default_flow_style=False
                )
            else:
                content = cloud_init_config
            with tempfile.NamedTemporaryFile(
                dir=Path.home(), suffix=".yaml", delete=False, mode="w"
            ) as tmp:
                tmp.write(content)
                cloud_init_path = tmp.name
            try:
                self._run(*cmd, "--cloud-init", cloud_init_path)
            finally:
                Path(cloud_init_path).unlink(missing_ok=True)
        else:
            self._run(*cmd)
        return MultipassVM(name, self._cmd, self._backend)

    def launch_many(
        self,
        configs: list[VmConfig],
        *,
        max_workers: int | None = None,
    ) -> list[MultipassVM]:
        """Launch multiple VMs in parallel. Rolls back all on any failure."""
        if not configs:
            return []

        workers = max_workers if max_workers is not None else len(configs)
        created: list[MultipassVM] = []
        first_error: BaseException | None = None

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.launch, cfg): cfg for cfg in configs}

            for fut in as_completed(futures):
                if first_error is not None:
                    continue
                exc = fut.exception()
                if exc is not None:
                    first_error = exc
                    for pending in futures:
                        pending.cancel()
                else:
                    created.append(fut.result())

        if first_error is not None:
            with ThreadPoolExecutor(max_workers=max(len(created), 1)) as rollback:
                for rf in [rollback.submit(vm.delete) for vm in created]:
                    with contextlib.suppress(Exception):
                        rf.result()
            raise first_error

        return created

    def ensure_running(
        self,
        name: str,
        image: str | None = None,
        *,
        cpus: int = 1,
        memory: str = "1G",
        disk: str = "5G",
        cloud_init: str | None = None,
        cloud_init_config: dict | str | None = None,
    ) -> MultipassVM:
        """Ensure the named VM exists and is running.

        State machine:
        - Not found  → launch with provided parameters
        - Deleted    → purge *all* soft-deleted VMs (system-wide), then launch
        - Running    → no-op
        - Any other  → start (Stopped, Suspended, etc.)

        .. warning::
            When the VM is in DELETED state, ``multipass purge`` is called, which
            permanently removes **all** soft-deleted instances on the system — not
            only the target VM. Ensure no other instances in DELETED state need
            to be recovered before calling this method.

        Returns the ``MultipassVM`` object in all cases.
        """
        try:
            info = self.get_vm(name).info()
        except VmNotFoundError:
            return self.launch(
                name,
                image,
                cpus=cpus,
                memory=memory,
                disk=disk,
                cloud_init=cloud_init,
                cloud_init_config=cloud_init_config,
            )

        if info.state == VmState.RUNNING:
            return self.get_vm(name)

        if info.state == VmState.DELETED:
            self.purge()
            return self.launch(
                name,
                image,
                cpus=cpus,
                memory=memory,
                disk=disk,
                cloud_init=cloud_init,
                cloud_init_config=cloud_init_config,
            )

        # Stopped, Suspended, Starting, Restarting, Unknown
        self.get_vm(name).start()
        return self.get_vm(name)

    def list_vms(self) -> list[VmInfo]:
        """List all VMs known to Multipass."""
        return VmInfo.from_list_json(self._run_json("list", "--format", "json"))

    def find(self) -> list[ImageInfo]:
        """List the images available to launch."""
        return ImageInfo.from_find_json(self._run_json("find", "--format", "json"))

    def purge(self) -> None:
        """Permanently remove all deleted instances from the system."""
        self._run("purge")

    def networks(self) -> list[NetworkInfo]:
        """List the networks available on the host."""
        return NetworkInfo.from_networks_json(
            self._run_json("networks", "--format", "json")
        )

    def version(self) -> VersionInfo:
        """Return the installed Multipass version."""
        return VersionInfo.from_json(self._run_json("version", "--format", "json"))

    def get(self, key: str) -> str:
        """Read a Multipass configuration value by key."""
        return self._run("get", key).stdout.strip()

    def set(self, key: str, value: str) -> None:
        """Set a Multipass configuration key to a value."""
        self._run("set", f"{key}={value}")

    def aliases(self) -> list[AliasInfo]:
        """List the command aliases currently defined."""
        return AliasInfo.from_aliases_json(
            self._run_json("aliases", "--format", "json")
        )

    def alias(self, name: str, vm: str, command: str) -> None:
        """Define ``name`` as an alias for ``command`` running on ``vm``."""
        self._run("alias", f"{vm}:{command}", name)

    def unalias(self, name: str) -> None:
        """Remove the alias with the given name."""
        self._run("unalias", name)
