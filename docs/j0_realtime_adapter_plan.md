# J0 Realtime Adapter Plan

> Phase 4.0 output — plan before code.
> Date: 2026-07-04. Sprint: J0A.
> This plan governs the implementation in Phase 4.1–4.6.

---

## Module Layout

```
scripts/
  j0_voice_adapters.py   — STT side: STTAdapter protocol, RealtimeSTTAdapter, FakeSTTAdapter
  j0_tts_adapters.py     — TTS side: TTSAdapter protocol, TTSResult, FakeTTSAdapter,
                           PiperSubprocessAdapter (stub), EdgeTTSAdapter (stub)
  j0_voice_loop.py       — Wiring: wake→STT→route→j0_live_status→TTS; default-off CLI
  _utf8io.py             — (existing) configure_utf8_stdio + dump_json
  j0_live_status.py      — (existing) collect_status with injectable deps

requirements-voice.txt   — candidate deps, versions TODO_VERIFY_VERSION
docs/THIRD_PARTY_VOICE.md — name, version [UNVERIFIED], license [UNVERIFIED], integration, fallback

tests/
  test_j0_voice_adapters.py — adapter unit tests
  test_j0_voice_loop.py     — loop routing and CLI tests
```

---

## Interfaces

### STTAdapter (Protocol)

```
STTAdapter:
  start() -> None         # begin listening session (lazy-imports real libs inside)
  stop() -> None          # end listening session
  listen() -> str         # blocking: return next recognized text
  is_available() -> bool  # True if underlying lib is importable (no actual import needed)
```

### RealtimeSTTAdapter

- Constructor stores config dict ONLY. No imports at construction time.
- Lazy import: `from RealtimeSTT import AudioToTextRecorder` inside `start()` / `listen()`.
- Config keys: `model`, `language`, `silero_sensitivity`, `wake_words`, `wake_word_backend`.
- Default config: model="small", language="tr", silero_sensitivity=0.4, wake_words="hey jarvis", wake_word_backend="oww".
- `is_available()`: uses `importlib.util.find_spec("RealtimeSTT")` — does NOT import the library.
- **Windows multiprocessing docstring**: any process entrypoint using RealtimeSTTAdapter must be inside `if __name__ == "__main__"`.

### FakeSTTAdapter

- `__init__(texts: list[str])` — stores texts queue.
- `listen()` — pops and returns first text; raises IndexError on empty (deliberate: test must control input count).
- `is_available()` — always True.

### TTSAdapter (Protocol)

```
TTSAdapter:
  speak(text: str) -> TTSResult
```

### TTSResult (dataclass)

```
TTSResult:
  ok: bool
  engine: str
  first_audio_hint_ms: Optional[float]  # None if not measured; NEVER 0 for unmeasured
  warning: Optional[str]                # set when first_audio_hint_ms is None
```

### FakeTTSAdapter

- Records all spoken texts in `self.spoken: list[str]`.
- `speak()` appends text, returns `TTSResult(ok=True, engine="fake", first_audio_hint_ms=None, warning="not measured in fake adapter")`.
- `first_audio_hint_ms` is always None (not 0, not a fabricated number).

### PiperSubprocessAdapter (stub)

- `speak()` raises `NotImplementedError("J0B")`.
- `build_piper_cmd(config: dict) -> list[str]` — pure function, fully tested:
  - Builds Piper CLI argv from config keys: `executable`, `model`, optionally `output_file`.
  - No subprocess spawn, no imports beyond builtins.

### EdgeTTSAdapter (stub)

- Default-off, cloud-only fallback. Label: cloud-fallback.
- `speak()` raises `NotImplementedError("J0B-edge")`.
- No network in J0A.

---

## Voice Loop Wiring

### Route Table (inside j0_voice_loop.py)

```python
_ROUTE_PHRASES = [
    "nerede kaldık",
    "son commit neydi",
    "en son ne yaptık",
    "bugün ne yapacağız",
]
```

ASCII-fold function maps: İ→i, I→i, Ş→s, ş→s, Ğ→g, ğ→g, Ü→u, ü→u, Ö→o, ö→o, Ç→c, ç→c, ı→i.
Both the route phrase AND the recognized text are folded before comparison.

Match: `any(fold(phrase) in fold(text) for phrase in _ROUTE_PHRASES)` — substring, not exact.

Out-of-scope phrases ("faz üç e bir" etc.) intentionally absent — entity normalization is later.

### run_one_turn (injectable for testing)

```python
def run_one_turn(
    stt: STTAdapter,
    tts: TTSAdapter,
    status_provider=None,   # callable() -> object with .text_summary() -> str
) -> str:
    text = stt.listen()
    response = route_and_respond(text, status_provider=status_provider)
    tts.speak(response)
    return response
```

Tests inject FakeSTTAdapter + FakeTTSAdapter + fake status_provider.
Real microphone path is only inside `if __name__ == "__main__"`.

### Default-Off CLI

```
JARVIS_J0_REALTIME_ENABLED (default "0"):
  - env=0 AND no args:  print JSON {"status": "disabled", ...} via dump_json_to_stdout; exit 0
  - env=1 AND --real-mic:  real mic path (guarded by if __name__ == "__main__")
  - env=1 AND no --real-mic:  print JSON {"status": "disabled", "reason": "--real-mic required"}; exit 0
```

All CLI output via `_utf8io.configure_utf8_stdio()` + `dump_json_to_stdout()`.

---

## Flags and Environment Variables

| Variable | Default | Meaning |
|---|---|---|
| `JARVIS_J0_REALTIME_ENABLED` | "0" | Master switch. "1" + `--real-mic` flag = real microphone path. |

---

## Failure Modes and Fallbacks

| Failure | Behavior |
|---|---|
| RealtimeSTT not installed | `is_available()` returns False (no import error at module level). CLI stays default-off. |
| Unknown voice intent | route_and_respond returns a short "not understood" message in Turkish. |
| j0_live_status fails | Exception propagates; voice loop logs to stderr and returns error text. |
| PiperSubprocessAdapter used | `NotImplementedError("J0B")` — explicit, loud. |
| first_audio_hint_ms requested | Returns None + warning string. Never 0. |

---

## Test Plan

### test_j0_voice_adapters.py

1. **IMPORT SAFETY** — `j0_voice_adapters` and `j0_tts_adapters` importable with env unset; `sys.modules` does not contain "RealtimeSTT", "sounddevice", "pyaudio" after import.
2. **FakeSTTAdapter** — `listen()` returns injected texts in order.
3. **RealtimeSTTAdapter** — construction with default config stores config dict; no import side effect.
4. **RealtimeSTTAdapter.is_available()** — returns bool without importing RealtimeSTT.
5. **FakeTTSAdapter** — `speak()` records text; TTSResult.ok=True; first_audio_hint_ms=None; warning is non-None string.
6. **PiperSubprocessAdapter.speak()** — raises NotImplementedError with "J0B" in message.
7. **EdgeTTSAdapter.speak()** — raises NotImplementedError.
8. **build_piper_cmd pure function** — given config dict produces expected argv list; no subprocess.
9. **HONESTY** — FakeTTSAdapter result.first_audio_hint_ms is None (not 0, not a number).
10. **STATIC SAFETY** — modules contain no "telegram", "scheduler", "requests", "sendMessage" tokens (AST / rg scan).

### test_j0_voice_loop.py

1. **IMPORT SAFETY** — `j0_voice_loop` importable with env=0; no RealtimeSTT in sys.modules.
2. **DEFAULT-OFF CLI subprocess** — run j0_voice_loop.py as subprocess; env JARVIS_J0_REALTIME_ENABLED=0; capture stdout bytes; decode strict UTF-8; exit 0; output contains "disabled"; no mojibake markers.
3. **_ascii_fold** — handles İ (U+0130), Ş, Ğ, Ü, Ö, Ç, ı.
4. **_matches_status_intent** — "nerede kaldık" → True; "hava nasıl" → False; "son commit neydi" → True; "bugün ne yapacağız" → True.
5. **ROUTE BEHAVIOR** — FakeSTTAdapter("nerede kaldık") + fake status_provider returning LiveStatus with unique marker → FakeTTSAdapter.spoken[0] contains marker.
6. **LIVE WIRING** — different in_progress step in injected LiveStatus changes the response text (proves live-tool wiring, not canned text).
7. **TTS CONTRACT** — FakeTTSAdapter.spoken list grows by 1 per run_one_turn call.
8. **STATIC SAFETY** — j0_voice_loop contains no telegram/scheduler/requests/sendMessage.
9. **UTF-8 bytes** — subprocess stdout decoded with strict UTF-8; no UnicodeDecodeError.
10. **Mojibake guard** — stdout does not contain \xc3, \xc4, \xc5, \xef\xbf\xbd patterns.

---

## Commit Plan (per sprint Phase 6)

### Commit 1: feat(j0): add default-off realtime voice adapter skeleton

Files:
- scripts/j0_voice_adapters.py
- scripts/j0_tts_adapters.py
- scripts/j0_voice_loop.py
- requirements-voice.txt
- tests/test_j0_voice_adapters.py
- tests/test_j0_voice_loop.py

### Commit 2: docs(j0): sprint audit, harvest map, backlog, adapter plan, third-party notes

Files:
- docs/JARVIS_REPO_AUDIT.md
- docs/JARVIS_HARVEST_MAP.md
- docs/JARVIS_BACKLOG.md
- docs/j0_realtime_adapter_plan.md
- docs/THIRD_PARTY_VOICE.md
- automation/SESSION_SUMMARY.md
- automation/AUTONOMY_LOG.md
- automation/CODEX_REVIEW_REQUEST.md
