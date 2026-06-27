# CODEX_REVIEW_REQUEST.md — Review Request

---

## Status
PENDING_CODEX_REVIEW — E1-S6A FIX (re-review after BLOCKER)

## Branch
auto/opencode-deepseek

## Commits to Review

```
c8eee9a84  fix(proactive): harden dry-run runner CLI contract  (E1-S6A fix)
cc0072ac5  feat(proactive): add dry-run one-shot runner  (E1-S6A original)
408e5cc28  docs(scheduler): record E1-S5 one-shot runner decision
1f9328b2b  docs(tr): record T1-S2 Turkish quality sign-off
9bbdab0c4  fix(local-agent): inject compact current project state
926616582  fix(local-agent): ground project-status answers in automation docs
0b127e7cc  fix(cli): prevent rich markup crash in local mode diagnostic
```

## E1-S6A BLOCKER FIX — c8eee9a84

### BLOCKER: CLI invocation (fixed)
- Supported invocation: `py -3.11 -m agents.proactive_runner [--dry-run] [--live]`
- Direct file invocation (`py agents/proactive_runner.py`) explicitly unsupported
- Subprocess test added: exit 0 + valid JSON via module invocation
- E1_S6_DECOMPOSITION.md updated: docs task scheduler invocation as module only

### Concern A: --live misleadingly exits 0 (fixed)
- `--live` now ALWAYS raises `RuntimeError(_LIVE_NOT_IMPLEMENTED)` regardless of env var
- `_check_live_gate()` (env-var only) replaced by gate inside `run_once()`
- Tests: `--live` blocked with `JARVIS_PROACTIVE_ENABLED=0` AND with `=1`

### Concern B: run_once(dry_run=False) bypassed gate (fixed)
- Gate moved inside `run_once()`: raises `RuntimeError` if `dry_run=False`
- Every caller (main, tests, future code) is protected; no env-var dependency
- `_check_live_gate()` removed

### Concern C: CLI parsing silent on unknown/conflicting args (fixed)
- Replaced ad-hoc `"--live" in argv` scan with argparse
- `--dry-run` and `--live` are mutually exclusive group; argparse enforces
- Unknown args rejected with non-zero exit
- Tests: both cases covered (`test_main_rejects_dry_run_and_live_together`, `test_main_rejects_unknown_flag`)

### Concern D: roadmap_state.json inconsistency (addressed)
- E1-S6A status: `"todo"` → `"in_progress"` (Codex blocker in progress)
- `acceptance_criteria_machine` updated to include module invocation check
- Will be set to `"done"` after this re-review passes

### Concern E: ProactiveCore.evaluate() not wired (addressed in docs)
- E1_S6_DECOMPOSITION.md updated with explicit "Architecture note (Concern E addressed)"
- E1-S6A intentionally wires `ProactivePolicy` directly; `ProactiveCore` deferred
- Runner docstring documents this decision

## Files Changed in c8eee9a84

```
agents/proactive_runner.py          UPDATED — argparse, live gate inside run_once, no _check_live_gate
tests/test_e1_6a_proactive_runner.py  UPDATED — 16 tests (was 11); +subprocess, +mutual exclusion, +live-always-blocked
roadmap_state.json                  UPDATED — E1-S6A status in_progress; criteria updated
automation/E1_S6_DECOMPOSITION.md  UPDATED — E1-S6A section rewritten; Concern E addressed
```

## Tests Run (c8eee9a84)

```
py -3.11 -m pytest tests/test_e1_6a_proactive_runner.py -q --tb=short
  -> 16/16 PASS

py -3.11 -m pytest tests/test_e1_6a_proactive_runner.py tests/test_proactive_delivery.py
                   tests/test_proactive_runtime.py -q --tb=short
  -> 51/51 PASS

py -3.11 -m agents.proactive_runner
  -> exit 0, stdout: {"ts":"...","dry_run":true,"decision":"suppress","reason":"proactive_disabled",...}

py -3.11 -m json.tool roadmap_state.json -> VALID
git diff --check -> clean (CRLF warnings only, not errors)
```

## Specific Review Questions for Codex

1. **E1-S6A scope complete?** The runner is intentionally minimal: no ProactiveCore,
   no throttle (E1-S6E), no live send (E1-S4). Is the scope boundary correct?

2. **roadmap_state.json**: After this review passes, E1-S6A should be marked `"done"`.
   Codex may do so in its fix if verdict is PASS, or Claude will update after PASS verdict.

3. **E1-S6B ready?** All blocking concerns are addressed. Is `DeliveryResult` struct
   (replace `bool` return from `deliver()`) next? Allowed paths confirmed in decomp.

4. **subprocess test environment**: `test_subprocess_module_invocation_*` passes
   `{**os.environ, "JARVIS_PROACTIVE_ENABLED": "0"}` — inherits full shell env
   but forces the guard to suppress. Any concern with test isolation?

## Forbidden Actions for Codex

- Do not edit .env
- Do not trigger live Telegram send
- Do not start Windows Task Scheduler or create a scheduled task
- Do not implement E1-S6B–E yet (verify E1-S6A fix first)
- Do not push

## Review Verdict Expected
PASS / CONCERN / BLOCKER

---

*Prepared by: Claude Code | Date: 2026-06-27 | Fix commit: c8eee9a84*
