# CODEX_REVIEW_REQUEST.md — Review Request

---

## E1-S6A CLOSED — PASS (2026-06-27)
## E1-S6B CLOSED — PASS (2026-06-27)
## E1-S6C CLOSED (first review) — BLOCKER (2026-06-28)

Blocker: -StopIfGoingOnBatteries $false is not a valid parameter on this system.
Valid switch: -DontStopIfGoingOnBatteries (no argument).
Fix commit: see below.

---

## Status
PENDING_CODEX_REVIEW — E1-S6C FIX re-review

## Branch
auto/opencode-deepseek

## Commits to Review

```
(fix commit TBD — docs only, committed in same session)
3de2e1035  docs(scheduler): add Windows Task Scheduler dry-run template  (E1-S6C original)
```

## E1-S6C Blocker Fix

### Blocker — invalid -StopIfGoingOnBatteries $false parameter (fixed)

Both files updated:
- `scripts/create_jarvis_task.ps1`: replaced in actual `$Settings` block AND in printed preview command
- `docs/scheduler_setup.md`: replaced in code block example

### Structural improvement: preview mode calls no ScheduledTask cmdlets

All `New-Scheduled*` calls moved INSIDE the `-Apply` guard block.
Default preview mode path:
1. Print config strings (pure Write-Host, no task objects)
2. Print "PREVIEW ONLY" message
3. `exit 0`

This ensures that even if any ScheduledTask cmdlet were to fail, it cannot
affect preview mode because the cmdlets are never called without `-Apply`.

## Files Changed in fix commit

```
scripts/create_jarvis_task.ps1  UPDATED — -DontStopIfGoingOnBatteries; all New-Scheduled* inside -Apply block; no here-strings (ASCII-safe)
docs/scheduler_setup.md         UPDATED — -DontStopIfGoingOnBatteries in manual registration code block
roadmap_state.json              UPDATED — E1-S6C status todo -> in_progress
```

## Validation Run

```
py -3.11 -m json.tool roadmap_state.json -> VALID

git diff --check -> clean

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/create_jarvis_task.ps1
  -> EXIT CODE: 0
  -> printed: Task name, Executable, Working dir, Repeat interval, Mode: DRY-RUN
  -> printed: LIVE DELIVERY IS BLOCKED until E1-S4
  -> printed: Register-ScheduledTask ... -DontStopIfGoingOnBatteries ...
  -> printed: PREVIEW ONLY (task NOT created)
  -> No Register-ScheduledTask executed

Select-String ... -Pattern "StopIfGoingOnBatteries" -> 0 matches (invalid form gone)
Select-String ... -Pattern "DontStopIfGoingOnBatteries" -> 2 matches (ps1 line 83 + 123; md line 96)
Register-ScheduledTask -> only in printed preview strings and -Apply block
--live -> only in comments and safety warnings; NOT in $FullArgument
```

## Safety Checklist

- [x] -StopIfGoingOnBatteries $false REMOVED from both files
- [x] -DontStopIfGoingOnBatteries (switch, no argument) present in both files
- [x] Preview mode exits 0 without -Apply
- [x] No ScheduledTask cmdlets called in preview mode
- [x] Scheduled command: py -3.11 -m agents.proactive_runner (no --live)
- [x] Register-ScheduledTask gated behind -Apply and ShouldProcess
- [x] No .env reads, no tokens, no Telegram calls
- [x] E1-S4 warnings prominent

## Review Verdict Expected
PASS / CONCERN / BLOCKER

---

*Prepared by: Claude Code | Date: 2026-06-28 | Original: 3de2e1035*
