"""Data models for Multipass VM, image, network, alias, and snapshot state."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum


class VmState(Enum):
    """Lifecycle states Multipass can report for a VM."""

    RUNNING = "Running"
    STOPPED = "Stopped"
    DELETED = "Deleted"
    SUSPENDED = "Suspended"
    STARTING = "Starting"
    RESTARTING = "Restarting"
    UNKNOWN = "Unknown"

    @classmethod
    def _missing_(cls, value: object) -> VmState:
        return cls.UNKNOWN


@dataclass
class VmInfo:
    """Detailed state of a single VM as reported by Multipass."""

    name: str
    state: VmState
    ipv4: list[str]
    image: str
    image_hash: str
    cpus: int
    memory_total: str
    memory_used: str
    disk_total: str
    disk_used: str
    mounts: dict[str, str]

    @classmethod
    def from_info_json(cls, data: dict, name: str) -> VmInfo:
        """Build a VmInfo from the JSON payload of `multipass info --format json`."""
        vm = data["info"][name]
        disks = vm.get("disks", {})
        first_disk = next(iter(disks.values()), {})
        memory = vm.get("memory", {})
        return cls(
            name=name,
            state=VmState(vm.get("state", "Unknown")),
            ipv4=vm.get("ipv4", []),
            image=vm.get("image_release", ""),
            image_hash=vm.get("image_hash", ""),
            cpus=int(vm.get("cpu_count") or 0),
            memory_total=str(memory.get("total", 0)),
            memory_used=str(memory.get("used", 0)),
            disk_total=str(first_disk.get("total", "0")),
            disk_used=str(first_disk.get("used", "0")),
            mounts={
                target: mount_data.get("source_path", "")
                for target, mount_data in vm.get("mounts", {}).items()
            },
        )

    @classmethod
    def from_list_json(cls, data: dict) -> list[VmInfo]:
        """Build VmInfo objects from the JSON payload of `multipass list`."""
        return [
            cls(
                name=item["name"],
                state=VmState(item.get("state", "Unknown")),
                ipv4=item.get("ipv4", []),
                image=item.get("release", ""),
                image_hash="",
                cpus=0,
                memory_total="",
                memory_used="",
                disk_total="",
                disk_used="",
                mounts={},
            )
            for item in data.get("list", [])
        ]


@dataclass
class ImageInfo:
    """A VM image available from a Multipass remote."""

    aliases: list[str]
    os: str
    release: str
    remote: str
    version: str

    @classmethod
    def from_find_json(cls, data: dict) -> list[ImageInfo]:
        """Build ImageInfo objects from the JSON payload of `multipass find`."""
        return [
            cls(
                aliases=img.get("aliases", []),
                os=img.get("os", ""),
                release=img.get("release", ""),
                remote=img.get("remote", ""),
                version=img.get("version", ""),
            )
            for img in data.get("images", {}).values()
        ]


@dataclass
class NetworkInfo:
    """A host network that Multipass can attach VMs to."""

    name: str
    type: str
    description: str

    @classmethod
    def from_networks_json(cls, data: dict) -> list[NetworkInfo]:
        """Build NetworkInfo objects from the JSON payload of `multipass networks`."""
        return [
            cls(
                name=item["name"],
                type=item.get("type", ""),
                description=item.get("description", ""),
            )
            for item in data.get("list", [])
        ]


@dataclass
class VersionInfo:
    """Client and daemon versions reported by `multipass version`."""

    multipass: str
    multipassd: str

    @classmethod
    def from_json(cls, data: dict) -> VersionInfo:
        """Build a VersionInfo from the JSON payload of `multipass version`."""
        return cls(
            multipass=data.get("multipass", ""),
            multipassd=data.get("multipassd", ""),
        )


@dataclass
class AliasInfo:
    """A command alias defined in Multipass."""

    alias: str
    instance: str
    command: str
    working_directory: str

    @classmethod
    def from_aliases_json(cls, data: dict) -> list[AliasInfo]:
        """Build AliasInfo objects from the JSON payload of `multipass aliases`."""
        return [
            cls(
                alias=item["alias"],
                instance=item.get("instance", ""),
                command=item.get("command", ""),
                working_directory=item.get("working-directory", ""),
            )
            for item in data.get("aliases", [])
        ]


@dataclass
class VmConfig:
    """Reusable VM launch configuration."""

    name: str | None = None
    image: str | None = None
    cpus: int = 1
    memory: str = "1G"
    disk: str = "5G"
    cloud_init: str | None = None
    cloud_init_config: dict | str | None = None


@dataclass
class CloudInitConfig:
    """Structured cloud-init configuration.

    Example::

        CloudInitConfig(
            packages=["git", "curl"],
            ssh_authorized_keys=["ssh-ed25519 AAAA..."],
        )
    """

    packages: list[str] | None = None
    ssh_authorized_keys: list[str] | None = None
    runcmd: list[list[str]] | None = None
    write_files: list[dict] | None = None
    users: list[dict] | None = None

    def to_dict(self) -> dict:
        """Return the configuration as a dict, omitting fields left unset."""
        result: dict = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if value is not None:
                result[f.name] = value
        return result


@dataclass
class SnapshotInfo:
    """A snapshot taken from a VM instance."""

    name: str
    comment: str
    created: str
    parent: str | None
    instance: str

    @classmethod
    def from_snapshots_json(cls, data: dict) -> list[SnapshotInfo]:
        """Build SnapshotInfo objects from the `multipass snapshot list` JSON."""
        result = []
        for instance_name, snapshots in data.get("info", {}).items():
            for snap_name, snap_data in snapshots.items():
                result.append(
                    cls(
                        name=snap_name,
                        comment=snap_data.get("comment", ""),
                        created=snap_data.get("created", ""),
                        parent=snap_data.get("parent") or None,
                        instance=instance_name,
                    )
                )
        return result
