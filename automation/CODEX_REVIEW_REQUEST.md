# CODEX_REVIEW_REQUEST.md — Review Request

---

## Status
PENDING_CODEX_REVIEW

## Branch
auto/opencode-deepseek

## Commits to Review

```
cc0072ac5  feat(proactive): add dry-run one-shot runner  (E1-S6A)
408e5cc28  docs(scheduler): record E1-S5 one-shot runner decision
1f9328b2b  docs(tr): record T1-S2 Turkish quality sign-off
9bbdab0c4  fix(local-agent): inject compact current project state
926616582  fix(local-agent): ground project-status answers in automation docs
0b127e7cc  fix(cli): prevent rich markup crash in local mode diagnostic
```

## Files Changed

```
agents/proactive_runner.py          NEW — E1-S6A one-shot dry-run runner
tests/test_e1_6a_proactive_runner.py  NEW — 11 runner tests

agent/local_agent.py                grounding rule + project context injection
main.py                             Rich markup fix
tests/test_local_agent_grounding.py NEW — 8 grounding regression tests
tests/test_main_cli_markup.py       NEW — 2 markup regression tests

roadmap_state.json                  FAZ-T1 done, E1-S5 decision, E1-S6A–E steps
automation/SCHEDULER_DECISION.md    NEW — E1-S5 architecture decision
automation/E1_S6_DECOMPOSITION.md  NEW — E1-S6A–E sub-task specs
automation/T1_S2_SMOKE_RESULTS.md  NEW — Ahmet T1-S2 PASS evidence
automation/HUMAN_NEEDED.md          T1-S2 + E1-S5 resolved; E1-S4 remains
automation/SESSION_SUMMARY.md       updated
automation/AUTONOMY_LOG.md          updated
```

## Tests Run

```
py -3.11 -m pytest tests/test_e1_6a_proactive_runner.py -q --tb=short
  -> 11/11 PASS

py -3.11 -m pytest tests/test_proactive_delivery.py tests/test_proactive_runtime.py -q --tb=short
  -> 35/35 PASS

py -3.11 -m pytest tests/test_local_agent_grounding.py tests/test_main_cli_markup.py
                   tests/test_tr_quality.py -q --tb=short
  -> 23/23 PASS (earlier batch)

py -3.11 -m py_compile agents/proactive_runner.py agent/local_agent.py main.py -> OK
py -3.11 -m json.tool roadmap_state.json -> VALID
git diff --check -> clean
```

## Specific Review Questions for Codex

1. **run_once() design**: accepts `state` dict and returns a result dict. The caller
   (main or tests) passes state in. Should the runner also accept a `state_fn` callable
   to fetch state from e.g. ProactiveCore, or is a plain dict sufficient for E1-S6A?

2. **--live in E1-S6A**: `--live` with `JARVIS_PROACTIVE_ENABLED=1` passes the gate
   but `sent=False` because no sender is wired yet. The comment says "Wired in E1-S4."
   Is this acceptable as E1-S6A scope, or should --live be completely blocked until E1-S6D?

3. **_check_live_gate placement**: the gate is in `proactive_runner.py`. E1-S6D will
   add more guard logic to the same file. Is it cleaner to keep gate logic in runner
   or move it to a shared `proactive_guards.py`?

4. **Hardcoded user_id/task_id defaults**: `user_id="ahmet"`, `task_id="morning_brief"`.
   These should eventually come from config. Is hardcoding acceptable for E1-S6A scope?

5. **subprocess in local_agent.py** (from previous batch): `git log -5 --oneline` at
   agent startup. Still safe? Timeout is 5s. Graceful fallback on failure.

## Forbidden Actions for Codex

- Do not edit .env
- Do not trigger live Telegram send
- Do not start Windows Task Scheduler or create a scheduled task
- Do not implement E1-S6B–E yet (review E1-S6A first)
- Do not push

## Review Verdict Expected
PASS / CONCERN / BLOCKER

---

*Prepared by: Claude Code | Date: 2026-06-27*
