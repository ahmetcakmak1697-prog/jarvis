# CODEX_REVIEW_REQUEST.md — Review Request

---

## E1-S6A CLOSED — PASS (2026-06-27)
## E1-S6B CLOSED — PASS (2026-06-27)

---

## Status
PENDING_CODEX_REVIEW — E1-S6C (Windows Task Scheduler docs + script template)

## Branch
auto/opencode-deepseek

## Commits to Review

```
3de2e1035  docs(scheduler): add Windows Task Scheduler dry-run template  (E1-S6C)
```

## E1-S6C Scope

Docs-only task. No code changes. No real scheduled task created.

### Files Changed
```
docs/scheduler_setup.md          NEW — step-by-step guide for Task Scheduler setup
scripts/create_jarvis_task.ps1   NEW — safe print-only PowerShell template
```

## Safety Checklist for Codex

### docs/scheduler_setup.md
- [ ] Supported invocation is `py -3.11 -m agents.proactive_runner` (module form)
- [ ] Working directory documented as repo root
- [ ] Default mode is dry-run (no `--live`)
- [ ] `--live` documented as blocked until E1-S4
- [ ] Manual smoke test commands and expected output provided
- [ ] E1-S4 gate warning present (live delivery blocked until sign-off)

### scripts/create_jarvis_task.ps1
- [ ] Default (no flags): PRINT ONLY — `Register-ScheduledTask` NOT called
- [ ] `-Apply` flag required to register (guarded by `if (-not $Apply) { exit 0 }`)
- [ ] Scheduled command uses `py -3.11 -m agents.proactive_runner` (no `--live`)
- [ ] `$RunnerModule = "-m agents.proactive_runner"` — no `--live` in the module arg
- [ ] No `.env` reads, no tokens, no Telegram calls
- [ ] Live delivery warning present (`E1-S4` mentioned)
- [ ] Safety check: warns if `JARVIS_PROACTIVE_ENABLED=1` is detected in env

## Validation Run

```
py -3.11 -m json.tool roadmap_state.json -> VALID
git diff --check -> clean (CRLF warnings only)
Get-Content scripts/create_jarvis_task.ps1 -> reviewed above
```

## Review Verdict Expected
PASS / CONCERN / BLOCKER

---

*Prepared by: Claude Code | Date: 2026-06-27 | Commit: 3de2e1035*
