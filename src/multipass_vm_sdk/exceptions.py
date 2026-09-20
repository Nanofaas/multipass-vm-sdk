"""Exception hierarchy raised by the multipass-sdk."""


class MultipassError(Exception):
    """Base exception for all multipass-sdk errors."""


class MultipassCommandError(MultipassError):
    """Raised when the Multipass CLI exits with a non-zero status.

    Exposes the failed command, its exit code, and the captured streams so
    callers can inspect or re-raise the underlying failure.
    """

    def __init__(self, args: list[str], returncode: int, stdout: str, stderr: str):
        """Record the failed command, its exit code, and its captured output."""
        self.args_list = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(
            f"Command {args} failed with exit code {returncode}: {stderr or stdout}"
        )


class MultipassNotInstalledError(MultipassError):
    """Raised when the Multipass binary cannot be found on the host."""

    def __init__(self) -> None:
        """Explain how to install the missing Multipass binary."""
        super().__init__(
            "Multipass binary not found. Install from https://multipass.run"
        )


class VmNotFoundError(MultipassError):
    """Raised when a named VM does not exist."""

    def __init__(self, name: str) -> None:
        """Record the name of the VM that could not be found."""
        self.name = name
        super().__init__(f"VM '{name}' not found")


class VmAlreadyRunningError(MultipassError):
    """Raised when starting a VM that is already running."""

    def __init__(self, name: str) -> None:
        """Record the name of the VM that is already running."""
        self.name = name
        super().__init__(f"VM '{name}' is already running")


class VmNotRunningError(MultipassError):
    """Raised when an operation requires a VM that is not running."""

    def __init__(self, name: str) -> None:
        """Record the name of the VM that is not running."""
        self.name = name
        super().__init__(f"VM '{name}' is not running")


class VmAlreadySuspendedError(MultipassError):
    """Raised when suspending a VM that is already suspended."""

    def __init__(self, name: str) -> None:
        """Record the name of the VM that is already suspended."""
        self.name = name
        super().__init__(f"VM '{name}' is already suspended")


class MultipassTimeoutError(MultipassError):
    """Raised when a VM does not become ready within the allotted time."""

    def __init__(self, name: str, timeout: float) -> None:
        """Record the VM name and the timeout, in seconds, that elapsed."""
        self.name = name
        self.timeout = timeout
        super().__init__(f"VM '{name}' did not become ready within {timeout}s")
