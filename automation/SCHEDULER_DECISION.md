# SCHEDULER_DECISION.md — E1-S5 Architecture Decision

> Approved by: Ahmet | Date: 2026-06-24
> Gate: E1-S5 Scheduler / background loop design

---

## Decision

**Use Windows Task Scheduler + one-shot proactive runner + default dry-run.**

---

## Architecture

### What we are building
A short-lived Python runner (`proactive_runner.py`) that:
1. Is triggered externally by Windows Task Scheduler
2. Runs once, evaluates proactive alerts, optionally delivers, then exits
3. Defaults to **dry-run** (no Telegram send) unless explicitly configured

### What we are NOT building
- No always-on asyncio background loop
- No daemon process
- No long-running scheduler inside Python
- No self-rescheduling code

### Delivery gate
Live Telegram delivery remains **blocked** until E1-S4 live smoke is completed by Ahmet.
`JARVIS_PROACTIVE_ENABLED` must remain 0 by default.
Live mode requires explicit flag AND human approval (E1-S4 sign-off).

---

## Rationale

| Concern | Why this design wins |
|---------|---------------------|
| Safety | Dry-run default; live mode requires explicit opt-in |
| Testability | One-shot runner is fully testable without a running daemon |
| Stoppability | Killing the Task Scheduler job stops all proactive delivery instantly |
| Windows fit | Windows Task Scheduler is native, reliable, no extra service |
| No scope creep | asyncio/daemon adds concurrency risk; unnecessary for current needs |
| 7/24 PC | Short-lived process is lighter than a resident daemon on a personal PC |

---

## Implementation Plan (E1-S6 sub-tasks)

| Sub-task | Title | Autonomy | Depends on |
|----------|-------|----------|------------|
| E1-S6A | proactive_runner.py dry-run CLI | SAFE_AUTONOMOUS | E1-S5 |
| E1-S6B | Delivery result logging | SAFE_AUTONOMOUS | E1-S6A |
| E1-S6C | Windows Task Scheduler docs + script template | SAFE_AUTONOMOUS | E1-S6A |
| E1-S6D | Live-mode guard (blocked until E1-S4) | SAFE_AUTONOMOUS | E1-S6A |
| E1-S6E | Duplicate / throttle guard | SAFE_AUTONOMOUS | E1-S6A |

See `automation/E1_S6_DECOMPOSITION.md` for full sub-task specs.

---

## Invariants (must hold throughout E1-S6 implementation)

1. `JARVIS_PROACTIVE_ENABLED=0` default — never flip in source or tests
2. No live Telegram send in any E1-S6A–E code until E1-S4 passes
3. Runner exits cleanly after one shot — no loops, no blocking
4. All delivery in dry-run mode logs what *would* be sent, not what *was* sent
5. Throttle/cooldown must prevent repeated identical alerts within a configurable window

---

*Written by: Claude Code | Approved by: Ahmet | Date: 2026-06-24*
