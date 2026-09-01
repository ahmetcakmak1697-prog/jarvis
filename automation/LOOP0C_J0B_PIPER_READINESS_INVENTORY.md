# LOOP-0C J0B/Piper Readiness Inventory

> Date: 2026-07-09
> Branch: auto/opencode-deepseek
> Status: READ-ONLY REPO INSPECTION + REPORT ONLY — NOT IMPLEMENTED

---

## 1. Status

- This is the LOOP-0C actual readiness-inventory implementation, as defined
  in `automation/LOOP0C_FIRST_REAL_CARGO_PLAN.md`.
- It is read-only repo inspection plus docs/checklist output.
- It does not implement J0B/Piper runtime.
- It does not run microphone/audio/Piper/Edge TTS.
- It does not approve auto-fix retry, commit automation, or autonomous
  next-task continuation.
- It must stop at Ahmet human gate.

---

## 2. References

- `automation/LOOP0C_FIRST_REAL_CARGO_PLAN.md` — commit `e329b9861` (read-only
  reference; not modified by this report).
- `automation/LOOP0_MACHINE_GATE_SPEC.md` — commit `aab936c8c` (read-only
  reference; not modified by this report).
- `docs/JARVIS_REPO_AUDIT.md` — **exists**. Found and read.

### docs/JARVIS_REPO_AUDIT.md detail

- Header states: "Phase 1 output. Read-only audit. No code changed. Date:
  2026-07-04. Branch: auto/opencode-deepseek. Head: `ae3708f8e`."
- This is the prior SPRINT-J0A audit.
- It already contains:
  - a DONE/IN-PROGRESS/PARKED table including `J0-Spike-A` and `J0-Spike-B`,
  - a file→purpose map for J0 core files and the (at-the-time not-yet-created)
    J0A adapter files,
  - a description of the "nerede kaldık" routing gap and why SemanticRouter
    must not be used for it,
  - a UTF-8 helper usage map,
  - a test inventory (101 J0 tests + 69 proactive/E1 tests as of 2026-07-04),
  - six named risks (SemanticRouter false positive, Windows RealtimeSTT
    multiprocessing, Piper GPL licensing boundary, UTF-8 coverage gaps, the
    `--live` invariant, missing version pins).
- **How this report extends/validates it:**
  - Re-inspected `scripts/j0_tts_adapters.py`, `scripts/j0_voice_adapters.py`,
    `scripts/j0_voice_loop.py` at current HEAD (`e329b9861`). Their git
    history's last touching commits are `591ded854`, `76206e92e`,
    `6ccb1d943` — all predate the audit's `J0A` closure. Content still
    matches the audit's description: `PiperSubprocessAdapter.speak()` and
    `EdgeTTSAdapter.speak()` still raise `NotImplementedError` with
    `"J0B"`/`"J0B-edge"` messages. **Validated: no drift since the prior
    audit on this point.**
  - Re-checked test counts: `tests/test_j0_voice_adapters.py` and
    `tests/test_j0_voice_loop.py` each currently contain **29** top-level
    `def test_` functions (grep count), higher than the audit's "planned
    ~15" placeholder figure for each suite. **Extends** the audit: actual
    coverage is larger than the audit's forward-looking estimate (the audit
    labeled these as "to be created" suites with planned counts, not final
    counts).
  - Checked `roadmap_state.json` directly: its `steps` list currently has
    **14** entries, and **none** are keyed `J0-Spike-A` / `J0-Spike-B` or
    any `j0`-prefixed key. The audit's DONE table cites file/commit evidence
    for these two rows (`j0_voice_latency_probe.py`; commit `a14076e7a`), not
    a `roadmap_state.json` step key — so this is not a contradiction of the
    audit's per-row evidence, but it does mean the audit's table *heading*
    ("evidence in roadmap_state.json") is broader than what the J0 rows
    themselves show. **Flag for documentation-precision follow-up, not a
    blocker.**
  - Confirmed `requirements-voice.txt` still pins all three voice
    dependencies (`RealtimeSTT`, `faster-whisper`, `openwakeword`) to
    `TODO_VERIFY_VERSION` and still instructs "Do not install these without
    verifying versions." **Validated: unchanged, no install has occurred.**
  - This inspection additionally found and reviewed
    `docs/JARVIS_BACKLOG.md`, `docs/JARVIS_HARVEST_MAP.md`,
    `docs/JARVIS_v5_MASTER_ROADMAP.md`, and
    `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md`, none of which are cited
    by name in `docs/JARVIS_REPO_AUDIT.md` itself but which contain material
    directly relevant to J0B/Piper readiness and to the strategic
    adopt-vs-build question (see §5A).

---

## 3. Existing J0/J0B/Piper inventory

Grouped by category. All items were **read only**, never executed (except
where the machine gate in §6 of this report explicitly runs
`tests/test_blackbox_log.py`, which is unrelated to J0/Piper).

### Docs

| Path | Observed purpose | J0B/Piper relevance | Executed? |
|---|---|---|---|
| `docs/JARVIS_REPO_AUDIT.md` | SPRINT-J0A read-only repo audit (2026-07-04) | Direct — primary prior audit | Read only |
| `docs/THIRD_PARTY_VOICE.md` | Third-party voice library register: RealtimeSTT, faster-whisper, openWakeWord, Piper, Edge TTS — versions/licenses marked `[UNVERIFIED]` | Direct — licensing/dependency ledger for J0B | Read only |
| `docs/j0_realtime_adapter_plan.md` | Phase 4.0 plan for `j0_voice_adapters.py`/`j0_tts_adapters.py`/`j0_voice_loop.py`, incl. `PiperSubprocessAdapter` stub design and `build_piper_cmd()` spec | Direct — design contract J0B must follow | Read only |
| `docs/j0_voice_loop_spike.md` | Voice loop spike notes | Direct | Read only |
| `docs/JARVIS_BACKLOG.md` | Active backlog; names J0B explicitly as "real Piper subprocess, real edge-TTS fallback wiring," lists J0B entry/exit criteria, and lists J1/J2/J5 (memory, Home Assistant/Wyoming/ESP32) as later fronts | Direct — current backlog framing for J0B | Read only |
| `docs/JARVIS_HARVEST_MAP.md` | Harvest decision map: KEEP / REPLACED-BY-ADOPTION / ADOPTION INTEGRATION POINTS / STUDY-DEFERRED / REJECT tables for J0A libraries | Direct — records Piper as "WRAP" (subprocess boundary), Home Assistant/Wyoming as "J2/J5, never on this Windows PC," Letta as "Rejected" | Read only |
| `docs/JARVIS_v5_MASTER_ROADMAP.md` | Longer-range roadmap; references Mem0 and Letta/MemGPT as memory-architecture references | Indirect — J1/memory, not J0B directly | Read only |
| `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md` | Strategy doc with a "Borrow/Adopt" table covering Wyoming, faster-whisper, Piper, openWakeWord, Home Assistant, ESPHome, Letta, Graphiti, Mem0, LiteLLM and others | Direct — this is the repo's own existing OSS-adoption analysis, predating this task's prompt | Read only |

### Tests

| Path | Observed purpose | J0B/Piper relevance | Executed? |
|---|---|---|---|
| `tests/test_j0_voice_adapters.py` | 29 test functions covering STT adapter protocol / `FakeSTTAdapter` / `RealtimeSTTAdapter` construction | Direct | Not executed in this task (only read/counted via grep) |
| `tests/test_j0_voice_loop.py` | 29 test functions covering wake→STT→route→status→TTS wiring with fakes | Direct | Not executed |
| `tests/test_j0_live_status.py` | 11 tests for `j0_live_status.py` | Direct (status route target) | Not executed |
| `tests/test_j0_live_status_unicode.py` | 23 tests, Turkish/Unicode handling for live status | Direct (UTF-8 discipline) | Not executed |
| `tests/test_j0_spike_b_latency_probe.py` | 62 tests for the Spike-B latency probe | Direct (latency baseline) | Not executed |
| `tests/test_j0_voice_latency_probe.py` | 5 tests for Spike-A skeleton | Direct | Not executed |
| `tests/test_blackbox_log.py` | 64 test functions for `agents/blackbox_log.py` | Indirect — used only for this task's own machine gate, not J0/Piper | **Executed** (machine gate, §6 of this report) |

### Source / adapters

| Path | Observed purpose | J0B/Piper relevance | Executed? |
|---|---|---|---|
| `scripts/j0_voice_adapters.py` (140 lines) | `STTAdapter` protocol, `FakeSTTAdapter`, `RealtimeSTTAdapter` (default-off, lazy-imported) | Direct | Read only |
| `scripts/j0_tts_adapters.py` (146 lines) | `TTSAdapter` protocol, `FakeTTSAdapter`, `PiperSubprocessAdapter` (stub, raises `NotImplementedError("J0B: ...")`), `EdgeTTSAdapter` (stub, raises `NotImplementedError("J0B-edge: ...")`), `build_piper_cmd()` pure function | **Direct — this is the exact stub surface J0B must fill in** | Read only |
| `scripts/j0_voice_loop.py` (221 lines) | Wires wake→STT→route→`j0_live_status`→TTS; default-off CLI | Direct | Read only |
| `scripts/j0_live_status.py` | "Nerede kaldık?" live status tool; the voice loop's routing target | Direct | Read only |
| `scripts/j0_spike_b_latency_probe.py` | Spike-B multi-run latency probe | Direct (diagnostic/legacy) | Read only |
| `scripts/j0_voice_latency_probe.py` | Spike-A skeleton, `TR_STT_PROBE_PHRASES` | Direct (diagnostic/legacy) | Read only |
| `scripts/_utf8io.py` | `configure_utf8_stdio()` + `dump_json()` | Direct (UTF-8 discipline, used by voice loop) | Read only |
| `voice/voice_engine.py`, `voice/voice_interface.py`, `voice/__init__.py` | Older/separate voice module, not under the `j0_*` naming | Indirect — not referenced in the prior audit; identified in this inspection as a naming/location question to resolve before J0B (are these superseded by `scripts/j0_voice_*` or still live?) | Read only |
| `tools/voice_io.py`, `voice_test.py` | Additional voice-adjacent utility/test script outside `scripts/j0_*` and `tests/` naming | Indirect — same open question as above | Read only |
| `agents/ollama_executor.py` | Ollama provider executor for the local-first LLM cascade | Indirect — Ollama is already in use as a **local LLM provider**, separate from the voice-pipeline "Ollama via Wyoming" idea raised in the strategic input (§5A) | Read only |

### Scripts / probes

Covered above under source/adapters (`scripts/j0_*` files are simultaneously
the probes and the adapters at this stage of the project).

### Config/env examples

| Path | Observed purpose | Relevance | Executed? |
|---|---|---|---|
| `requirements-voice.txt` | Candidate pip deps for the voice pipeline (`RealtimeSTT`, `faster-whisper`, `openwakeword`, `sounddevice`), all pinned to `TODO_VERIFY_VERSION`; explicit "Do not install" note; Piper is called out as binary-only, not pip | Direct | Read only, not installed |
| `.env.example` | Generic env template | Not J0/Piper-specific; not opened for secret content, only listed by filename via `git ls-files` | Not opened |

No logs/reports specific to J0/Piper were found beyond the docs already
listed above.

---

## 4. Previously proven capabilities

Based only on repo files and the prior audit:

- **Local voice command spike**: Spike-A (`scripts/j0_voice_latency_probe.py`)
  and Spike-B (`scripts/j0_spike_b_latency_probe.py`) exist with dedicated
  test suites (5 and 62 tests respectively). Per the prior audit these are
  "diagnostic/legacy once adapter lands" — i.e. proven as spikes, not as the
  final adapter path.
- **STT path**: `RealtimeSTTAdapter` exists as a default-off, lazy-imported
  adapter (`scripts/j0_voice_adapters.py`) with test coverage
  (`tests/test_j0_voice_adapters.py`, 29 tests). Real microphone execution
  itself is **not confirmed by inspected files** — the design is present,
  live capture is explicitly out of scope for J0A/this task.
- **Ambient/noise gate**: Silero VAD is wired only *by configuration*
  (`silero_sensitivity`) inside `RealtimeSTTAdapter`, per
  `docs/JARVIS_HARVEST_MAP.md`. No standalone ambient/noise-gate module was
  found. **Not confirmed as a proven standalone capability** — it rides
  inside the RealtimeSTT dependency, which itself has not been installed
  (`requirements-voice.txt` is all `TODO_VERIFY_VERSION`).
- **Latency probe**: proven — Spike-B is described as a "multi-run latency
  probe" with a dedicated 62-test suite.
- **Unicode/Turkish output handling**: proven for the J0 core path —
  `configure_utf8_stdio()` is called in `scripts/j0_live_status.py` and
  `scripts/j0_spike_b_latency_probe.py` (per prior audit, re-confirmed by
  this inspection's file listing), with a 23-test dedicated Unicode suite
  (`tests/test_j0_live_status_unicode.py`). The prior audit's own list of
  files that do **not** call `configure_utf8_stdio()`
  (`scripts/checkpoint_summary.py`, `scripts/escalation_policy.py`,
  `scripts/mutation_gate.py`, `scripts/daily_report.py`) was not
  re-verified line-by-line in this task — carried forward as-is from the
  prior audit, out of scope to re-check here since none of those files are
  J0B/Piper-specific.
- **Live status route**: `scripts/j0_live_status.py` proven and tested (11
  tests); the prior audit's conclusion that no functional voice→status route
  exists yet (SemanticRouter would mis-route "nerede kaldık" to "research")
  was re-read and nothing in this inspection contradicts it. **Not
  reverified by execution** — reading `scripts/j0_voice_loop.py` shows a
  route table is present in that file per the prior design doc, but this
  task did not execute it to confirm runtime behavior (execution is out of
  scope).
- **Adapter/test coverage**: proven — `j0_voice_adapters.py` and
  `j0_voice_loop.py` each have larger test suites now (29 tests each) than
  the prior audit's placeholder plan (~15 each).
- **Safety boundaries around mic/audio/runtime**: proven at the code level —
  `PiperSubprocessAdapter.speak()` and `EdgeTTSAdapter.speak()` both raise
  `NotImplementedError` unconditionally; `RealtimeSTTAdapter` lazy-imports
  its dependency so it cannot activate real hardware just by being imported.
  This inspection did not execute any of these adapters, consistent with
  the read-only requirement.

---

## 5. Gaps before safe J0B/Piper runtime work

**Documentation gaps**
- The two voice-related files outside the `j0_*`/`tests/` naming convention
  (`voice/voice_engine.py`, `voice/voice_interface.py`, `tools/voice_io.py`,
  `voice_test.py`) are not mentioned in `docs/JARVIS_REPO_AUDIT.md`,
  `docs/JARVIS_HARVEST_MAP.md`, or `docs/JARVIS_BACKLOG.md`. Before J0B
  work, it should be documented whether these are superseded/dead code or a
  separate active surface.
- `docs/JARVIS_REPO_AUDIT.md`'s DONE-table evidence column ("evidence in
  roadmap_state.json") is broader than what the J0-Spike-A/B rows actually
  cite (file/commit, not a roadmap step key) — worth a precision fix
  next time that doc is touched.

**Test gaps**
- No test suite currently exercises `build_piper_cmd()` against a real
  installed Piper binary (would require install, explicitly out of scope
  today). This is expected at this stage, not a defect.
- No test currently asserts machine-readable behavior for
  `RealtimeSTTAdapter` beyond construction/config (per prior audit risk #3,
  real mic path must stay inside `if __name__ == "__main__"`); not
  reverified line-by-line in this task.

**Safety/guardrail gaps**
- No explicit guard was found (in this read-only pass) preventing
  `PiperSubprocessAdapter`/`EdgeTTSAdapter` from being wired into
  `j0_voice_loop.py`'s default path once their `NotImplementedError` stubs
  are removed in J0B — i.e. the *future* implementation will need its own
  explicit env-flag/`--real-mic`-style guard analogous to the one already
  described for the mic path (prior audit risk #6). This is a gap to close
  **in** J0B design, not before it, but it should be named now.

**Runtime integration gaps**
- Piper binary and `tr_TR` voice model are not present in the repo (by
  design — `requirements-voice.txt` and `docs/THIRD_PARTY_VOICE.md` both
  say these are downloaded separately, not installed here).
- Edge TTS wiring is entirely unimplemented (stub only).

**Dependency/environment gaps**
- `RealtimeSTT`, `faster-whisper`, `openwakeword`, `sounddevice` are all
  pinned to `TODO_VERIFY_VERSION` in `requirements-voice.txt` and have not
  been installed. Installing them is explicitly **not** an approved action
  in this task.

**User-approval gates**
- Per `docs/JARVIS_BACKLOG.md`, Piper license must be verified before any
  distribution/commercial use — this is an Ahmet-level decision, not
  something this inspection can close.
- Any move from this readiness inventory to actual J0B/Piper runtime work
  requires separate explicit Ahmet approval (per
  `automation/LOOP0C_FIRST_REAL_CARGO_PLAN.md` §7 and
  `automation/LOOP0_MACHINE_GATE_SPEC.md` §9).

This report does **not** suggest running mic/audio/Piper, installing
packages, or running Telegram/scheduler as approved next actions, and does
**not** propose auto-fix retry.

---

## 5A. Strategic adopt-vs-build decision risks

Based only on inspected repo files (no web research performed):

- **Home Assistant / HA Assist / Wyoming / Whisper / Piper / Ollama**:
  **Found, and already substantially documented in the repo**, predating
  this task's external-research prompt:
  - `docs/JARVIS_BACKLOG.md` (§ "J2/J5") already states the entry gate is
    "J1 complete. HA dedicated box provisioned (NOT this Windows PC).
    Wyoming protocol confirmed working on that box," and explicitly frames
    "our Whisper/Piper/Ollama served via Wyoming" as the target
    architecture for that later front.
  - `docs/JARVIS_HARVEST_MAP.md` lists "Home Assistant / Wyoming" under
    STUDY/DEFERRED as "J2/J5 — dedicated box... Never on this Windows PC."
  - `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md` has an explicit
    "Borrow/Adopt" table marking "Wyoming + faster-whisper + Piper +
    openWakeWord" and "Home Assistant + ESPHome + Node-RED" as **Adopt**
    candidates, and separately marks a V0/V1/M1 milestone path
    ("Wake word: openWakeWord (Wyoming)", "M1 Device/scene köprüsü... Home
    Assistant + Wyoming Assist").
  - Ollama itself is **already adopted** in this repo, but as the
    **local-first LLM provider** (`agents/ollama_executor.py`), not (yet)
    as a Wyoming-served voice backend. The strategic input's "Ollama via
    Wyoming" framing is a different integration point than the existing
    Ollama usage.
  - Net: the repo's own strategy docs already lean toward eventually
    routing voice/home-control through Home Assistant + Wyoming rather than
    a fully custom stack, but treat it as a **later, separate-hardware**
    front (J2/J5), not as a replacement for the current J0/J0B scope, which
    is explicitly scoped to this Windows PC only.
- **Letta / Mem0 / Graphiti memory-layer evidence**: **Found, with an
  internal inconsistency worth flagging.**
  - `docs/JARVIS_BACKLOG.md` names "MemPalace-OSS... audit API before
    adoption; B-plan: Mem0-OSS" for the J1 memory front.
  - `docs/JARVIS_HARVEST_MAP.md` lists "Mem0-OSS | J1 B-plan | No code" under
    STUDY/DEFERRED, but separately lists **"Letta runtime | Rejected."**
    under REJECT.
  - `docs/JARVIS_v5_MASTER_ROADMAP.md` references "Mem0" and "Letta /
    MemGPT" as architecture references (not necessarily adoption commitments).
  - `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md` marks "Letta (MemGPT)"
    and "Graphiti / Mem0" as **"verified, adopt candidate"** — this directly
    conflicts with `JARVIS_HARVEST_MAP.md`'s "Letta runtime | Rejected."
  - **This is a real, pre-existing documentation conflict** between two
    repo docs about whether Letta is rejected or an adopt-candidate. This
    report does not resolve it; it is surfaced here as something Ahmet
    should reconcile before J1 memory-layer decisions are finalized, not
    something invented by the strategic-input prompt.
- **Frigate / Double Take room-vision evidence**: **Not confirmed by
  inspected repo files.** No filename or content match for "Frigate" or
  "Double Take" was found anywhere in the tracked repo.
- **Existing adopt-over-build policy evidence**: **Found — this is already
  an explicit, named policy in the repo**, not a new idea:
  - `automation/LOOP0_MACHINE_GATE_SPEC.md` §3 is titled "Adopt-over-build
    check."
  - `automation/LOOP0A_CAPABILITY_REPORT.md` §4 is titled "Adopt-Over-Build:
    Local Control-Plane Findings."
  - `automation/LOOP0C_FIRST_REAL_CARGO_PLAN.md` explicitly invokes
    "Adopt-over-build applies to prior Jarvis docs the same way it applied
    to prior external tooling in LOOP-0A."
  - `docs/strategy/JARVIS_v5_REALITY_OS_ROADMAP.md` independently uses
    "Adopt" as a recurring decision label across many rows (LiteLLM,
    Wyoming/Piper stack, SearXNG/Crawl4AI, Docling/MinerU, LLM Guard,
    Langfuse/Phoenix, etc.).

**Required open decision (stated, not resolved here):**
Before implementing custom J0B/Piper runtime, decide whether JARVIS
voice/home-control should be routed through Home Assistant
Assist/Wyoming/Piper instead of custom Piper subprocess integration.

- This inspection does not make that decision.
- This inspection does not rewrite the roadmap.
- This inspection performed no web research.
- The repo's own strategy docs already lean toward an eventual HA+Wyoming
  path for the *later* J2/J5 front, but currently scope J0/J0B narrowly to
  this Windows PC with a direct Piper subprocess — those two framings have
  not yet been explicitly reconciled by Ahmet as a single decision.

---

## 6. Readiness checklist

| Item | Status |
|---|---|
| J0A audit (`docs/JARVIS_REPO_AUDIT.md`) exists and was read | READY |
| J0/J0B files identified | READY |
| Piper-related files identified | READY |
| STT/voice spike evidence identified | READY |
| Tests relevant to voice/J0 found | READY |
| OSS adopt-vs-build evidence inspected | READY |
| Home Assistant / HA Assist evidence inspected | READY |
| Memory-layer OSS evidence inspected | PARTIAL — found, but with an unresolved Letta reject-vs-adopt conflict between two repo docs (§5A) |
| Runtime execution avoided | READY |
| Secrets/env avoided | READY — `.env.example` filename only listed, not opened; no `.env` file opened |
| Source/test files unchanged | READY |
| Future J0B runtime gate still requires Ahmet approval | READY |

No item is BLOCKED or NOT INSPECTED.

---

## 7. Recommended next implementation card

**"LOOP-0D/J0B safety contract before runtime"**

Reasoning: this inspection found that the *code-level* stub safety
(`NotImplementedError` in `PiperSubprocessAdapter`/`EdgeTTSAdapter`) is
solid, but it did not find an explicit, written safety contract for what
guards must exist once those stubs are removed — e.g. an explicit
env-flag/CLI-flag gate analogous to `proactive_runner.py --live` or the
mic path's `env=1` + `--real-mic` combination, applied specifically to
Piper subprocess spawning and Edge TTS network calls. It also surfaced an
unresolved strategic question (§5A: HA/Wyoming vs. custom Piper) and an
unresolved documentation conflict (Letta rejected vs. adopt-candidate)
that a safety-contract card would be the natural place to require Ahmet to
resolve before any runtime code is written.

This is not another docs-only planning layer for its own sake — the
inspection shows a concrete missing artifact (a written J0B safety/guard
contract covering subprocess spawning, network calls, and the
HA/Wyoming-vs-custom decision) that does not yet exist anywhere in the
repo.

Not recommended: "J0B/Piper narrow runtime spike with fake/non-mic input
only" — because the safety contract for what such a spike may and may not
do has not yet been written down, and the strategic HA/Wyoming-vs-custom
question is still open.

**This is only a recommendation for Ahmet review. It is not approval to
start that card. It is not approval to run Piper, microphone, or audio. It
is not approval to implement J0B/Piper runtime.**

---

## 8. Human gate

- This report must be reviewed by Ahmet.
- Even if machine gate and Codex PASS, no commit until Ahmet approves.
- Any BLOCKER/CONCERN goes to Ahmet.
- Movement from readiness inventory to actual J0B/Piper runtime requires
  separate explicit Ahmet approval.

---

*Prepared by: Claude Code | Date: 2026-07-09 | Sprint: LOOP-0C (readiness
inventory implementation)*
