"""Testing helpers. Exposes FakeBackend for exercising the client without Multipass."""

from __future__ import annotations

from ._backend import FakeBackend

__all__ = ["FakeBackend"]
