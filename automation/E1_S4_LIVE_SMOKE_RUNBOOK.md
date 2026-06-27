# E1-S4 Live Telegram Smoke Runbook

**Status:** PENDING AHMET APPROVAL  
**Gate:** HUMAN_REQUIRED — do not proceed without explicit approval in session  
**Date prepared:** 2026-06-28

---

## Purpose

E1-S4 is the first and only controlled live Telegram message sent by JARVIS.
It verifies that the delivery path works end-to-end before any scheduled
automation is enabled.

All E1-S6A–E safety guards have passed Codex review. This runbook is the
final step before live delivery can be considered safe to schedule.

---

## Preconditions (all must be true before proceeding)

| Guard | Status |
|-------|--------|
| E1-S6A: dry-run CLI + live guard | DONE (cc0072ac5, c8eee9a84) |
| E1-S6B: DeliveryResult struct | DONE (a53001577, 648b74455) |
| E1-S6C: scheduler docs + template | DONE (3de2e1035, 4f6a5b6e0) |
| E1-S6D: live-mode guard regression tests | DONE (b4670036b) |
| E1-S6E: throttle/cooldown guard | DONE (c9c7d75b3, 399587609) |
| `--live` blocked until E1-S4 wiring | VERIFIED |
| `JARVIS_PROACTIVE_ENABLED=0` default | VERIFIED |

---

## Step 1 — Pre-flight (Ahmet runs before approving)

Run from repo root (`C:\Users\Ahmedov\Desktop\Jarvis\jarvis-agent-auto`):

```powershell
# 1a. Full regression suite must pass
py -3.11 -m pytest tests/test_e1_6e_throttle_guard.py tests/test_e1_6d_live_guard.py tests/test_e1_6a_proactive_runner.py tests/test_e1_6b_delivery_result.py tests/test_proactive_delivery.py tests/test_proactive_runtime.py -q --tb=short

# 1b. Dry-run still exits 0
py -3.11 -m agents.proactive_runner

# 1c. Live still blocked before E1-S4 wiring
py -3.11 -m agents.proactive_runner --live
```

**Expected results:**

- `1a`: 124/124 PASS (or more if new tests added)
- `1b`: exit 0, JSON output with `"dry_run": true, "sent": false`
- `1c`: exit 1, stderr JSON with `"NOT IMPLEMENTED"` in error field

**If any pre-flight fails: ABORT. Do not proceed.**

---

## Step 2 — Verify credentials (Ahmet, do not share output)

Before approving live send, verify you have the following in your environment
(or `.env` file that is NOT in git):

- `TELEGRAM_BOT_TOKEN` — your JARVIS bot token
- `TELEGRAM_CHAT_ID` — your personal Telegram chat ID (from BotFather `/getid` or `@userinfobot`)

Check (run in a terminal only, never paste output into chat):

```powershell
echo $env:TELEGRAM_BOT_TOKEN   # should show token, not empty
echo $env:TELEGRAM_CHAT_ID     # should show numeric chat ID
```

**If either is missing or blank: ABORT. Set them before proceeding.**

---

## Step 3 — What E1-S4 wiring will look like (review before approving)

Live Telegram delivery in JARVIS uses injection — no hardcoded credentials in code:

```python
# Conceptual wiring (not yet implemented in runner):
from agents.proactive_telegram_adapter import (
    make_static_chat_id_resolver,
    make_telegram_sender_factory,
)
import os

chat_id = os.environ["TELEGRAM_CHAT_ID"]
bot_token = os.environ["TELEGRAM_BOT_TOKEN"]

# A real send_message_fn will use python-telegram-bot or requests
# to POST to api.telegram.org — not yet wired in runner

resolver = make_static_chat_id_resolver({"ahmet": chat_id})
# sender_factory wraps the actual HTTP call
```

The adapter seam (`agents/proactive_telegram_adapter.py`) is already implemented
and tested. The missing piece is the actual `send_message_fn` that calls the
Telegram Bot API, and wiring it into `run_once()` behind a live-mode path.

**Claude must implement the live send function and wire it before E1-S4 can run.**
**This wiring must be reviewed and approved by Ahmet before it is executed.**

---

## Step 4 — Manual approval gate

Ahmet must explicitly say one of the following in the chat session before
Claude writes any live-send code or runs any live command:

> "Proceed with E1-S4 live wiring."  
> "Approve E1-S4."  
> "Wire live Telegram and send the smoke test."

A general "continue" or "go ahead" is NOT sufficient — the approval must
be specific to E1-S4 live send.

---

## Step 5 — Live smoke message

Once wiring is implemented, reviewed, and Ahmet approves execution:

- Send exactly ONE message to Ahmet's chat
- Message text (or equivalent):

  ```
  JARVIS E1-S4 live Telegram smoke test. If you received this, live delivery path works.
  ```

- Do NOT include any token, chat ID, or secret in the message
- Do NOT retry if first attempt fails — investigate before retrying
- Do NOT send to any chat other than Ahmet's known personal chat

---

## Step 6 — Confirmation evidence to collect

After Ahmet confirms receipt on phone:

| Evidence | Notes |
|----------|-------|
| Timestamp (UTC) | From DeliveryResult.ts or run_once() output |
| Command used | Exact CLI command or Python snippet |
| git status | Must be clean |
| DeliveryResult | Full JSON from run_once() output |
| Phone confirmation | Screenshot or text confirmation from Ahmet |
| Messages sent count | Must be exactly 1 |

---

## Step 7 — Completion

E1-S4 is marked done **only after**:

1. Ahmet confirms message received on phone
2. Evidence recorded in this file (add evidence section below)
3. Claude updates `roadmap_state.json` E1-S4 status to `"done"`
4. Commit: `docs(automation): mark E1-S4 done after live Telegram smoke`

---

## Rollback / Abort Conditions

Stop immediately and do NOT retry if:

- Any pre-flight test fails
- `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` is missing
- Telegram API returns an error
- More than one message is sent accidentally
- Unexpected network activity is observed
- Any safety invariant from E1-S6A–E is violated

---

## What happens after E1-S4

After E1-S4 is confirmed:

1. The `--live` gate in `run_once()` can be replaced with actual live delivery
2. Windows Task Scheduler task can be created using `scripts/create_jarvis_task.ps1 -Apply`
3. Scheduled dry-run can be changed to scheduled live run
4. `JARVIS_PROACTIVE_ENABLED` can be set to `1` in the environment

None of these steps happen automatically — each requires explicit approval.

---

## Evidence (fill in after E1-S4 completion)

```
Status:       PENDING
Completed at: —
Command:      —
git status:   —
Messages sent: 0
Ahmet confirmed: NO
```

---

*Prepared by: Claude Code | Date: 2026-06-28*
