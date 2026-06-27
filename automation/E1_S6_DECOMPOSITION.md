# E1_S6_DECOMPOSITION.md — E1-S6 Implementation Sub-task Specs

> Source: E1-S5 architecture decision (automation/SCHEDULER_DECISION.md)
> Approved by: Ahmet | Date: 2026-06-24
> All sub-tasks are SAFE_AUTONOMOUS unless noted.

---

## Overview

Windows Task Scheduler triggers `proactive_runner.py`.
Runner is one-shot: evaluate → (dry-run by default) → log → exit.
Live delivery blocked until E1-S4 smoke complete.

---

## E1-S6A — proactive_runner.py dry-run CLI
**Classification: SAFE_AUTONOMOUS**
**Depends on:** E1-S3B (adapter seam done), E1-S5 (decision)
**Status: DONE (cc0072ac5 + fix c8eee9a84) — Codex PASS 2026-06-27**

### Supported invocation (from repo root)
```
py -3.11 -m agents.proactive_runner [--dry-run] [--live]
```
Direct file invocation (`py agents/proactive_runner.py`) is NOT supported.
Windows Task Scheduler must use module invocation with `--working-directory` set to repo root.

### What was built
- `agents/proactive_runner.py`
- `run_once(state, *, dry_run, user_id, task_id) -> dict` — pure, no network
- `main(argv) -> int` — argparse-based; rejects unknown args; --dry-run and --live are mutually exclusive
- `--dry-run` (default): no send, no network, no .env needed; exits 0
- `--live`: ALWAYS raises RuntimeError("NOT IMPLEMENTED until E1-S4") in E1-S6A regardless of env var
- `run_once(dry_run=False)`: also raises RuntimeError so every caller is protected
- Exit: 0 = success, 1 = error / not-implemented

### Architecture note (Concern E addressed)
E1-S6A wires **ProactivePolicy directly**, not ProactiveCore.evaluate().
ProactiveCore integration is deferred to a later sub-task when a real state
source (calendar, sensors, etc.) is available. Using ProactivePolicy directly
allows full dry-run testing without ProactiveCore dependencies.

### Tests (16 passing)
- dry-run/suppress/deliver behavior, required keys
- run_once(dry_run=False) raises RuntimeError
- --live blocked with and without env var (Concern A)
- --dry-run + --live mutually exclusive (Concern C)
- unknown args rejected (Concern C)
- one-shot non-blocking thread test
- subprocess: `py -3.11 -m agents.proactive_runner` exits 0, stdout is valid JSON (Blocker fix)

### Allowed paths
- `agents/proactive_runner.py`
- `tests/test_e1_6a_proactive_runner.py`

---

## E1-S6B — Delivery result logging
**Classification: SAFE_AUTONOMOUS**
**Depends on:** E1-S6A

### What to build
- `DeliveryResult` dataclass: `dry_run: bool`, `plan_status: str`, `sent: bool`, `reason: str`, `ts: float`
- `deliver()` in `agents/proactive_delivery.py` returns `DeliveryResult` instead of `bool`
- `run_proactive_delivery()` in `agents/proactive_runtime.py` returns `DeliveryResult`
- Log result to stdout as single JSON line: `{"ts": ..., "dry_run": ..., "status": ..., "sent": ..., "reason": ...}`
- Replaces current silent bool return (addresses design debt noted in SESSION_SUMMARY)

### Tests
- `tests/test_e1_6b_delivery_result.py`
- dry-run result: `sent=False`, `dry_run=True`
- invalid plan: `sent=False`, `reason="invalid_plan"`
- stdout JSON line is valid JSON with required keys
- existing bool-return tests updated or complemented

### Allowed paths
- `agents/proactive_delivery.py`
- `agents/proactive_runtime.py`
- `tests/test_e1_6b_delivery_result.py` (NEW)
- `tests/test_proactive_delivery.py` (update if needed)
- `tests/test_proactive_runtime.py` (update if needed)

---

## E1-S6C — Windows Task Scheduler docs + script template
**Classification: SAFE_AUTONOMOUS (docs/script only)**
**Depends on:** E1-S6A

### What to build
- `docs/scheduler_setup.md`: step-by-step guide for creating a Windows Task Scheduler job
  - How to point it at `python agents/proactive_runner.py --dry-run`
  - How to set working directory, Python path, venv activation
  - How to set schedule (e.g., every 30 min)
  - How to enable live mode after E1-S4 passes
- `scripts/create_jarvis_task.ps1`: PowerShell template to register the task (commented out by default, no auto-execution)
  - Includes safety comment: "Uncomment only after E1-S4 live smoke passes"

### Tests
- None (docs/script only)
- `git diff --check` suffices

### Allowed paths
- `docs/scheduler_setup.md` (NEW)
- `scripts/create_jarvis_task.ps1` (NEW)

---

## E1-S6D — Live-mode guard (blocked until E1-S4)
**Classification: SAFE_AUTONOMOUS**
**Depends on:** E1-S6A

### What to build
- `agents/proactive_runner.py` `--live` path: check `JARVIS_PROACTIVE_ENABLED == "1"` before constructing sender
- If env var not set to "1": log `"LIVE MODE BLOCKED: set JARVIS_PROACTIVE_ENABLED=1 and complete E1-S4 smoke"` and exit 1
- No live Telegram send in this sub-task (that's E1-S4's job)
- This sub-task only implements the guard, not the actual live send

### Tests
- `tests/test_e1_6d_live_guard.py`
- without env: runner exits non-zero, no sender constructed
- with env=1 but sender=None stub: guard passes, dry-run still works
- guard message contains "E1-S4" or "BLOCKER" wording

### Allowed paths
- `agents/proactive_runner.py`
- `tests/test_e1_6d_live_guard.py` (NEW)

---

## E1-S6E — Duplicate / throttle guard
**Classification: SAFE_AUTONOMOUS**
**Depends on:** E1-S6A

### What to build
- `agents/proactive_throttle.py`: simple file-based cooldown store
  - `ThrottleStore(path)`: reads/writes a JSON file
  - `is_throttled(alert_id: str, cooldown_seconds: int) -> bool`
  - `record_sent(alert_id: str)`: marks alert as sent with timestamp
- Wire into `proactive_runner.py`: before delivery, check throttle; skip if throttled
- Default cooldown: 3600 seconds (1 hour) for same alert_id
- Dry-run: check throttle but do NOT record (so dry-run doesn't block real runs)

### Tests
- `tests/test_e1_6e_throttle.py`
- fresh store: `is_throttled` returns False
- after `record_sent`: `is_throttled` returns True within cooldown
- after cooldown expires: `is_throttled` returns False
- dry-run does not call `record_sent`
- corrupt/missing store file: graceful fallback (not throttled)

### Allowed paths
- `agents/proactive_throttle.py` (NEW)
- `tests/test_e1_6e_throttle.py` (NEW)
- `agents/proactive_runner.py` (wire throttle check)

---

## Execution Order

```
E1-S6A  (SAFE_AUTONOMOUS)  — dry-run CLI runner
E1-S6B  (SAFE_AUTONOMOUS)  — delivery result logging (resolves design debt)
E1-S6C  (SAFE_AUTONOMOUS)  — Windows Task Scheduler docs
E1-S6D  (SAFE_AUTONOMOUS)  — live-mode guard
E1-S6E  (SAFE_AUTONOMOUS)  — throttle guard
E1-S4   (HUMAN_REQUIRED)   — live Telegram smoke (after all E1-S6 done)
```

---

## Safety Invariants (must hold throughout)

1. `JARVIS_PROACTIVE_ENABLED=0` default — never flip in source or tests
2. No live Telegram send until E1-S4 passes
3. `--live` flag always guarded by env check before any sender construction
4. Throttle store is file-based only (no network, no external service)
5. Runner always exits (never loops or sleeps indefinitely)

---

*Written by: Claude Code | Date: 2026-06-24 | No code changed*
