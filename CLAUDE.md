# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

An unofficial Python SDK that wraps the Multipass CLI to manage Ubuntu VMs programmatically. Full coverage of every Multipass CLI command. Designed to be imported by other projects (e.g. nanofaas) — it has no dependencies on them.

## Setup

```bash
uv sync
```

Requires [uv](https://docs.astral.sh/uv/). Multipass itself is NOT required for unit tests.

The toolchain (ruff, basedpyright, bandit, pytest, pre-commit) lives in
`[dependency-groups].dev`, which a plain `uv sync` installs. It must stay there
and not move to `[project.optional-dependencies]`: extras are skipped by
`uv run`, so the basedpyright pre-commit hook — which runs `uv run --frozen
basedpyright` — would fail in CI with "Failed to spawn: basedpyright".

## Running Tests

```bash
# Unit tests only (no Multipass required)
uv run pytest tests/unit/ -v

# Single test
uv run pytest tests/unit/test_vm.py::test_exec_builds_command_from_list -v

# Integration tests (requires Multipass installed)
uv run pytest -m integration -v
```

## Architecture

`src/multipass/` contains nine modules:

- `_backend.py` — `CommandResult` dataclass, `CommandBackend` protocol, `SubprocessBackend` (real CLI), `FakeBackend` (for tests). All subprocess calls go through the backend.
- `exceptions.py` — Typed exception hierarchy rooted at `MultipassError`.
- `models.py` — Dataclasses (`VmInfo`, `VmState`, `ImageInfo`, `VmConfig`, etc.) with `from_*_json()` class methods that parse the actual Multipass CLI JSON output.
- `vm.py` — `MultipassVM`: per-VM operations (info, start, stop, restart, suspend, delete, recover, exec, exec_structured, transfer, mount, unmount, snapshot, restore, clone).
- `client.py` — `MultipassClient`: global operations (launch, launch_many, list_vms, find, purge, networks, version, get, set, aliases, ensure_running).
- `utils.py` — Small shared helpers.
- `testing.py` — Helpers for consumers writing their own tests against the SDK.
- `e2e.py` — The `multipass-vm-e2e` console script: an end-to-end harness that creates real VMs and exercises every operation. Not imported by the library.

`MultipassClient` creates `MultipassVM` instances and passes its backend down to them. Unit tests inject a `FakeBackend` configured with pre-built `CommandResult` responses.
