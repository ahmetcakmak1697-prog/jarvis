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

Check presence and length without revealing values (run in a terminal, never paste output into chat):

```powershell
$tok = $env:TELEGRAM_BOT_TOKEN
if ($tok) { Write-Host "TELEGRAM_BOT_TOKEN: SET hidden length=$($tok.Length)" } else { Write-Host "TELEGRAM_BOT_TOKEN: MISSING" }
Remove-Variable tok

$cid = $env:TELEGRAM_CHAT_ID
if ($cid) { Write-Host "TELEGRAM_CHAT_ID: SET hidden length=$($cid.Length)" } else { Write-Host "TELEGRAM_CHAT_ID: MISSING" }
Remove-Variable cid
```

Expected output (values hidden):
```
TELEGRAM_BOT_TOKEN: SET hidden length=46
TELEGRAM_CHAT_ID: SET hidden length=10
```

**Do not echo or print raw token / chat_id values. If either is MISSING: ABORT.**

---

## Step 3 — Wiring implemented (review before approving execution)

The E1-S4 smoke path is now wired in `agents/proactive_runner.py`.

Files added/changed:
- `agents/e1_s4_smoke_sender.py` — HTTP sender factory using stdlib `urllib` only
- `agents/proactive_runner.py` — `run_e1_s4_smoke()` function + `--e1-s4-smoke` CLI flag
- `tests/test_e1_s4_live_smoke_wiring.py` — 21 tests (all mocked, no real sends)

How it works:
- `run_e1_s4_smoke()` reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from env
- If either is missing → fail closed, no send
- Sends exactly one message via injected or HTTP sender
- Token and chat_id values never appear in output (only SET/NOT SET hints)
- No retry loop, no scheduler, no .env file touch

The existing `--live` flag **remains blocked** (raises RuntimeError / exits 1).
Only `--e1-s4-smoke` sends a message.

**Exact command Ahmet must approve for execution:**
```powershell
py -3.11 -m agents.proactive_runner --e1-s4-smoke
```

---

## Step 4 — Manual approval gate

Ahmet must explicitly say one of the following in the chat session before
Claude executes the live smoke command:

> "Run the E1-S4 smoke now."  
> "Execute --e1-s4-smoke."  
> "Send the E1-S4 smoke message."

A general "continue" or "go ahead" is NOT sufficient — the approval must
be specific to executing the smoke send.

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

## Evidence — COMPLETED

```
Status:           DONE
Completed at:     2026-06-27T22:51:38.969829+00:00 (UTC)
Command:          py -3.11 -m agents.proactive_runner --e1-s4-smoke
Wiring commit:    a39db4568 (fix(proactive): sanitize E1-S4 smoke errors)
Codex PASS:       a39db4568 — 33 smoke wiring tests + 157 full regression, all PASS
Messages sent:    1 (exactly one)
Ahmet confirmed:  YES — received on phone

Message text (exact):
  JARVIS E1-S4 live Telegram smoke test. If you received this, live delivery path works.

CLI output (token/chat_id values hidden):
  TELEGRAM_BOT_TOKEN: SET hidden length=46
  TELEGRAM_CHAT_ID: SET hidden length=10
  {"sent": true, "reason": "sent", "token": "SET hidden length=46",
   "chat_id": "SET hidden length=10",
   "message": "JARVIS E1-S4 live Telegram smoke test. If you received this, live delivery path works.",
   "ts": "2026-06-27T22:51:38.969829+00:00"}

Token exposed:    NO
Chat ID exposed:  NO
Retry:            NO
Scheduler:        NO
Background loop:  NO
git status:       clean
```

**Do not run --e1-s4-smoke again. One smoke per E1-S4 gate. Next step: explicit approval for scheduler or live delivery activation.**

---

*Prepared by: Claude Code | Date: 2026-06-28 | Completed: 2026-06-27*
