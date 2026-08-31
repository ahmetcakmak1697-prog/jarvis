# LOOP-0D/J0B Safety Contract Before Runtime

> Date: 2026-07-10
> Branch: auto/opencode-deepseek
> Status: SAFETY CONTRACT — NOT IMPLEMENTED, NOT A RUNTIME APPROVAL

---

## 1. Status

- This is a safety contract document.
- It does not implement J0B/Piper runtime.
- It does not run microphone/audio/Piper/Edge TTS.
- It does not approve runtime execution.
- It does not approve auto-fix retry, commit automation, or autonomous
  next-task continuation.
- Any future runtime spike (fake/non-mic or otherwise) requires separate
  explicit Ahmet approval — this document only defines what such a future
  card may request; it does not start one.

---

## 2. Background and evidence chain

Chain so far:
- BLACKBOX-0 feature frozen (`fa204fc41`).
- LOOP-0A capability probe confirmed (`f2015d0d3`).
- LOOP-0S machine-gate spec committed (`aab936c8c`).
- LOOP-0B stub rehearsal committed (`1b03b6392`), CONCERN accepted as
  non-blocking (`8cde149fe`).
- LOOP-0C first-real-cargo plan (`e329b9861`).
- BLACKBOX redaction type-safe bugfix (`dc453bcb`), fixed across three
  Ahmet-reviewed iterations (type-narrowing → numeric-secret carve-out →
  fail-safe known-safe-preserve inversion), ending Codex PASS.
- LOOP-0C readiness inventory recorded (`be80b6462`).

**Current BLACKBOX state** (`automation/BLACKBOX.jsonl`, read-only —
verified via `validate_log`: `ok=True, event_count=4, last_sequence=4`):

| sequence | event_name | event_type | status |
|---|---|---|---|
| 1 | `LOOP0A_CAPABILITY_PROBE` | `risk_noted` | PASS |
| 2 | `LOOP0B_STUB_CHAIN_REHEARSAL` | `codex_verdict` | CONCERN (accepted non-blocking by Ahmet) |
| 3 | `LOOP0C_FIRST_REAL_CARGO` | `codex_verdict` | CONCERN — **historical**: contains the `no_secret_env_access` redaction false-positive (`"[REDACTED]"` instead of `true`) that motivated the `dc453bcb` bugfix |
| 4 | `BLACKBOX_REDACTION_TYPE_SAFE_VERIFICATION` | `correction_verification` | PASS — append-only verification that post-`dc453bcb` redaction preserves `no_secret_env_access` as a real boolean |

**Sequence=3 was not rewritten or deleted.** It remains historical evidence
of the bug, per the project's append-only BLACKBOX discipline. Sequence=4
is a later append-only correction/verification event, not a rewrite of
sequence=3. This contract does not touch `automation/BLACKBOX.jsonl` in
any way.

This contract's input is the LOOP-0C readiness inventory
(`automation/LOOP0C_J0B_PIPER_READINESS_INVENTORY.md`), specifically:
- §3: `PiperSubprocessAdapter.speak()` and `EdgeTTSAdapter.speak()` are
  still stubs, unconditionally raising `NotImplementedError`.
- §5: gaps before safe J0B/Piper runtime work, including the missing
  explicit runtime guard analogous to `proactive_runner.py --live`.
- §5A: the Home Assistant/Wyoming/Whisper/Piper/Ollama adopt-vs-build
  question, and the Letta documentation conflict.
- §7: this contract is the recommended next card, chosen over a fake-input
  runtime spike specifically because the safety contract did not yet exist.

---

## 3. Runtime boundary

### Remains forbidden until a later explicit card

- Microphone/audio capture (any real audio device).
- Piper subprocess execution (spawning the actual `piper` binary).
- Edge TTS execution (any real network call to the cloud TTS fallback).
- Speaker/audio playback of any kind.
- Wake-word runtime loop (`RealtimeSTTAdapter` real listen path).
- Home Assistant Assist / Wyoming integration of any kind.
- Telegram/scheduler/autonomous delivery.
- Any persistent background service or always-on process.

### May be allowed in the next narrow card (not approved here)

- Fake/non-mic input only (`FakeSTTAdapter`, static text, or equivalent).
- No real audio device.
- No Piper process.
- No Edge TTS network call.
- No Home Assistant call.
- No scheduler/Telegram.
- No `.env`/secrets.

---

## 4. J0B/Piper safety contract

These gates must all be satisfied and reviewed before `NotImplementedError`
is removed from `PiperSubprocessAdapter`, `EdgeTTSAdapter`, or any
equivalent runtime stub.

### Required before real Piper runtime

- Written command allowlist (`build_piper_cmd()`'s argv shape is
  documented and fixed — no free-form command construction).
- Explicit process timeout on the subprocess call.
- No `shell=True` unless separately justified and reviewed.
- Fixed executable path / no user-controlled command injection (model
  path and executable must not be built from unsanitized external input).
- No automatic model download — model files remain a manual, Ahmet-driven
  step, per `docs/THIRD_PARTY_VOICE.md`.
- No audio playback during tests — tests exercise `build_piper_cmd()` and
  structured results only, never real audio.
- Fake-input test path must exist and pass before any real-input path is
  attempted.
- Subprocess stdout/stderr captured safely (no raw blob dumped into
  BLACKBOX or logs — consistent with the existing `_FORBIDDEN_EVIDENCE_KEYS`
  guard in `agents/blackbox_log.py`).
- Failure returns a structured `TTSResult`/error, never an uncaught crash.
- No secrets/env read by the Piper adapter path.
- No network call from the Piper subprocess path (Piper is local-only by
  design).
- Ahmet explicit runtime approval, separate from this contract.

### Required before real Edge TTS runtime

- Default-off (current stub behavior preserved as the default).
- No network calls in tests — tests use `FakeTTSAdapter` only.
- Explicit cloud/provider approval from Ahmet before any real network call.
- No automatic fallback to a paid/cloud provider without an explicit
  policy decision (mirrors the existing local-first cascade discipline in
  `agents/local_first_router.py`).
- Clear privacy warning surfaced to Ahmet before enabling (Edge TTS sends
  text to a cloud service).
- Ahmet explicit approval, separate from this contract.

### Required before real microphone/audio capture

- Explicit real-mic flag (e.g. `--real-mic`), mirroring the
  `JARVIS_J0_REALTIME_ENABLED` + `--real-mic` pattern already described in
  the prior J0A audit.
- Ambient/noise gate precheck before any recording begins.
- Recording duration cap (no unbounded listen).
- Device name logging (so Ahmet can see which physical device was used).
- No background always-listening mode.
- User-visible start/stop indication.
- Ahmet explicit approval, separate from this contract.

---

## 5. Fake/non-mic input contract

The only acceptable next runtime-adjacent step is:

**"J0B fake/non-mic runtime spike"**

Allowed, if and when that future card is separately approved:
- `FakeSTTAdapter` or static text input.
- `FakeTTSAdapter` or non-playing text output.
- No microphone.
- No Piper.
- No Edge TTS.
- No speaker playback.
- No network.
- No scheduler.
- No Telegram.
- No `.env`/secrets.
- Tests only.
- Machine gate + Codex review-only + Ahmet human gate, per
  `automation/LOOP0_MACHINE_GATE_SPEC.md`.

**This fake/non-mic spike is still not approved by this document.** This
section only defines what a future implementation card may request; it
does not start that card, choose it automatically, or authorize any code
change.

---

## 6. Home Assistant / Wyoming adopt-vs-build decision

Based only on existing repo docs (no web research performed in this task
or in the LOOP-0C inventory it draws from):

- `docs/JARVIS_BACKLOG.md` frames Home Assistant + Wyoming as a **later,
  separate-hardware front (J2/J5)**: "HA dedicated box provisioned (NOT
  this Windows PC). Wyoming protocol confirmed working on that box,"
  targeting "our Whisper/Piper/Ollama served via Wyoming."
- `docs/JARVIS_HARVEST_MAP.md` lists "Home Assistant / Wyoming" under
  STUDY/DEFERRED: "J2/J5 — dedicated box... Never on this Windows PC."
- `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md` marks "Wyoming +
  faster-whisper + Piper + openWakeWord" and "Home Assistant + ESPHome +
  Node-RED" as **Adopt** candidates, with a milestone path (V0 wake word →
  V1 STT → M1 "Home Assistant + Wyoming Assist").
- Ollama is already adopted in this repo, but as the **local-first LLM
  provider** (`agents/ollama_executor.py`) — a different integration point
  than "Ollama served via Wyoming."

**Net reading:** the repo's own strategy docs already lean toward
eventually routing home-control voice through Home Assistant + Wyoming,
but scope it as a **later, separate-hardware front (J2/J5)**, distinct
from the current J0/J0B milestone, which is explicitly scoped to this
Windows PC only. The two framings — Windows-local J0/J0B now, HA/Wyoming
later on separate hardware — have not been explicitly reconciled by Ahmet
as a single decision, and the LOOP-0C inventory named this exact gap.

**Required decision (not made here):**
Before implementing custom J0B/Piper runtime, Ahmet must decide whether
this is:

- **A)** Windows-local J0 voice milestone only, separate from later Home
  Assistant/Wyoming home-control stack.
- **B)** replaced/deferred in favor of Home Assistant Assist/Wyoming/Piper
  adoption.
- **C)** hybrid: Windows-local J0 for personal PC control, HA/Wyoming for
  the home-control voice layer.

**Advisory-only recommendation:** the inspected docs (`JARVIS_BACKLOG.md`,
`JARVIS_HARVEST_MAP.md`, `JARVIS_v5_REALITY_OS_ROADMAP.md`) consistently
treat J0/J0B and HA/Wyoming as separate fronts on separate hardware rather
than as competing implementations of the same milestone, which supports
**option (C) hybrid** as the path already implied by existing repo
strategy. This is advisory only — it is not a final architecture decision,
it does not rewrite the roadmap, and Ahmet may choose A or B instead.

---

## 7. Letta documentation conflict decision

Read only (no edits made to either document):
- `docs/JARVIS_HARVEST_MAP.md`
- `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md`

**Conflict summary:**
- `docs/JARVIS_HARVEST_MAP.md` (REJECT table): **"Letta runtime |
  Rejected."**
- `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md`: marks **"Letta
  (MemGPT)"** as **"verified, adopt candidate"** for the memory-layer
  front, alongside "Graphiti / Mem0."
- `docs/JARVIS_v5_MASTER_ROADMAP.md` references "Mem0" and "Letta /
  MemGPT" as architecture references, without a clear commitment either
  way.

These two documents directly disagree on whether Letta is rejected or an
adopt candidate. This is a pre-existing conflict, first surfaced by the
LOOP-0C readiness inventory (§5A), not something introduced by this task.

**Provisional decision for safety (this contract's ruling until Ahmet
resolves the conflict):**
- Letta runtime is **NOT approved** as a runtime adoption.
- The Letta/MemGPT tiered-memory pattern (core/recall/archival) **may be
  used as a design reference only** — reading its architecture for ideas
  is not the same as running it.
- Lightweight memory service/layer options such as Mem0/Graphiti **remain
  study candidates**, not approved runtime adoptions.
- Any actual memory runtime/framework adoption (Letta, Mem0, Graphiti, or
  otherwise) requires a separate explicit Ahmet decision and an updated
  single source-of-truth doc — it must not be decided implicitly by
  whichever of the two conflicting docs a future implementer happens to
  read first.

**Required follow-up:** a later decision-cleanup card must reconcile
`docs/JARVIS_HARVEST_MAP.md` and
`docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md` on the Letta question,
unless Ahmet explicitly chooses to resolve it as part of this LOOP-0D
follow-up instead. Neither document is edited by this task.

---

## 8. Human gate and approval rules

- Even if a future fake/non-mic spike's machine gate and Codex review both
  PASS, it must still stop at Ahmet human gate before commit.
- The runtime-spike recommendation in §5 is advisory only.
- No automatic commit.
- No automatic next task.
- No auto-fix retry.
- Any BLOCKER/CONCERN from a future card goes to Ahmet.
- Movement from fake/non-mic input to real mic/audio/Piper/Edge TTS
  requires separate explicit Ahmet approval — this contract does not
  grant it, now or implicitly later.

---

## 9. BLACKBOX logging expectation for future implementation

A future fake/non-mic implementation card should log one BLACKBOX event
with:
- `event_name`: `LOOP0D_J0B_SAFETY_CONTRACT` or
  `LOOP0E_J0B_FAKE_INPUT_SPIKE`, depending on which future task it is.
- `status`: PASS / BLOCKER / CONCERN.
- `human_gate_required`: true.
- `runtime_recommendation_requires_separate_ahmet_approval`: true.
- `no_real_mic`: true.
- `no_piper_runtime`: true.
- `no_edge_tts_runtime`: true.
- `no_audio_playback`: true.
- `no_telegram`: true.
- `no_scheduler`: true.
- `no_secret_env_access`: true.
- `no_auto_fix_retry`: true.
- `no_commit`: true.
- `no_automatic_next_task`: true.

**This current docs-only safety contract task does NOT add a BLACKBOX
event.**

---

## 10. Exit criteria for this task

This task is complete when:
- `automation/LOOP0D_J0B_SAFETY_CONTRACT.md` exists.
- `automation/AUTONOMY_LOG.md` has one concise entry.
- No BLACKBOX event is added.
- No source/test/runtime files are touched.
- No J0B/Piper/mic/audio/Telegram/scheduler runtime is touched.
- No roadmap/doc source-of-truth files are modified except the new
  contract and `AUTONOMY_LOG.md`.
- `git diff --check` is clean except benign CRLF/LF warnings.
- `git status` shows only the two allowed files changed.

---

## EK — 2026-08-31: TTS kapısı taşındı (Eşik 1)

Bu sözleşme yazıldığında `PiperSubprocessAdapter.speak()` ve
`EdgeTTSAdapter.speak()` **koşulsuz** `NotImplementedError` fırlatıyordu.
Ahmet'in açık talimatıyla (denetim raporundaki Eşik 1) bu kapı **kaldırılmadı,
taşındı**:

| | Önce | Şimdi |
|---|---|---|
| Piper | Hiç çalışmaz | Yalnız **mutlak + var olan** exe ve `.onnx` yolu ile çalışır. PATH aranmaz, indirme yapılmaz, yol tahmin edilmez. Başarısızlık `TTSResult(ok=False)` döner, exception değil. |
| Edge TTS | Hiç çalışmaz | Yalnız `JARVIS_J0_EDGE_TTS_ENABLED=1` ile çalışır. **Bulut servisi — metin makineden çıkar** (CLAUDE.md §7). Varsayılan kapalı. |

Korunan özellikler:

- Modülü import etmek hâlâ subprocess doğurmaz, ağ kütüphanesi yüklemez, ses
  cihazına dokunmaz — `subprocess`, `edge_tts` ve `pygame` yalnız varsayılan
  çalıştırıcıların içinde, tembel import edilir. Import-güvenliği testleri
  bunu doğruluyor.
- `PiperCommandPlan` hâlâ kendi başına hiçbir yürütme yolu sunmuyor
  (`execute`/`run` yok).
- Faz A kuru-çalıştırma planlaması olduğu gibi duruyor.

**Doğrulama durumu:** Edge TTS yolu bu makinede **gerçekten çalıştırıldı** —
hoparlörden Türkçe ses alındı, sentez 1.1–1.5s. Piper yolu **gerçek ikiliyle
hiç çalıştırılmadı**: `piper.exe` ve `.onnx` ses modeli bu makinede yok, bu
yüzden yürütme yolu yalnız enjekte edilmiş çalıştırıcıyla test edildi. Piper
Faz B (gerçek ikiliyle manuel çalıştırma) **hâlâ yürütülmedi**.

*Prepared by: Claude Code | Date: 2026-07-10 | Sprint: LOOP-0D (safety
contract only) | Amended: 2026-08-31 (Eşik 1)*
