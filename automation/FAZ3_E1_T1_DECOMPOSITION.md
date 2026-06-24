# FAZ3_E1_T1_DECOMPOSITION.md — Human-Gate Decomposition

> AUTO-1D output. Read-only analysis. No code changed.
> Purpose: break FAZ-3-E1 and FAZ-T1 into sub-tasks with clear autonomy classifications
> so GPT can issue safe task cards one at a time.

---

## Current State Summary

| Item | File | Status |
|------|------|--------|
| ProactivePolicy.decide() | agents/proactive_policy.py | DONE — delivers/suppress/defer logic, cooldown, mute, DND |
| JARVIS_PROACTIVE_ENABLED guard | agents/proactive_policy.py | DONE — env flag, default off |
| DeliveryPlan struct | agents/proactive_delivery.py | DONE — frozen dataclass, planning only |
| create_delivery_plan() | agents/proactive_delivery.py | DONE — returns DeliveryPlan, no executor |
| deliver() runtime function | agents/proactive_delivery.py | **MISSING** |
| Telegram send wiring | tools/telegram_agent.py | **NOT WIRED** to proactive path |
| Scheduler / background loop | — | **NOT BUILT** |
| tests/test_tr_quality.py | tests/ | **NOT CREATED** |

---

## FAZ-3-E1: Proaktif Davranış Motoru

### E1-S1 — Delivery gap audit (read-only spec)
**Classification: SAFE_AUTONOMOUS**

- Read `agents/proactive_delivery.py`, `agents/proactive_policy.py`, `tools/telegram_agent.py`
- Identify exact interface: what signature does `deliver()` need?
- Identify what `TelegramAgent` currently exposes for a send call
- Output: short spec written to `automation/CLAUDE_REPORT.md` — no code changes
- Allowed files: read-only
- Tests: none
- Stop condition: if telegram_agent.py requires `.env` / live token to construct, stop and flag

### E1-S2 — Add injectable `deliver()` with noop guard
**Classification: GPT_REVIEW_REQUIRED** (first runtime delivery function)

- Add `deliver(plan: DeliveryPlan, sender=None)` to `agents/proactive_delivery.py`
- `sender=None` → noop (no Telegram call, fully testable without network)
- Raise `RuntimeError` if `plan` is not a `DeliveryPlan`
- Extend `tests/test_proactive_delivery.py` with:
  - noop path (no sender) never raises
  - sender called exactly once when provided and plan is deliver-type
  - non-deliver plan does not call sender
- Allowed files: `agents/proactive_delivery.py`, `tests/test_proactive_delivery.py`
- Tests: `pytest tests/test_proactive_delivery.py -q --tb=short`
- GPT must review before proceeding to E1-S3 (no live send yet, but first wiring step)

### E1-S3 — Wire deliver() to real TelegramAgent sender
**Classification: GPT_REVIEW_REQUIRED** (first real push behavior)

- Create `TelegramSender` wrapper in `tools/telegram_agent.py` or thin adapter
- Wire `deliver(plan, sender=TelegramSender())` in composition root
- Guard: only constructed when `JARVIS_PROACTIVE_ENABLED=1`
- Default composition path: sender=None (noop), preserving existing default-off invariant
- Allowed files: `tools/telegram_agent.py`, composition entry point (TBD by GPT)
- Tests: integration test with fake sender, assert no real network call in tests
- Human gate: do NOT enable `JARVIS_PROACTIVE_ENABLED=1` in tests or source

### E1-S4 — Live proactive smoke (Ahmet opt-in)
**Classification: HUMAN_REQUIRED**

- Ahmet sets `JARVIS_PROACTIVE_ENABLED=1` in `.env`
- Ahmet triggers a proactive alert (manually or via test harness)
- Ahmet confirms Telegram message received on phone
- Ahmet signs off on cooldown/mute/rate-limit behavior in real use
- Claude cannot run this step — requires live Telegram token, `.env` edit, and human judgment

### E1-S5 — Scheduler / background loop design (future)
**Classification: HUMAN_REQUIRED (design gate before implementation)**

- Design decision: cron-style, asyncio loop, or external trigger?
- Requires Ahmet + GPT alignment before any code
- Not yet a Claude task — add to HUMAN_NEEDED.md when E1-S4 is done

---

## FAZ-T1: Türkçe Kalite Track'i

### T1-S1 — Create tests/test_tr_quality.py skeleton
**Classification: SAFE_AUTONOMOUS**

- Create `tests/test_tr_quality.py`
- Deterministic checks only (no subjective judgment):
  - `_fold_tr` round-trips for known Türkçe characters (İ, ı, ğ, ş, ç, ö, ü)
  - Known assistant output strings don't contain mojibake artifacts
  - `"İ".lower()` issue is handled (combining dot regression guard)
  - ASCII-fold does not lose Turkish codepoints
- Allowed files: `tests/test_tr_quality.py`
- Tests: `pytest tests/test_tr_quality.py -q --tb=short`
- Regression: `pytest tests/ -k fold_tr -q --tb=short`

### T1-S2 — Ahmet quality sign-off
**Classification: HUMAN_REQUIRED**

- Ahmet runs JARVIS with real Turkish queries
- Evaluates: natural phrasing, correct diacritics, no broken output
- Subjective criterion — cannot be tested with code
- Ahmet signs off → FAZ-T1 marked done in roadmap_state.json

---

## Recommended Execution Order

```
E1-S1  (SAFE_AUTONOMOUS)        ← next Claude task
E1-S2  (GPT_REVIEW_REQUIRED)    ← after E1-S1 accepted
T1-S1  (SAFE_AUTONOMOUS)        ← can run in parallel with E1-S2 if GPT approves
E1-S3  (GPT_REVIEW_REQUIRED)    ← after E1-S2 accepted
E1-S4  (HUMAN_REQUIRED)         ← after E1-S3 accepted
T1-S2  (HUMAN_REQUIRED)         ← after T1-S1 + Ahmet has bandwidth
E1-S5  (HUMAN_REQUIRED/design)  ← future, after E1-S4 done
```

---
*Written by: Claude Code (AUTO-1D) | Date: 2026-06-24 | No code changed*
