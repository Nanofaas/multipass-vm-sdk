"""Public API for the Multipass SDK.

Exposes the client, VM handle, models, backends, and exceptions that make up
the supported surface of the package.
"""

from ._backend import CommandResult, FakeBackend, SubprocessBackend
from .client import MultipassClient
from .exceptions import (
    MultipassCommandError,
    MultipassError,
    MultipassNotInstalledError,
    MultipassTimeoutError,
    VmAlreadyRunningError,
    VmAlreadySuspendedError,
    VmNotFoundError,
    VmNotRunningError,
)
from .models import (
    AliasInfo,
    CloudInitConfig,
    ImageInfo,
    NetworkInfo,
    SnapshotInfo,
    VersionInfo,
    VmConfig,
    VmInfo,
    VmState,
)
from .utils import find_ssh_public_key
from .vm import MultipassVM

__all__ = [
    "AliasInfo",
    "CloudInitConfig",
    "CommandResult",
    "FakeBackend",
    "ImageInfo",
    "MultipassClient",
    "MultipassCommandError",
    "MultipassError",
    "MultipassNotInstalledError",
    "MultipassTimeoutError",
    "MultipassVM",
    "NetworkInfo",
    "SnapshotInfo",
    "SubprocessBackend",
    "VersionInfo",
    "VmAlreadyRunningError",
    "VmAlreadySuspendedError",
    "VmConfig",
    "VmInfo",
    "VmNotFoundError",
    "VmNotRunningError",
    "VmState",
    "find_ssh_public_key",
]
