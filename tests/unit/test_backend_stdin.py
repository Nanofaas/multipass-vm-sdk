from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from multipass._backend import SubprocessBackend


def test_subprocess_backend_never_inherits_stdin() -> None:
    """Verify the backend closes stdin instead of inheriting the parent pty.

    Multipass exec forwards stdin to the remote command; an inherited pty
    with no writer makes the session hang forever. The backend is
    non-interactive by design, so stdin must be closed explicitly.
    """
    backend = SubprocessBackend()
    completed = MagicMock(returncode=0, stdout="", stderr="")
    with patch("multipass._backend.subprocess.run", return_value=completed) as mock_run:
        backend.run(["multipass", "exec", "vm", "--", "true"])

    assert mock_run.call_args.kwargs.get("stdin") == subprocess.DEVNULL
