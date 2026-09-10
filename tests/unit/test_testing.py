"""The public `multipass.testing` surface the README tells consumers to use."""

import pytest

from multipass import MultipassClient, MultipassCommandError
from multipass._backend import CommandResult
from multipass._backend import FakeBackend as InternalFakeBackend
from multipass.testing import FakeBackend


def test_fake_backend_is_the_same_object_as_the_internal_one():
    """The re-export would silently break consumers if it ever diverged."""
    assert FakeBackend is InternalFakeBackend


def test_fake_backend_drives_the_client_without_multipass():
    backend = FakeBackend()
    backend.set_default(
        CommandResult(args=[], returncode=0, stdout='{"list": []}', stderr="")
    )
    client = MultipassClient(backend=backend)

    assert client.list_vms() == []


def test_fake_backend_surfaces_command_failures():
    """A non-zero exit becomes the SDK's own error type, not a bare return code."""
    backend = FakeBackend()
    backend.set_default(CommandResult(args=[], returncode=1, stdout="", stderr="boom"))
    client = MultipassClient(backend=backend)

    with pytest.raises(MultipassCommandError):
        client.list_vms()
