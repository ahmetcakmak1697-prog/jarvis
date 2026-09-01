# JARVIS_REPO_AUDIT.md — SPRINT-J0A Repo Audit

> Phase 1 output. Read-only audit. No code changed.
> Date: 2026-07-04. Branch: auto/opencode-deepseek. Head: ae3708f8e.

---

## 1. DONE / IN-PROGRESS / PARKED

### DONE (evidence in roadmap_state.json)

| Step | Title | Evidence |
|---|---|---|
| FAZ-0 | Temel sistem (FastAPI + Ollama + RAG + memory) | PASS 2026-05 |
| DEVOPS-verifier | Deterministik verifier + auto-coder runner | commit 867b471b0, PASS 2026-06-17 |
| FAZ-1B.13H | Türkçe noktalı I (U+0130) folding düzeltmesi | commit a99148f0d, PASS 2026-06-17 |
| FAZ-1B.13-audit | FAZ 1B.13 durum tespiti | human review accepted 2026-06-18 |
| FAZ-1B.13I-api-executor-routing | Wire resolve_provider() into AssistantExecutor | commit dacf2aeaf, 126+15 passed |
| FAZ-2-D2 | Web research yeteneği (default-off) | done 2026-06-18, 41 tests |
| FAZ-PHASE2-integration | FAZ 2 entegrasyon kapısı | commit e39e7a6bb, 53 passed |
| FAZ-T1 | Türkçe kalite track'i | Ahmet sign-off 2026-06-24, PASS |
| FAZ-3-E1 (policy layer) | Proaktif davranış motoru (policy done) | see E1-S6x |
| E1-S6A | proactive_runner.py dry-run CLI | Codex PASS 2026-06-27 |
| E1-S6B | DeliveryResult struct | Codex PASS 2026-06-27 |
| E1-S6C | Windows Task Scheduler docs + script | Codex PASS 2026-06-28 |
| E1-S6D | Live-mode guard regression suite | Codex PASS 2026-06-28 |
| E1-S6E | Throttle/cooldown guard | Codex PASS 2026-06-28 |
| E1-S4 | Live Telegram smoke | Ahmet phone receipt 2026-06-27T22:51Z |
| J0-Spike-A | Voice latency harness skeleton | j0_voice_latency_probe.py |
| J0-Spike-B | Latency probe (multi-run, WER, labeled t0) | commit a14076e7a |

### IN-PROGRESS

| Step | Title | Status |
|---|---|---|
| FAZ-3-E1 | Proaktif davranış motoru (delivery layer) | policy done; runtime delivery/scheduler not yet live |

### PARKED / FUTURE

| Front | Notes |
|---|---|
| AUTO-0Q / AUTO-1 / autonomous_dev_planner | Parked. Do not touch. |
| orchestrator.py | Parked. scripts/orchestrator.py is legacy; agents/orchestrator.py is a lightweight facade. |
| J1 (memory layer) | BGE-M3, MemPalace, Chroma — future |
| J2/J5 (Home Assistant / Wyoming / ESP32) | Future; never on this Windows PC |
| J4 (Grafana / Prometheus / HUD) | Future |
| J6 (LiteLLM, Presidio, GPTCache) | Future |
| J7 (OpenHands study) | Parked |
| Speaker-ID (SpeechBrain ECAPA) | After J1 |
| Piper real subprocess | J0B |
| Edge TTS live | J0B (default-off fallback) |

---

## 2. File → Purpose Map (J0 and Governance)

### J0 Core

| File | Purpose |
|---|---|
| `scripts/j0_live_status.py` | "Nerede kaldık?" live tool. Reads git log + roadmap_state.json at runtime. Injectable (git_runner, roadmap_loader). |
| `scripts/j0_spike_b_latency_probe.py` | Spike-B multi-run latency probe; has `status_route_matched` string-contains check. Diagnostic/legacy once adapter lands. |
| `scripts/j0_voice_latency_probe.py` | Spike-A skeleton. Defines VoiceLatencyProbe dataclass and TR_STT_PROBE_PHRASES. Diagnostic/legacy. |
| `scripts/_utf8io.py` | configure_utf8_stdio() + dump_json(). Used by j0_live_status and j0_spike_b_latency_probe. |

### Governance / Policy

| File | Purpose |
|---|---|
| `roadmap_state.json` | Single source of truth for step status. Do not modify in J0A. |
| `agents/execution_policy.py` | Execution policy (human-override, cost gate). |
| `agents/proactive_policy.py` | Proactive delivery policy; JARVIS_PROACTIVE_ENABLED=0 default-off. |
| `agents/proactive_runner.py` | One-shot runner. --live always exit 1 (NOT IMPLEMENTED). |
| `scripts/mutation_gate.py` | Mutation gate (parked/governance). |
| `scripts/escalation_policy.py` | Escalation policy (parked/governance). |
| `scripts/orchestrator.py` | Legacy orchestrator (parked). |

### Provider / API Layer

| File | Purpose |
|---|---|
| `agents/api_executor.py` | Core API executor with multi-provider logic. |
| `agents/assistant_executor.py` | AssistantExecutor with resolve_provider() wiring (FAZ-1B.13I). |
| `agents/provider_decision.py` | resolve_provider() — deterministic routing. |
| `agents/local_first_router.py` | Local-first cascade: cache → RAG → local LLM → budget gate → external. |

### New files for J0A (to be created)

| File | Purpose |
|---|---|
| `scripts/j0_voice_adapters.py` | STTAdapter protocol, RealtimeSTTAdapter (default-off), FakeSTTAdapter. |
| `scripts/j0_tts_adapters.py` | TTSAdapter protocol, FakeTTSAdapter, PiperSubprocessAdapter (stub), EdgeTTSAdapter (stub). |
| `scripts/j0_voice_loop.py` | Wake→STT→route→j0_live_status→TTS wiring. Default-off CLI. |

---

## 3. Existing Intent/Status-Route Mechanism

### What exists today

**`agents/semantic_router.py`** — SemanticRouter class:
- Has `RESEARCH_KW` containing "nerede", which routes "nerede kaldık" → "research".
- This is WRONG for the voice loop use case. "nerede kaldık" should route to `j0_live_status`, not a web research path.
- Not used by any J0 voice path today.

**`scripts/j0_spike_b_latency_probe.py`** — probe-level check:
- `"status_route_matched": "nerede" in phrase` — string-contains, field in probe output JSON only.
- This is a measurement label, not a routing function.

**`scripts/j0_voice_latency_probe.py`** — TR_STT_PROBE_PHRASES:
- Defines `["nerede kaldık", "son commit neydi", "en son ne yaptık", "bugün ne yapacağız"]`
- No routing logic.

### Conclusion

There is **no existing functional route from voice input to j0_live_status**. The voice loop (`j0_voice_loop.py`) must add a minimal route table internally. The SemanticRouter's "nerede" → "research" mapping is a false positive for this use case; the voice loop must NOT use SemanticRouter for this intent.

The route table will use ASCII-fold matching (per CLAUDE.md Turkish rules: İ→i, Ş→s, Ğ→g, Ü→u, Ö→o, Ç→c, ı→i) on the four canonical phrases.

---

## 4. UTF-8 Helper Usage Map

### configure_utf8_stdio called

| File | Status |
|---|---|
| `scripts/j0_live_status.py` | YES — called in main() |
| `scripts/j0_spike_b_latency_probe.py` | YES — called in main() |

### configure_utf8_stdio NOT called (follow-up scope, outside J0A)

| File | Notes |
|---|---|
| `scripts/checkpoint_summary.py` | Turkish output; no configure_utf8_stdio. Outside J0 scope. |
| `scripts/escalation_policy.py` | Turkish output; no configure_utf8_stdio. Outside J0 scope. |
| `scripts/mutation_gate.py` | Turkish output; no configure_utf8_stdio. Outside J0 scope. |
| `scripts/daily_report.py` | Turkish output; no configure_utf8_stdio. Outside J0 scope. |

**Action in this sprint:** j0_voice_loop.py will call configure_utf8_stdio() in main(). The four files above are listed only; do not fix them in J0A.

---

## 5. Test Inventory

### J0 suites (run 2026-07-04)

```
py -3.11 -m pytest tests/test_j0_spike_b_latency_probe.py tests/test_j0_live_status_unicode.py tests/test_j0_live_status.py tests/test_j0_voice_latency_probe.py -q --tb=short
-> 101 passed in 22.39s
```

| Suite | Count |
|---|---|
| test_j0_spike_b_latency_probe.py | 62 |
| test_j0_live_status_unicode.py | 23 |
| test_j0_live_status.py | 11 |
| test_j0_voice_latency_probe.py | 5 |
| **Total** | **101** |

### Proactive / E1 suites (run 2026-07-04)

```
py -3.11 -m pytest tests/test_e1_s4_live_smoke_wiring.py tests/test_proactive_delivery.py tests/test_proactive_runtime.py -q --tb=short
-> 69 passed in 0.23s
```

| Suite | Count |
|---|---|
| test_e1_s4_live_smoke_wiring.py | 33 |
| test_proactive_delivery.py | 27 |
| test_proactive_runtime.py | 9 |
| **Total** | **69** |

### New suites from J0A (to be created)

| Suite | Planned count |
|---|---|
| tests/test_j0_voice_adapters.py | ~15 |
| tests/test_j0_voice_loop.py | ~15 |

---

## 6. Risks and Ambiguities

1. **SemanticRouter false positive**: "nerede kaldık" → "research" in SemanticRouter. Confirmed the voice loop must NOT use SemanticRouter. Minimal route table inside j0_voice_loop.py resolves this.

2. **No existing voice route wiring**: The route table is entirely new. Sprint prompt section 4.4 authorizes adding it inside j0_voice_loop.py.

3. **RealtimeSTT Windows multiprocessing**: On Windows, RealtimeSTT spawns child processes. Any real entrypoint must be inside `if __name__ == "__main__"`. Docstring-only warning; tests must NEVER trigger the real path.

4. **Piper license**: Piper is GPL. Subprocess boundary is the accepted approach. License must be verified before distribution. No subprocess code in J0A.

5. **UTF-8 coverage gap**: checkpoint_summary.py, escalation_policy.py, mutation_gate.py, daily_report.py lack configure_utf8_stdio(). Listed, not fixed in J0A.

6. **`--live` invariant**: proactive_runner.py --live always exits 1 (E1-S6D). j0_voice_loop.py adds its own guard: real mic path requires both env=1 and --real-mic flag.

7. **No version pins possible without install**: requirements-voice.txt uses TODO_VERIFY_VERSION per sprint rules. No guessing.
