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

## EVIDENCE
```
py_compile:    [OK / FAIL]
pytest target: [N passed / N failed — command used]
pytest regr.:  [N passed / N failed — command used]
git diff --check: [clean / issues]
git status:    [clean / N files]
```

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
