# GPT_REVIEW_PACKET.md — Review Packet for GPT

> Ahmet pastes this file's content to GPT for each review cycle.
> Claude fills this after finishing a task. Keep it compact and evidence-based.

---

## TASK
<!-- Task ID and one-line description -->

## STATUS
<!-- DONE | DONE_WITH_RISKS | BLOCKED | PARTIAL -->

## WHAT CHANGED
<!-- Bullet list: file → what and why. No prose. -->

## EXACT FILES CHANGED
<!-- One per line: full relative path -->

## EXACT COMMANDS RUN
<!-- One per line, in order: what Claude actually executed -->

## EVIDENCE SUMMARY
```
py_compile:       [OK / FAIL / not applicable]
pytest target:    [N passed / N failed — exact command]
pytest regr.:     [N passed / N failed — exact command / not run]
git diff --check: [clean / issues found]
git status:       [clean / N untracked / N modified]
git diff --stat:  [empty / N files changed]
```

## AUTONOMY RULE VIOLATIONS
<!-- yes (describe) / no -->

## RISKS / OPEN QUESTIONS
<!-- Anything GPT should review carefully. Empty = none. -->

## HUMAN NEEDED
<!-- Anything requiring Ahmet before next step. Empty = none. -->

## COMMIT READY
<!-- yes / no -->

## SUGGESTED COMMIT
```
<one-liner>
```

## NEXT SAFE STEP
<!-- Task ID + autonomy level: SAFE_AUTONOMOUS | GPT_REVIEW_REQUIRED | HUMAN_REQUIRED -->

---
*Packet prepared by: Claude Code | Date: YYYY-MM-DD*
