# JARVIS_BACKLOG.md — Sprint Backlog (J1 → J2/J5 → J4 → J6)

> Phase 3 output. Doc only. No implementation.
> Date: 2026-07-04. Sprint: J0A.
> J7 (OpenHands) is parked — not sequenced below.
> Active front after J0A: BLACKBOX-0 (offline validation, Ahmet confirms) → then J0B (real Piper subprocess, real edge-TTS fallback wiring).

---

## BLACKBOX-0 — Pre-J0B Checkpoint (mini-sprint)

**Entry gate:** J0A Codex PASS.

**Purpose:** Before enabling any real audio hardware, verify the adapter skeleton
works end-to-end in a controlled offline environment:
- Confirm import safety on the target machine (RealtimeSTT importable or missing_dependency clean)
- Confirm `py -3.11 scripts/j0_voice_loop.py` disabled-mode exits 0 with correct JSON
- Confirm all 240+ tests pass on target machine
- Confirm `git diff --check` clean
- Confirm no network calls in test run

**What is NOT in BLACKBOX-0:**
- No microphone open
- No model download
- No Piper subprocess
- No live TTS
- No scheduler/proactive activation

**Human gate:** Ahmet runs the validation commands and confirms clean. Only then proceed to J0B.

**Note:** Any real-mic command (e.g., `py -3.11 scripts/j0_voice_loop.py --real-mic`) is
future/manual, after BLACKBOX-0 confirmation AND after J0B Piper integration.
Do NOT run real-mic before BLACKBOX-0 decision.

---

## J0B — Real TTS + Piper Subprocess

**Entry gate:** BLACKBOX-0 complete (Ahmet confirmed). `j0_voice_adapters.py` and `j0_tts_adapters.py` from J0A merged and validated.

**Dependencies:**
- Piper binary + tr_TR voice model (download separately; not in repo)
- Piper license verified before any distribution/commercial use
- requirements-voice.txt pinned by Ahmet (Ahmet runs `pip install`, not Claude)

**First concrete task:**
1. Implement `PiperSubprocessAdapter.speak()` — spawn `piper` binary via `build_piper_cmd()`, pipe text to stdin, capture stdout raw audio.
2. Wire stdout to a Windows audio output (e.g., sounddevice) or save to .wav.
3. Measure first-audio onset (t0) per Spike-B lessons: warmup excluded, finite timestamps, ≥2 valid runs.
4. Update `TTSResult.first_audio_hint_ms` with real measured value — never `None` in J0B live path.
5. Add `EdgeTTSAdapter` as real fallback (JARVIS_J0_EDGE_TTS_ENABLED=0 default-off; no network in tests).

**What will NOT be built by hand:**
- Audio encoding / DSP — Piper handles this.
- Wake-word model training — openWakeWord pretrained model is adopted.
- STT model fine-tuning — faster-whisper pretrained "small" model used.

**Human gate to enable real-mic (FUTURE MANUAL ONLY — after BLACKBOX-0 + J0B):**

> **NOT part of J0A. Not authorized now. Runs only after BLACKBOX-0 is confirmed and J0B implementation is complete.**

After BLACKBOX-0 confirmation AND after J0B Piper integration, Ahmet manually:
1. Pins versions in requirements-voice.txt (reads `pip show <pkg>` after install)
2. Runs `pip install -r requirements-voice.txt`
3. Confirms model downloads
4. Runs `py -3.11 scripts/j0_voice_loop.py --real-mic` warmup and reports first-audio onset

---

## J1 — Memory Layer Upgrade

**Entry gate:** J0B complete + Codex PASS. Voice loop stable. No blocking J0 issues.

**Dependencies:**
- Chroma (keep existing) — verified working
- BGE-M3 embeddings — install + validate TR recall quality
- MemPalace-OSS (local, MIT) candidate — audit API before adoption; B-plan: Mem0-OSS
- Small invalidation rule: `updated_at` + `supersede` + nightly curation (build by hand, short)

**First concrete task:**
1. Write BGE-M3 embedding adapter behind existing memory_retrieval_policy interface.
2. Benchmark TR recall on JARVIS persona corpus (local, no LLM calls).
3. Wire MemPalace or Mem0-OSS behind existing MemoryPolicy seam; compare recall vs. Chroma.
4. Add `schema_version` field to all data files that lack it.

**What will NOT be built by hand:**
- Embedding model training — BGE-M3 pretrained model adopted.
- Vector DB from scratch — Chroma kept.
- Full LangChain / LlamaIndex orchestration — REJECTED.

---

## J2/J5 — Home Automation + Edge Satellites

**Entry gate:** J1 complete. HA dedicated box provisioned (NOT this Windows PC). Wyoming protocol confirmed working on that box.

**Dependencies:**
- Home Assistant on a separate Linux box (never Windows PC).
- Wyoming protocol: our Whisper/Piper/Ollama served via Wyoming.
- ESP32-S3 hardware + microWakeWord firmware.
- ESPHome: VOC/PM2.5/CO2 sensor config.

**First concrete task:**
1. Stand up Wyoming Whisper server on HA box. Test with real TR speech.
2. Wire HA Lovelace to our roadmap_state.json summary (read-only webhook).
3. Flash one ESP32-S3 satellite, confirm wake-word trigger → HA integration.

**What will NOT be built by hand:**
- Voice AI stack on Windows PC — moved to HA box.
- Wyoming protocol implementation — adopted (HA project).
- ESP32 RF/hardware design — microWakeWord firmware adopted.

---

## J4 — Observability + HUD

**Entry gate:** J2/J5 at least partially running. Metrics worth collecting.

**Dependencies:**
- Grafana OSS + Prometheus/Loki — install on monitoring box.
- FastAPI + React HUD — minimal custom layer only.

**First concrete task:**
1. Export proactive_runner DeliveryResult metrics to Prometheus (small exporter, no framework).
2. Wire Grafana dashboard: delivery sent/dry-run/cooldown counts.
3. FastAPI HUD: read roadmap_state.json + recent DeliveryResult log → simple JSON API.
4. React HUD: minimal read-only view of roadmap and recent alerts.

**What will NOT be built by hand:**
- Full BI dashboard — Grafana handles.
- Admin UI — Lovelace handles home view.
- Streamlit — REJECTED.

---

## J6 — LLM Transport, Cost, and PII

**Entry gate:** J4 partial. Cost visibility exists. Supply-chain incident memory (2026-03).

**Dependencies:**
- LiteLLM pinned versions (NOT unpinned — supply-chain lesson).
- Presidio + TR recognizers (our own TR PII recognizer rules).
- Redis / LangCache (GPTCache alternative) — evaluate after J4 metrics.

**First concrete task:**
1. Wire LiteLLM as transport bridge UNDER APIExecutor policy layer (Option-A: our policy runs first, LiteLLM is transport only).
2. Add Presidio redaction step before any external provider call, after DataClassifier.
3. Write TR-specific recognizer: TC kimlik, IBAN, GSM patterns.
4. Benchmark LangCache hit rate on JARVIS query corpus.

**What will NOT be built by hand:**
- LLM provider SDKs — LiteLLM handles the transport.
- Generic PII recognizers — Presidio adopted; only TR patterns are ours.
- RouteLLM — REJECTED (unmaintained).

---

## J7 — OpenHands (PARKED)

**Status:** STUDY only. No implementation date set.

**Parking reason:** Our Claude Code + Codex + human-gate loop is the accepted dev workflow. OpenHands sandbox pattern is interesting for future isolated code execution but is not blocking any current front. Aider is REJECTED (maintenance risk).

**Re-entry condition:** After J6 completes. If isolated code execution becomes a bottleneck.

---

## Sequencing Summary

```
J0A → Codex PASS → BLACKBOX-0 (offline validation, Ahmet confirms) → J0B (TTS + Piper real) → Codex PASS
  → J1 (memory BGE-M3 + MemPalace) → Codex PASS
    → J2/J5 (HA box + Wyoming + ESP32) → partial milestone
      → J4 (Grafana + HUD) → metrics baseline
        → J6 (LiteLLM + Presidio + TR PII)
          → J7 PARKED (OpenHands study if needed)
```

Each transition requires:
- Codex PASS on the finishing sprint
- Human gate (Ahmet sign-off) for any live deployment, hardware, or live API step
- No installation without Ahmet manually running the command
