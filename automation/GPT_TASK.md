# GPT_TASK.md — Current Task Card

> Overwrite this file each time GPT assigns a new task.
> Claude reads this at session start. If this file contains only the template, Claude stops and waits.

---

## Task ID
<!-- e.g. AUTO-1A, FAZ-3-E1-delivery, J0-fix-encoding -->

## Objective
<!-- One paragraph: what must be true when this task is done. -->

## Autonomous continuation allowed
<!-- yes / no -->

## Human presence required
<!-- yes / no — if yes, Claude stops immediately after reading this -->

## Maximum commands allowed
<!-- e.g. 10 — helps Claude avoid runaway execution -->

## Maximum files allowed
<!-- e.g. 3 — helps Claude stay surgical -->

## Scope — Allowed Files
<!-- List exact file paths Claude may create or edit. -->
<!-- Claude must not touch anything outside this list. -->

## Scope — Forbidden Files / Operations
<!-- List explicit exclusions beyond the standard forbidden list. -->

## Tests Required
<!-- Exact pytest commands Claude must run to verify success. -->
```powershell

```

## Stop Conditions
<!-- When must Claude stop immediately and report, even if incomplete? -->
- [ ] Any test file outside the allowed scope needs changing
- [ ] Fix attempt 3 still failing
- [ ] Unexpected file appears in git status
- [ ] Ambiguity about allowed_paths
- [add more as needed]

## Success Criteria
<!-- What exact evidence makes this task DONE? -->
- [ ] py_compile passes on changed files
- [ ] Required tests pass
- [ ] git diff --check clean
- [ ] git status shows only expected files
- [ ] CLAUDE_REPORT.md written
- [ ] GPT_REVIEW_PACKET.md written

## Notes for Claude
<!-- Architecture hints, gotchas, Turkish encoding rules, anchors, etc. -->

---
*Written by: GPT | Date: YYYY-MM-DD*
