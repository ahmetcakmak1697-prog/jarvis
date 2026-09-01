# LOOP-0C First Real Cargo Plan

> Date: 2026-07-08
> Branch: auto/opencode-deepseek
> Status: PLANNING / SPEC ONLY — NOT IMPLEMENTED

---

## 1. Status

- This is a planning/spec document only.
- No code implementation is approved by this document.
- LOOP-0C is not started until Ahmet explicitly approves a separate
  implementation task card.
- J0B/Piper/mic/audio/Telegram/scheduler remain out of scope for this
  document.
- This document does not approve auto-fix retry, commit automation, or
  autonomous next-task continuation.

---

## 2. Background

Chain so far:
- BLACKBOX-0 feature frozen (`fa204fc41`).
- LOOP-0A capability probe passed (`f2015d0d3`).
- LOOP-0S machine-gate spec committed (`aab936c8c`).
- LOOP-0B stub rehearsal committed (`1b03b6392`).
- LOOP-0B CONCERN accepted as non-blocking by Ahmet (`8cde149fe`).

LOOP-0B proved the real-data chain works once, end to end:
Claude Code → machine gate → Codex review-only → BLACKBOX event → Ahmet
human gate → Ahmet-approved commit.

LOOP-0B did not implement a runner/orchestrator. LOOP-0B did not start
J0B/Piper.

**Prior audit reference:** `docs/JARVIS_REPO_AUDIT.md` (SPRINT-J0A,
2026-07-04, head `ae3708f8e`) exists and is the prior read-only audit of
J0/J0B readiness state. It already maps:
- what J0 core files exist (`scripts/j0_live_status.py`,
  `scripts/j0_spike_b_latency_probe.py`,
  `scripts/j0_voice_latency_probe.py`, `scripts/_utf8io.py`),
- what J0A added (`scripts/j0_voice_adapters.py`,
  `scripts/j0_tts_adapters.py`, `scripts/j0_voice_loop.py`, with
  `PiperSubprocessAdapter` and `EdgeTTSAdapter` as **stubs only**),
- what is explicitly parked for J0B (real Piper subprocess, live Edge
  TTS fallback),
- existing test inventory (101 J0 tests + 69 proactive/E1 tests as of
  2026-07-04, plus J0A's new `test_j0_voice_adapters.py` /
  `test_j0_voice_loop.py` suites),
- open risks (SemanticRouter false positive on "nerede kaldık", Windows
  RealtimeSTT multiprocessing constraint, Piper GPL licensing boundary,
  UTF-8 coverage gaps in non-J0 scripts).

Future LOOP-0C implementation **must read that audit first** and
extend/validate it — it must not recreate the same inventory from
scratch. Adopt-over-build applies to prior Jarvis docs the same way it
applied to prior external tooling in LOOP-0A: reuse what already exists
before generating new discovery work.

---

## 3. Definition of "first real cargo"

"First real cargo" is:
- a small, real, useful change related to JARVIS/J0B readiness,
- narrow,
- reversible,
- testable,
- manually gated,
- based on existing project state (including
  `docs/JARVIS_REPO_AUDIT.md`) rather than duplicate discovery work.

It must **NOT** be:
- live microphone/audio capture,
- Piper/TTS runtime integration,
- Telegram delivery,
- scheduler/autonomous runtime,
- auto-fix retry,
- commit automation,
- broad architecture rewrite,
- package installation,
- secrets/.env work.

---

## 4. Recommended first cargo candidate

**J0B/Piper readiness inventory — read-only repo inspection +
docs/checklist report.**

The candidate should only:
- inspect existing repo files,
- first read `docs/JARVIS_REPO_AUDIT.md` from SPRINT-J0A if it exists,
- reference, validate, and extend/update that prior audit instead of
  duplicating the same inventory from scratch,
- identify what J0/J0B/Piper-related files already exist,
- identify what is already proven by earlier J0 voice spikes,
- identify what is missing before safe J0B/Piper runtime work,
- produce a small readiness report/checklist,
- avoid running microphone/audio/Piper,
- avoid changing runtime behavior,
- avoid adding dependencies,
- avoid tests/source changes unless separately approved.

No competing candidate is proposed as the main recommendation.

**Rejected/parked alternatives** (listed only, not recommended):
- Starting `PiperSubprocessAdapter` real implementation directly —
  rejected: skips the readiness-inventory step and touches runtime
  behavior before a gated checklist exists.
- Wiring live Edge TTS fallback — rejected: same reason, and it is
  explicitly parked for J0B in the prior audit.
- Running the existing J0 voice adapters against real mic/audio to
  "test readiness" — rejected: hard-banned mic/audio activation.

---

## 5. Allowed implementation shape for the future LOOP-0C implementation card

The future implementation card may allow only:
- read-only file inspection,
- read-only reference to `docs/JARVIS_REPO_AUDIT.md` if it exists,
- docs/checklist output,
- machine gate with existing tests,
- Codex real review-only on the actual diff,
- BLACKBOX event using `append_event()`,
- stop at Ahmet human gate,
- no commit until Ahmet approves.

The future implementation card must **NOT** allow:
- mic/audio/Piper runtime execution,
- Telegram/scheduler runtime,
- package install/update,
- .env/secrets access,
- auto-fix retry,
- commit automation,
- autonomous next task,
- runner/orchestrator implementation.

---

## 6. Machine gate binding

Future LOOP-0C implementation must follow, without redefinition:
- `automation/LOOP0_MACHINE_GATE_SPEC.md` §6 — machine gate PASS
  definition.
- `automation/LOOP0_MACHINE_GATE_SPEC.md` §7 — failure taxonomy.
- `automation/LOOP0_MACHINE_GATE_SPEC.md` §8 — Codex review gate.
- `automation/LOOP0_MACHINE_GATE_SPEC.md` §9 — Ahmet human gate.
- `automation/LOOP0_MACHINE_GATE_SPEC.md` §10 — BLACKBOX logging.
- `automation/LOOP0_MACHINE_GATE_SPEC.md` §11 — UTF-8/mojibake rules.

These rules are not redefined differently by this document.

---

## 7. Human gate

- Even if machine gate PASSes and Codex returns PASS, LOOP-0C
  implementation must stop at Ahmet human gate.
- No automatic commit.
- No automatic next task.
- No auto-fix retry.
- Any BLOCKER/CONCERN goes to Ahmet.
- Ahmet must explicitly approve any movement from readiness inventory
  to actual J0B/Piper runtime work.

---

## 8. BLACKBOX logging expectation for future implementation

Future LOOP-0C implementation should log one BLACKBOX event with:
- `event_name`: `LOOP0C_FIRST_REAL_CARGO`
- `cargo_name`: `J0B_PIPER_READINESS_INVENTORY`
- `status`: PASS / BLOCKER / CONCERN
- `human_gate_required`: true
- `prior_audit_reference`: `docs/JARVIS_REPO_AUDIT.md` if it exists
- `no_auto_fix_retry`: true
- `no_commit`: true
- `no_automatic_next_task`: true
- `no_mic_audio_piper_runtime`: true
- `no_telegram`: true
- `no_scheduler`: true
- `no_secret_env_access`: true

**This docs-only planning task does NOT add a BLACKBOX event.**

---

## 9. Exit criteria for this planning task

This docs-only task is complete when:
- `automation/LOOP0C_FIRST_REAL_CARGO_PLAN.md` exists.
- `automation/AUTONOMY_LOG.md` has one concise entry.
- `docs/JARVIS_REPO_AUDIT.md` was not modified.
- no BLACKBOX event is added.
- no source/test/runtime files are touched.
- no J0B/Piper/mic/audio/Telegram/scheduler files are touched.
- `git diff --check` is clean except benign CRLF/LF warnings.
- `git status` shows only the two allowed files changed.

---

## 10. Next step

- Ahmet reviews this plan.
- If approved, the next card must be the actual LOOP-0C implementation
  card for the J0B/Piper readiness inventory.
- That future card must perform read-only repo inspection and produce
  the readiness report/checklist.
- The next card must not be another docs-only planning or closure layer
  unless Ahmet explicitly requests one.
- Actual J0B/Piper runtime work remains a later separate decision.

---

*Prepared by: Claude Code | Date: 2026-07-08 | Sprint: LOOP-0C (plan only)*
