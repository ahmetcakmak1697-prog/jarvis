# E1_S1_DELIVERY_GAP_AUDIT.md — Proactive Delivery Gap Audit

> E1-S1 output. Read-only audit. No code changed.
> Date: 2026-06-24

---

## 1. What agents/proactive_delivery.py currently provides

Two exports only:

```python
@dataclass(frozen=True)
class DeliveryPlan:
    status: str           # "ready" | "deferred"
    channel: str          # "telegram" (only allowed)
    user_id: str
    task_id: str
    reason: str
    priority: str
    created_at: str       # ISO-8601 UTC
    cooldown_seconds: int
    requires_user_opt_in: bool

def create_delivery_plan(
    decision: ProactiveDecision, *,
    user_id: str, task_id: str, channel: str = "telegram", now: datetime | None = None
) -> DeliveryPlan | None:
    # Returns None for suppress, requires_user_opt_in=True
    # Returns DeliveryPlan(status="ready") for deliver
    # Returns DeliveryPlan(status="deferred") for defer
```

**No deliver(), no send(), no dispatch(), no network, no scheduler.**

---

## 2. Does it only create plans, or actually deliver?

**Only creates plans.** The docstring is explicit:
> "Pure and deterministic: no network, no Telegram, no scheduler, no runtime send."

---

## 3. Is there any deliver() / send() / dispatch() function?

**No.** Confirmed by reading the file and by existing test 11:
> `test_module_has_no_send_function` — asserts no function with "send" in its name exists.

No `deliver()` exists either. The module is a pure planning struct factory.

---

## 4. How is JARVIS_PROACTIVE_ENABLED used today?

**Only in agents/proactive_policy.py — not in proactive_delivery.py.**

```python
# proactive_policy.py
@staticmethod
def is_feature_enabled() -> bool:
    raw = os.environ.get("JARVIS_PROACTIVE_ENABLED", "").strip().lower()
    if raw in {"", "0", "false", "no", "off"}:
        return False
    return raw in {"1", "true", "yes", "on"}
```

When disabled (default), `ProactivePolicy.decide()` returns:
```python
ProactiveDecision(decision="suppress", reason="proactive_disabled", requires_user_opt_in=True)
```
→ `create_delivery_plan()` returns `None` (opt-in guard)
→ No plan, no send. Safe default-off confirmed.

---

## 5. Is Telegram currently wired into proactive delivery?

**No.** `tools/telegram_agent.py` has NO import of `proactive_delivery`, `proactive_policy`, or `proactive_core`. The proactive pipeline is completely isolated from Telegram.

`cmd_brief()` in telegram_agent.py does call `ProactiveCore().build_state()` — but this is **pull-based** (user sends `/brief` command), bypasses `ProactivePolicy` entirely, and has nothing to do with the ProactiveDelivery push path.

---

## 6. What Telegram sender interface exists in tools/telegram_agent.py?

A plain module-level function (not a class):

```python
def send_message(chat_id: int | str, text: str, parse_mode: str | None = None) -> None:
    payload = {"chat_id": str(chat_id), "text": text[:4000], "disable_web_page_preview": "true"}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    telegram_post("sendMessage", payload)
```

`telegram_post()` makes a live HTTP call to `https://api.telegram.org/bot{token}/sendMessage`.
`bot_token()` reads `TELEGRAM_BOT_TOKEN` from env — **raises RuntimeError if missing**.

**Key: send_message is injectable as a callable** — its signature `(chat_id, text)` is simple enough to wrap.

---

## 7. What tests already cover proactive delivery?

From `tests/test_proactive_delivery.py` — 12 tests:

| # | Test | What it guards |
|---|------|---------------|
| 1 | `test_deliver_plan_created` | deliver decision → ready plan |
| 2 | `test_suppress_returns_none` | suppress → None |
| 3 | `test_defer_creates_deferred_plan` | defer → deferred plan |
| 4 | `test_delivery_plan_schema` | all fields present and correct |
| 5 | `test_unknown_channel_fails_closed` | invalid channel → ValueError |
| 6 | `test_missing_user_id_fails_closed` | empty user_id → ValueError |
| 7 | `test_missing_task_id_fails_closed` | empty task_id → ValueError |
| 8 | `test_requires_user_opt_in_returns_none` | opt-in required → None |
| 9 | `test_no_network_imports_in_module` | no urllib/requests/httpx/telegram imports |
| 10 | `test_no_scheduler_or_background_imports_in_module` | no threading/asyncio/schedule |
| 11 | `test_module_has_no_send_function` | **no function with "send" in name** |
| 12 | `test_created_at_is_deterministic_with_now` | injectable clock works |

**Critical: Test 11 will FAIL if any function named `send_*()` is added to proactive_delivery.py.**
A `deliver()` function would pass (no "send" in name).

---

## 8. Smallest safe next implementation step (E1-S2)

Add one function to `agents/proactive_delivery.py`:

```python
def deliver(plan: DeliveryPlan, sender_fn=None) -> bool:
    """Execute a ready DeliveryPlan. Returns True if sent, False otherwise.
    
    sender_fn: callable(chat_id: str, text: str) -> None
               None = noop (default-off, safe for tests)
    """
    if plan.status != "ready":
        return False
    if sender_fn is None:
        return False
    sender_fn(plan.user_id, _format_brief(plan))
    return True
```

And a `_format_brief(plan: DeliveryPlan) -> str` helper.

**Why this is safe:**
- No network imports in the module (tests 9, 10 still pass)
- No "send" in the function name (test 11 still pass)
- `sender_fn=None` default → noop → all existing tests still pass
- Real send only happens when caller explicitly passes a sender_fn
- Fully injectable and testable without Telegram

**New tests needed in test_proactive_delivery.py:**
- deliver() with sender_fn=None returns False (noop)
- deliver() with deferred plan returns False
- deliver() with ready plan + fake sender calls sender exactly once
- deliver() with ready plan passes correct user_id to sender
- deliver() with ready plan passes non-empty text to sender

---

## 9. Which parts require GPT review?

**E1-S2** (GPT_REVIEW_REQUIRED): Adding `deliver()` to proactive_delivery.py is the first step toward runtime delivery. Even though it defaults to noop, it's the logical boundary between planning and execution. GPT should review the function signature and test coverage before it proceeds to E1-S3.

**E1-S3** (GPT_REVIEW_REQUIRED): Wiring real `send_message` as sender_fn requires:
1. GPT to confirm the composition root: add to `telegram_agent.py`'s `_build_*` pattern, or a new `agents/proactive_runtime.py`?
2. GPT to clarify **user_id → Telegram chat_id mapping**: `DeliveryPlan.user_id` is an arbitrary string. `telegram_agent.send_message(chat_id, text)` needs the real Telegram chat_id. Are these the same value? Where is the mapping?
3. GPT to confirm the message format (plain text, Telegram HTML, etc.)

---

## 10. Which parts require human live testing?

**E1-S4** (HUMAN_REQUIRED):
- Setting `JARVIS_PROACTIVE_ENABLED=1` in `.env`
- Providing real Telegram chat_id for `user_id` in the proactive call
- Confirming the Telegram message arrives on Ahmet's phone
- Validating tone, cooldown, and mute behavior in real use

**E1-S5** (HUMAN_REQUIRED):
- Deciding the scheduler design (cron, asyncio loop, FastAPI background task, external trigger)

---

## Open Questions for GPT

1. **Composition root**: Where should the proactive push pipeline be assembled?
   - Option A: Inside `telegram_agent.py` alongside `_build_assistant_executor()`
   - Option B: New file `agents/proactive_runtime.py`

2. **user_id → chat_id mapping**: `DeliveryPlan.user_id` is a string. How does it map to the Telegram `chat_id`? Is it read from `TELEGRAM_ALLOWED_USER_IDS`? Is it always Ahmet's single chat_id?

3. **Message format**: Should `deliver()` format the message using `cmd_brief()`, or produce its own text from `DeliveryPlan` fields?

4. **deliver() text content**: If we use `DeliveryPlan` fields only (not `ProactiveCore.build_state()`), the message will be a sparse summary. If we want the full `/brief` style output, we need to call `cmd_brief()`. Which is correct for a push notification?

---
*Written by: Claude Code (E1-S1) | Date: 2026-06-24 | No code changed*
