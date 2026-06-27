# CODEX_REVIEW_REQUEST.md — Review Request

---

## E1-S6A CLOSED — PASS (2026-06-27)
## E1-S6B CLOSED — PASS (2026-06-27)
## E1-S6C CLOSED — PASS (2026-06-28)
## E1-S6D CLOSED — PASS (2026-06-28)
## E1-S6E CLOSED — PASS (2026-06-28)

Commits reviewed and closed:
- E1-S6A: c8eee9a84, cc0072ac5
- E1-S6B: 648b74455, a53001577
- E1-S6C: 4f6a5b6e0, 3de2e1035
- E1-S6D: b4670036b
- E1-S6E: c9c7d75b3, 399587609

---

## Status
PENDING_CODEX_REVIEW — E1-S4 wiring BLOCKER fix

## Branch
auto/opencode-deepseek

## Commits to Review

```
0739333da  feat(proactive): prepare E1-S4 Telegram smoke wiring  (initial)
(fix hash TBD — commit in progress)  fix(proactive): sanitize E1-S4 smoke errors  (BLOCKER fix)
```

## BLOCKER Fix Summary

Codex returned BLOCKER on 0739333da. Four issues addressed:

### BLOCKER 1 — str(exc) exposes secrets (FIXED)

`agents/proactive_runner.py` `run_e1_s4_smoke()`:
- `"error": str(exc)` → `"error": type(exc).__name__`
- Exception message (which may contain token/chat_id) never reaches output
- Example: `RuntimeError("error: token=abc123")` → result has `"error": "RuntimeError"`

### BLOCKER 2 — HTTP sender ignored Telegram ok field (FIXED)

`agents/e1_s4_smoke_sender.py` `send_fn`:
- Added try/except around `urlopen` → re-raises `RuntimeError("telegram_send_failed")`
  (original exception swallowed — its message may contain the token-bearing URL)
- Parses JSON response body; malformed → `RuntimeError("telegram_response_invalid")`
- Checks `parsed.get("ok")`; if falsy → `RuntimeError("telegram_api_error")`
- No retry, exactly one HTTP request

### BLOCKER 3 — Runbook instructed `echo $env:TELEGRAM_BOT_TOKEN` (FIXED)

`automation/E1_S4_LIVE_SMOKE_RUNBOOK.md` Step 2:
- Removed `echo $env:TELEGRAM_BOT_TOKEN` and `echo $env:TELEGRAM_CHAT_ID`
- Replaced with hidden presence/length check:
  `if ($tok) { Write-Host "TELEGRAM_BOT_TOKEN: SET hidden length=..." }`
- Raw values never displayed

### BLOCKER 4 — Tests did not cover secret-bearing failures or response validation (FIXED)

`tests/test_e1_s4_live_smoke_wiring.py`: 21 → 33 tests (+12 new)

New tests for `run_e1_s4_smoke()`:
- `test_secret_bearing_exception_does_not_expose_token` — token absent from result
- `test_secret_bearing_exception_does_not_expose_chat_id` — chat_id absent
- `test_error_field_is_type_name_not_exception_message` — `"error": "RuntimeError"`
- `test_send_error_reason_is_send_error` — reason field correct
- `test_send_error_sent_is_false` — sent=False

New tests for `make_telegram_http_send_fn`:
- `test_concrete_sender_ok_true_succeeds` — `{"ok": true}` → no raise
- `test_concrete_sender_ok_false_raises` — `{"ok": false}` → `telegram_api_error`
- `test_concrete_sender_malformed_json_raises` — → `telegram_response_invalid`
- `test_concrete_sender_network_exception_raises_sanitized` — → `telegram_send_failed`
- `test_concrete_sender_exception_does_not_expose_token` — re-raised exc has no token
- `test_concrete_sender_urlopen_called_exactly_once_no_retry` — called once
- `test_concrete_sender_request_params_correct` — chat_id and text in body

## Tests Run

```
py -3.11 -m pytest tests/test_e1_s4_live_smoke_wiring.py -q --tb=short
  -> 33/33 PASS

py -3.11 -m pytest [full 7-suite] -q --tb=short
  -> 157/157 PASS

py -3.11 -m agents.proactive_runner         -> exit 0, dry_run=true
py -3.11 -m agents.proactive_runner --live  -> exit 1, NOT IMPLEMENTED
py -3.11 -m json.tool roadmap_state.json    -> VALID
git diff --check -> clean

No Telegram message sent.
```

## Review Verdict Expected
PASS / CONCERN / BLOCKER

---

*Prepared by: Claude Code | Date: 2026-06-28*
