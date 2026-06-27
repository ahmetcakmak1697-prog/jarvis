# CODEX_REVIEW_REQUEST.md — Review Request

---

## E1-S6A CLOSED — PASS (2026-06-27)
## E1-S6B CLOSED — PASS (2026-06-27)

Commits reviewed and closed:
- E1-S6A: c8eee9a84, cc0072ac5
- E1-S6B: 648b74455, a53001577

---

## Status
PENDING_CODEX_REVIEW — E1-S6C (Windows Task Scheduler docs + script template)

## Branch
auto/opencode-deepseek

## Commits to Review

```
(commit hash TBD — E1-S6C not yet committed)
```

## E1-S6C Scope

Docs and commented-out PowerShell template for Windows Task Scheduler integration.
No code changes. No real scheduled task created.

### Files Expected
```
docs/scheduler_setup.md          NEW — step-by-step guide
scripts/create_jarvis_task.ps1   NEW — safe print-only template (no Register-ScheduledTask by default)
```

### Safety Invariants for Codex to Verify
- `Register-ScheduledTask` NOT called by default (print-only unless -Apply flag)
- Invocation uses module form: `py -3.11 -m agents.proactive_runner`
- Working directory is repo root: `C:\Users\Ahmedov\Desktop\Jarvis\jarvis-agent-auto`
- No `.env`, no tokens, no Telegram
- No `--live` flag in scheduled command
- Clear comment: live delivery blocked until E1-S4

### Validation Expected
```
py -3.11 -m json.tool roadmap_state.json -> VALID
git diff --check -> clean
Get-Content scripts/create_jarvis_task.ps1 -> review content
```

## Review Verdict Expected
PASS / CONCERN / BLOCKER

---

*Prepared by: Claude Code | Date: 2026-06-27*
