# Exec stdin DEVNULL Implementation Plan (multipass-sdk)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `multipass` CLI invocations from inheriting the caller's stdin, which makes `multipass exec` hang forever when stdin is a pty with no writer.

**Architecture:** One-line change in `SubprocessBackend.run` (`stdin=subprocess.DEVNULL`): the SDK is non-interactive by design — no SDK call ever feeds data through stdin, so the multipass CLI must never be left waiting on it. Single unit test pins the contract.

**Tech Stack:** Python, subprocess, pytest.

---

## Context (why)

Found during nanofaas PR #118 smoke debugging (2026-06-11): nanofaas wraps its e2e runs in `script` (pty) to defeat rich's no-tty output suppression. `SubprocessBackend.run` uses `subprocess.run(args, capture_output=True, text=True, cwd=cwd, env=env)` — stdout/stderr are piped but **stdin is inherited**. `multipass exec` forwards stdin to the remote process; with an inherited pty that never receives input or EOF, the exec session never terminates: three independent runs hung 1h+ on a sub-second remote command (`multipass exec ... authorized_keys` setup), while the identical command with socket/null stdin completed in 0.3 s.

`capture_output=True` already declares this backend non-interactive; closing stdin makes that explicit and immune to the caller's stdin type.

## Repo state note

This repo currently has untracked `docs/` and `uv.lock` — leave them as they are; stage only the files this plan touches.

---

### Task 1: stdin=DEVNULL in SubprocessBackend

**Files:**
- Modify: `src/multipass/_backend.py` (the `subprocess.run(...)` call in `SubprocessBackend.run`, ~line 43)
- Test: the unit test file covering the backend (find it: `grep -rln "SubprocessBackend" tests/unit/`; create `tests/unit/test_backend_stdin.py` if none fits)

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from multipass._backend import SubprocessBackend


def test_subprocess_backend_never_inherits_stdin() -> None:
    """multipass exec forwards stdin to the remote command; an inherited pty
    with no writer makes the session hang forever. The backend is
    non-interactive by design, so stdin must be closed explicitly."""
    backend = SubprocessBackend()
    completed = MagicMock(returncode=0, stdout="", stderr="")
    with patch("multipass._backend.subprocess.run", return_value=completed) as mock_run:
        backend.run(["multipass", "exec", "vm", "--", "true"])

    assert mock_run.call_args.kwargs.get("stdin") == subprocess.DEVNULL
```

Adapt only the plumbing if reality differs (e.g. `backend.run` signature, how `CommandResult` is built from the mock — if the constructor needs more attributes on `completed`, add them); the `stdin == subprocess.DEVNULL` assertion is the requirement.

- [ ] **Step 2: Run it — expect FAIL** (`stdin` kwarg absent → `None != DEVNULL`).

Run: `uv run pytest tests/unit -q` (check `pyproject.toml` for the project's actual test invocation/coverage flags; use the full unit suite if single files trip a coverage gate).

- [ ] **Step 3: Implement (one line)**

In `src/multipass/_backend.py`:

```python
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
            )
```

- [ ] **Step 4: Run the FULL test suite** (unit + integration if they don't require a live multipass; check how CI/`pyproject` runs them): `uv run pytest tests/unit -q` → green. If integration tests run against a real multipass on this machine and one is available, run them too — this change is exactly the kind integration tests exist for.

- [ ] **Step 5: Commit**

```bash
git add src/multipass/_backend.py tests/unit/
git commit -m "fix: never inherit caller stdin in SubprocessBackend (multipass exec hangs on writer-less pty)"
```

---

### Task 2: Publish (USER DECISION — this is the user's separate project)

- [ ] **Step 1:** The user reviews and pushes (plain push to `main` or PR, their call): `git push origin main` from `~/Downloads/multipass-sdk`.
- [ ] **Step 2:** Record the new short SHA (`git rev-parse --short HEAD`) — it gates **Task 4 of the nanofaas plan** `mcFaas/docs/superpowers/plans/2026-06-11-pr118-followups.md`, which bumps `multipass-sdk @ git+...@83b3704` → `@<new-sha>` in `tools/workflow-tasks/pyproject.toml` and `tools/controlplane/pyproject.toml`.

## Out of scope (deliberate)

- No behavior flag for interactive use: nothing in this SDK exposes interactive exec; if that ever becomes a feature, it needs its own streaming API, not inherited stdin.
- The sibling SDKs (azure-vm-sdk, proxmox-sdk) may have the same pattern — worth a 5-minute audit, but not part of this plan.
