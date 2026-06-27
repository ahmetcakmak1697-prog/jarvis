# CODEX_REVIEW_REQUEST.md — Review Request

---

## E1-S6A CLOSED — PASS (2026-06-27)
## E1-S6B CLOSED — PASS (2026-06-27)
## E1-S6C CLOSED — PASS (2026-06-28)

Commits reviewed and closed:
- E1-S6A: c8eee9a84, cc0072ac5
- E1-S6B: 648b74455, a53001577
- E1-S6C: 4f6a5b6e0, 3de2e1035

---

## Status
PENDING_CODEX_REVIEW — E1-S6D (live-mode guard regression tests)

## Branch
auto/opencode-deepseek

## Commits to Review

```
(commit hash TBD — E1-S6D not yet committed)
```

## E1-S6D Scope

Dedicated regression tests that lock the live-mode guard contract.
No new code in proactive_runner.py — the guard is already implemented.
New file: tests/test_e1_6d_live_guard.py

### Contract Being Locked
- `py -3.11 -m agents.proactive_runner --live` → exit 1
- `--live` blocked even with JARVIS_PROACTIVE_ENABLED=1
- `run_once(dry_run=False)` → raises RuntimeError mentioning E1-S4
- `--dry-run --live` together → non-zero exit
- Unknown args → non-zero exit
- Default dry-run still exits 0
- No Telegram/network imports in runner

### Tests Expected (tests/test_e1_6d_live_guard.py)
- test_live_cli_blocked_without_env
- test_live_cli_blocked_with_env_enabled
- test_run_once_dry_run_false_raises
- test_live_error_mentions_e1_s4
- test_default_dry_run_still_exits_0
- test_no_live_sender_or_telegram_imports_in_runner
- test_conflicting_dry_run_and_live_rejected
- test_unknown_arg_rejected

### Validation Expected
```
py -3.11 -m pytest tests/test_e1_6d_live_guard.py tests/test_e1_6a_proactive_runner.py
                   tests/test_e1_6b_delivery_result.py tests/test_proactive_delivery.py
                   tests/test_proactive_runtime.py -q --tb=short
py -3.11 -m agents.proactive_runner            -> exit 0
py -3.11 -m agents.proactive_runner --live     -> exit 1
git diff --check -> clean
```

## Review Verdict Expected
PASS / CONCERN / BLOCKER

---

*Prepared by: Claude Code | Date: 2026-06-28*
