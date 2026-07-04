# JARVIS_HARVEST_MAP.md — Harvest Decision Map

> Phase 2 output. Maps every harvest decision to a concrete repo integration point.
> Date: 2026-07-04. Sprint: J0A. Source: CLAUDE_CODE_SPRINT_PROMPT.md authoritative decisions.

---

## KEEP (ours — not replaced)

| Module | Why KEEP |
|---|---|
| `scripts/j0_live_status.py` | Live "nerede kaldık" tool. Core voice intent target. Read-only, injectable, battle-tested. |
| `scripts/_utf8io.py` | configure_utf8_stdio() — UTF-8 on Windows CLI. Required by every voice CLI entrypoint. |
| `agents/api_executor.py` | Core API execution + multi-provider logic. Our policy layer stays ours. |
| `agents/assistant_executor.py` | AssistantExecutor with resolve_provider() wiring. Our policy orchestration stays. |
| `agents/execution_policy.py` | Execution policy with human-override, cost gate. |
| `agents/provider_decision.py` | Deterministic provider routing. Confidence + route_reason. |
| `agents/local_first_router.py` | Cascade: cache → RAG → local LLM → budget gate → external. Unchanged. |
| `agents/proactive_policy.py` | JARVIS_PROACTIVE_ENABLED=0 policy engine. |
| `agents/proactive_runner.py` | One-shot runner; --live always blocked. |
| `scripts/escalation_policy.py` | Escalation policy governance. Read-only in J0A. |
| `scripts/mutation_gate.py` | Mutation gate governance. Read-only in J0A. |
| `roadmap_state.json` | Single source of truth. Untouched in J0A. |
| Persona assets (constitutions) | Not audited in J0A; assumed KEEP per sprint prompt. |

---

## DIAGNOSTIC / LEGACY (kept; not deleted; not the main path once adapter lands)

These files have served their purpose and taught valuable lessons that become **requirements** on any future measurement/adapter path.

| Module | Legacy Role | Lessons Encoded as Requirements |
|---|---|---|
| `scripts/j0_spike_b_latency_probe.py` | Spike-B latency probe (multi-run, normalized WER, labeled t0) | t0 must be defined at first audio onset; measurement must be valid (≥2 samples, warmup excluded, finite timestamps); WER normalized via ASCII-fold + punctuation strip; probe phrases are canonical TR; status_route_matched = "nerede" substring; mojibake guard before any metric claim |
| `scripts/j0_voice_latency_probe.py` | Spike-A skeleton (VoiceLatencyProbe dataclass) | TR_STT_PROBE_PHRASES = ["nerede kaldık", "son commit neydi", "en son ne yaptık", "bugün ne yapacağız"]; latency math: (first_audio_or_text_at - trigger_detected_at) × 1000; no fabricated latency numbers |

These modules are **not deleted**, not renamed, and not imported by the new adapter modules. They live as diagnostic history.

---

## REPLACED-BY-ADOPTION (concepts replaced; existing code superseded)

| Concept / Code | Replaced By | Integration Point |
|---|---|---|
| Fixed-window audio recording (hand-rolled, no VAD) | RealtimeSTT (MIT) + Silero VAD filter | `scripts/j0_voice_adapters.py::RealtimeSTTAdapter` wraps it. VAD means no fixed-window buffer; speech boundary detected automatically. |
| Hand-rolled audio capture loop | RealtimeSTT AudioToTextRecorder | Lazy-imported inside RealtimeSTTAdapter.start(). Not active in J0A. |
| No wake-word detection | openWakeWord "hey jarvis" | RealtimeSTTAdapter config: `wake_words="hey jarvis"`, `wake_word_backend="oww"`. Lazy-imported. |
| No TR STT | faster-whisper (via RealtimeSTT) + Silero VAD | RealtimeSTTAdapter config: `model="small"`, `language="tr"`, `silero_sensitivity=0.4`. |

---

## ADOPTION INTEGRATION POINTS (new modules created in J0A)

### `scripts/j0_voice_adapters.py`

| Adopted Library | Integration Method | Existing Code It Touches |
|---|---|---|
| RealtimeSTT (MIT) | Dep-behind-adapter (lazy import in start()/listen()) | None at module level. Calls j0_live_status indirectly via j0_voice_loop. |
| openWakeWord | Via RealtimeSTT config (`wake_word_backend="oww"`) | None. |
| faster-whisper / Silero VAD | Via RealtimeSTT config (`silero_sensitivity`) | None. |

### `scripts/j0_tts_adapters.py`

| Adopted Library | Integration Method | Status |
|---|---|---|
| Piper tr_TR | Subprocess (GPL-safe via process boundary) | **J0B stub only.** `PiperSubprocessAdapter.speak()` raises `NotImplementedError("J0B")`. |
| Edge TTS | Default-off cloud fallback adapter | **J0B stub only.** `EdgeTTSAdapter.speak()` raises `NotImplementedError("J0B-edge")`. |

### `scripts/j0_voice_loop.py`

| Integration | What it wires |
|---|---|
| STTAdapter → j0_live_status | Route table inside this file. "nerede kaldık" → collect_status() from j0_live_status. |
| TTSAdapter | Receives response text. FakeTTSAdapter in tests; real adapter in J0B+. |

---

## STUDY / DEFERRED (per harvest decisions)

| Library | Decision | Notes |
|---|---|---|
| Pipecat | STUDY only (J3/J5) | Too heavy for J0A. No integration code. |
| SpeechBrain ECAPA (speaker-ID) | Later, after J1 | No code. |
| BGE-M3 embeddings | J1 | No code. |
| MemPalace (local, MIT) | J1 candidate | No code. |
| Mem0-OSS | J1 B-plan | No code. |
| Home Assistant / Wyoming | J2/J5 — dedicated box | Never on this Windows PC. |
| Grafana / Prometheus / Loki | J4 | No code. |
| FastAPI+React HUD | J4 | No code. |
| LiteLLM | J6 bridge pattern | No code. |
| Presidio | J6 PII redaction | No code. |

---

## REJECT (per harvest decisions; no integration ever)

| Library | Rejection Reason |
|---|---|
| Letta runtime | Rejected. |
| LangChain / LlamaIndex / Haystack | Rejected. |
| RouteLLM | Unmaintained. |
| Aider | Maintenance risk. |
| Streamlit | Rejected (FastAPI+React preferred). |

---

## Disagreements with Harvest Decisions (evidence-based; no action taken)

**No disagreements found.** All harvest decisions are consistent with repo evidence:

- RealtimeSTT MIT license: consistent with ADAPT decision.
- Piper GPL + subprocess boundary: consistent with WRAP decision.
- openWakeWord integration via RealtimeSTT: consistent with ADOPT decision.
- SemanticRouter.RESEARCH_KW false positive for "nerede kaldık": addressed by the minimal route table in j0_voice_loop.py — not a disagreement with the harvest, just a routing clarification.
