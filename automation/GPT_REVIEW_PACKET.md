# GPT_REVIEW_PACKET.md — Review Packet for GPT

> Ahmet pastes this file's content to GPT for each review cycle.

---

## TASK
E1-S1 — Read-Only Proactive Delivery Gap Audit

## STATUS
DONE

## WHAT CHANGED
- `automation/E1_S1_DELIVERY_GAP_AUDIT.md` created (full audit)
- `automation/GPT_REVIEW_PACKET.md` updated (this file)
- `automation/SESSION_SUMMARY.md` updated

## EXACT FILES CHANGED
```
automation/E1_S1_DELIVERY_GAP_AUDIT.md   (new)
automation/GPT_REVIEW_PACKET.md          (updated)
automation/SESSION_SUMMARY.md            (updated)
```

## EXACT COMMANDS RUN
```
git status --short (pre)
Read agents/proactive_delivery.py
Read agents/proactive_policy.py
Read tools/telegram_agent.py
Read tests/test_proactive_delivery.py
git status --short / diff --check / diff --stat (post)
```

## EVIDENCE SUMMARY
```
py_compile:       not applicable (docs-only)
pytest target:    not run (docs-only)
pytest regr.:     not run (docs-only)
git diff --check: clean
git status:       1 new + 2 modified in automation/ (expected)
git diff --stat:  docs only, no Python touched
```

## AUTONOMY RULE VIOLATIONS
no

## KEY FINDINGS (for GPT review)

### Gap summary
```
ProactivePolicy.decide() → ProactiveDecision
create_delivery_plan()   → DeliveryPlan(status="ready")
[GAP] no deliver() function exists
[GAP] no Telegram send wired to proactive path
[GAP] no composition root for proactive push
```

### What exists
- `DeliveryPlan` frozen dataclass + `create_delivery_plan()` — planning only
- `ProactivePolicy` with feature flag, mute, DND, cooldown logic — decision only
- `JARVIS_PROACTIVE_ENABLED` guard lives in ProactivePolicy only
- `send_message(chat_id, text)` in telegram_agent.py — plain function, injectable
- 12 tests in test_proactive_delivery.py, all planning-layer only

### Test 11 constraint
`test_module_has_no_send_function` asserts no function with "send" in name exists
in proactive_delivery.py. A `deliver()` function would pass this guard.

### cmd_brief() is pull-based, unrelated
telegram_agent.cmd_brief() calls ProactiveCore directly. It is NOT the push path.
ProactivePolicy/DeliveryPlan are completely unused in production today.

### Smallest safe next step (E1-S2)
Add `deliver(plan: DeliveryPlan, sender_fn=None) -> bool` to proactive_delivery.py.
sender_fn=None → noop. Real send only when caller explicitly provides sender_fn.
No network imports in module. All 12 existing tests still pass.

## OPEN QUESTIONS FOR GPT (must answer before E1-S3)

1. **Composition root**: Where should proactive push pipeline be assembled?
   - Option A: Inside telegram_agent.py (alongside _build_assistant_executor)
   - Option B: New file agents/proactive_runtime.py

2. **user_id → chat_id mapping**: DeliveryPlan.user_id is a caller-provided string.
   telegram_agent.send_message(chat_id, text) needs the real Telegram chat_id.
   Are these the same value? Where does the caller get Ahmet's chat_id from?

3. **Message format for push**: Should deliver() format using DeliveryPlan fields only
   (sparse: task_id, priority, reason), or call cmd_brief() for full brief-style output?

## RISKS / OPEN QUESTIONS
- All 3 open questions above must be resolved by GPT before E1-S3 task card is issued.
- test_module_has_no_send_function is a safety guard — E1-S2 must not break it.

## HUMAN NEEDED
- E1-S4: Ahmet sets JARVIS_PROACTIVE_ENABLED=1, confirms Telegram message on phone
- E1-S5: Ahmet + GPT decide scheduler design

## COMMIT READY
yes (when approved)

## SUGGESTED COMMIT
```
docs(automation): add E1-S1 proactive delivery gap audit
```

## NEXT SAFE STEP
GPT reviews this audit → answers 3 open questions → issues E1-S2 task card
(SAFE_AUTONOMOUS for deliver() noop implementation, GPT_REVIEW_REQUIRED before E1-S3)

---
*Packet prepared by: Claude Code | Date: 2026-06-24*
