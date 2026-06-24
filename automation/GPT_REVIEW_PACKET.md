# GPT_REVIEW_PACKET.md — Review Packet for GPT

> Ahmet pastes this file's content to GPT for each review cycle.
> Claude fills this after finishing a task. Keep it compact and evidence-based.

---

## TASK
AUTO-1D — FAZ-3-E1 and FAZ-T1 human-gate decomposition

## STATUS
DONE

## WHAT CHANGED
- `automation/FAZ3_E1_T1_DECOMPOSITION.md` created — full sub-task breakdown
- `automation/GPT_REVIEW_PACKET.md` updated (this file)
- `automation/SESSION_SUMMARY.md` updated

## EXACT FILES CHANGED
```
automation/FAZ3_E1_T1_DECOMPOSITION.md   (new)
automation/GPT_REVIEW_PACKET.md          (updated)
automation/SESSION_SUMMARY.md            (updated)
```

## EXACT COMMANDS RUN
```
git status --short
Get-ChildItem agents/ | Select Name
Get-ChildItem tests/ | Where { match proactive|e1_|tr_quality }
grep class|def|JARVIS_PROACTIVE in agents/proactive_delivery.py
grep JARVIS_PROACTIVE_ENABLED|def send|def deliver in agents/
grep def|class|ENABLED in agents/proactive_policy.py
Write automation/FAZ3_E1_T1_DECOMPOSITION.md
Write automation/GPT_REVIEW_PACKET.md
Write automation/SESSION_SUMMARY.md
git status --short (final)
git diff --check
git diff --stat
```

## EVIDENCE SUMMARY
```
py_compile:       not applicable (docs-only)
pytest target:    not run (docs-only)
pytest regr.:     not run (docs-only)
git diff --check: clean
git status:       3 untracked/modified files in automation/ (expected)
git diff --stat:  docs only, no Python touched
```

## AUTONOMY RULE VIOLATIONS
no

## RISKS / OPEN QUESTIONS
1. E1-S3 (Telegram wiring) needs GPT to clarify which file is the composition root
   for proactive delivery. `tools/telegram_agent.py` or a new adapter?
2. E1-S5 (scheduler design) depends on Ahmet's preferred runtime model
   (cron? asyncio? FastAPI background task?). Not safe to assume.
3. T1-S1 relies on `_fold_tr` being importable from a known module.
   GPT task card should specify exact import path.

## HUMAN NEEDED
- E1-S4, E1-S5, T1-S2 all require Ahmet — no action needed now.

## COMMIT READY
yes (when approved)

## SUGGESTED COMMIT
```
docs(automation): add FAZ-3-E1 and FAZ-T1 sub-task decomposition
```

## NEXT SAFE STEP
E1-S1 (SAFE_AUTONOMOUS) — GPT issues task card for delivery gap audit
(read-only: agents/proactive_delivery.py, proactive_policy.py, tools/telegram_agent.py)

---
*Packet prepared by: Claude Code | Date: 2026-06-24*
