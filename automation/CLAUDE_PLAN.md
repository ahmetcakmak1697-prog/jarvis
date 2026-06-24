# CLAUDE_PLAN.md — Pre-Edit Plan

> Claude writes this before touching any file.
> Overwrite each task. GPT or Ahmet may veto before execution begins.

---

## Selected Task
<!-- Task ID and title from GPT_TASK.md -->

## Session Bootstrap Status
<!-- Output of scripts/jarvis_autonomy_status.ps1 — one-line summary -->
<!-- e.g. "branch: auto/opencode-deepseek | status: clean | last: abc1234 ..." -->

## Safety Classification
<!-- SAFE_AUTONOMOUS | GPT_REVIEW_REQUIRED | HUMAN_REQUIRED -->

## Stop Reason (if not SAFE_AUTONOMOUS)
<!-- If GPT_REVIEW_REQUIRED or HUMAN_REQUIRED: explain exactly why Claude is stopping. -->
<!-- Leave blank if SAFE_AUTONOMOUS. -->

## Dependency Check
<!-- Are all depends_on steps marked done in roadmap_state.json? -->
- [ ] Yes — proceed
- [ ] No — blocked on: [list]

## Files Expected to Touch
<!-- List exact file paths. Must be subset of GPT_TASK.md allowed list. -->

## Files Expected NOT to Touch
<!-- Explicit no-touch list based on task constraints. -->

## Token-Saver Plan
<!-- Minimal reads and commands needed — not a broad sweep. -->
<!-- e.g. "Read only agents/foo.py lines 40-80; grep for symbol X; run 1 targeted test." -->

## Plan
<!-- Step-by-step numbered list. Keep each step small and verifiable. -->
1.
2.
3.

## Commands Expected to Run
```powershell
# compile check

# targeted test

# regression (only if shared logic touched)

# git status
```

## Risks Identified Before Starting
<!-- Known edge cases, Türkçe encoding gotchas, import side effects, etc. -->

## Estimated Scope
<!-- Rough: lines changed, files touched, test count -->

---
*Written by: Claude Code | Date: YYYY-MM-DD*
