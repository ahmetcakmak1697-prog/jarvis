# CLAUDE_PLAN.md — Pre-Edit Plan

> Claude writes this before touching any file.
> Overwrite each task. GPT or Ahmet may veto before execution begins.

---

## Selected Task
<!-- Task ID and title from GPT_TASK.md -->

## Safety Classification
<!-- SAFE_AUTONOMOUS | GPT_REVIEW_REQUIRED | HUMAN_REQUIRED -->
<!-- If not SAFE_AUTONOMOUS, explain why and stop here. -->

## Dependency Check
<!-- Are all depends_on steps marked done in roadmap_state.json? -->
- [ ] Yes — proceed
- [ ] No — blocked on: [list]

## Files Expected to Touch
<!-- List exact file paths. Must be subset of GPT_TASK.md allowed list. -->

## Files Expected NOT to Touch
<!-- Explicit no-touch list based on task constraints. -->

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
