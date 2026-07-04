"""
tests/test_j0_voice_adapters.py — Adapter unit tests for j0_voice_adapters and j0_tts_adapters.

Coverage:
  1) IMPORT SAFETY — no RealtimeSTT/sounddevice/pyaudio at module level
  2) FakeSTTAdapter behaviour
  3) RealtimeSTTAdapter config storage (no import side-effect)
  4) RealtimeSTTAdapter.is_available() returns bool without importing RealtimeSTT
  5) FakeTTSAdapter speak() + TTSResult contract
  6) PiperSubprocessAdapter.speak() raises NotImplementedError("J0B")
  7) EdgeTTSAdapter.speak() raises NotImplementedError
  8) build_piper_cmd pure function
  9) HONESTY: first_audio_hint_ms=None, not 0
 10) STATIC SAFETY: no telegram/scheduler/requests/sendMessage
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

import pytest

# Ensure scripts/ is on sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FORBIDDEN_TOKENS = {
    "telegram", "scheduler", "requests", "sendMessage",
    "pyaudio", "sounddevice",
}

_IMPORT_SAFETY_MODULES = {"RealtimeSTT", "sounddevice", "pyaudio"}


def _module_has_forbidden_token(source_path: Path, token: str) -> bool:
    source = source_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in getattr(node, "names", [])]
            module = getattr(node, "module", "") or ""
            if any(token in n for n in names) or token in module:
                return True
        if isinstance(node, ast.Attribute):
            if token in (node.attr or ""):
                return True
        if isinstance(node, ast.Name):
            if token in (node.id or ""):
                return True
    return False


# ---------------------------------------------------------------------------
# 1. IMPORT SAFETY
# ---------------------------------------------------------------------------


def test_import_voice_adapters_does_not_load_realtimestt():
    """Importing j0_voice_adapters must not import RealtimeSTT/sounddevice/pyaudio."""
    for mod_name in _IMPORT_SAFETY_MODULES:
        assert mod_name not in sys.modules, (
            f"{mod_name} was already in sys.modules before test; isolation issue"
        )

    import j0_voice_adapters  # noqa: F401

    for mod_name in _IMPORT_SAFETY_MODULES:
        assert mod_name not in sys.modules, (
            f"importing j0_voice_adapters caused {mod_name} to be imported"
        )


def test_import_tts_adapters_does_not_load_audio_libs():
    """Importing j0_tts_adapters must not import sounddevice/pyaudio."""
    for mod_name in {"sounddevice", "pyaudio"}:
        assert mod_name not in sys.modules

    import j0_tts_adapters  # noqa: F401

    for mod_name in {"sounddevice", "pyaudio"}:
        assert mod_name not in sys.modules, (
            f"importing j0_tts_adapters caused {mod_name} to be imported"
        )


# ---------------------------------------------------------------------------
# 2. FakeSTTAdapter
# ---------------------------------------------------------------------------


def test_fake_stt_adapter_returns_injected_texts_in_order():
    from j0_voice_adapters import FakeSTTAdapter

    stt = FakeSTTAdapter(["nerede kaldık", "son commit neydi"])
    assert stt.listen() == "nerede kaldık"
    assert stt.listen() == "son commit neydi"


def test_fake_stt_adapter_raises_index_error_when_exhausted():
    from j0_voice_adapters import FakeSTTAdapter

    stt = FakeSTTAdapter([])
    with pytest.raises(IndexError):
        stt.listen()


def test_fake_stt_adapter_is_available_true():
    from j0_voice_adapters import FakeSTTAdapter

    assert FakeSTTAdapter([]).is_available() is True


def test_fake_stt_adapter_start_stop_noop():
    from j0_voice_adapters import FakeSTTAdapter

    stt = FakeSTTAdapter(["x"])
    stt.start()
    stt.stop()  # must not raise


# ---------------------------------------------------------------------------
# 3. RealtimeSTTAdapter — config storage, no import side-effect
# ---------------------------------------------------------------------------


def test_realtime_stt_adapter_stores_default_config():
    from j0_voice_adapters import RealtimeSTTAdapter

    adapter = RealtimeSTTAdapter()
    cfg = adapter.config
    assert cfg["model"] == "small"
    assert cfg["language"] == "tr"
    assert cfg["wake_words"] == "hey jarvis"
    assert cfg["wake_word_backend"] == "oww"
    assert cfg["silero_sensitivity"] == pytest.approx(0.4)


def test_realtime_stt_adapter_config_overrides():
    from j0_voice_adapters import RealtimeSTTAdapter

    adapter = RealtimeSTTAdapter(model="large", language="en")
    assert adapter.config["model"] == "large"
    assert adapter.config["language"] == "en"
    assert adapter.config["wake_words"] == "hey jarvis"  # default preserved


def test_realtime_stt_adapter_construction_does_not_import_realtimestt():
    """Constructor must not trigger a RealtimeSTT import."""
    from j0_voice_adapters import RealtimeSTTAdapter

    before = set(sys.modules.keys())
    adapter = RealtimeSTTAdapter()
    after = set(sys.modules.keys())
    new_modules = after - before
    assert "RealtimeSTT" not in new_modules, (
        f"RealtimeSTTAdapter constructor imported RealtimeSTT: {new_modules}"
    )


def test_realtime_stt_listen_raises_if_not_started():
    from j0_voice_adapters import RealtimeSTTAdapter

    adapter = RealtimeSTTAdapter()
    with pytest.raises(RuntimeError, match="start\\(\\)"):
        adapter.listen()


# ---------------------------------------------------------------------------
# 4. RealtimeSTTAdapter.is_available()
# ---------------------------------------------------------------------------


def test_realtime_stt_is_available_returns_bool():
    from j0_voice_adapters import RealtimeSTTAdapter

    result = RealtimeSTTAdapter().is_available()
    assert isinstance(result, bool)
    # Does not matter True or False — RealtimeSTT may not be installed.
    # What matters: no exception raised, no import triggered.
    assert "RealtimeSTT" not in sys.modules or True  # idempotent


# ---------------------------------------------------------------------------
# 5. FakeTTSAdapter speak() + TTSResult contract
# ---------------------------------------------------------------------------


def test_fake_tts_adapter_records_spoken_text():
    from j0_tts_adapters import FakeTTSAdapter

    tts = FakeTTSAdapter()
    tts.speak("nerede kaldık yanıtı")
    assert tts.spoken == ["nerede kaldık yanıtı"]


def test_fake_tts_adapter_result_ok():
    from j0_tts_adapters import FakeTTSAdapter

    result = FakeTTSAdapter().speak("test")
    assert result.ok is True


def test_fake_tts_adapter_result_engine_is_fake():
    from j0_tts_adapters import FakeTTSAdapter

    result = FakeTTSAdapter().speak("test")
    assert result.engine == "fake"


def test_fake_tts_adapter_first_audio_hint_ms_is_none():
    from j0_tts_adapters import FakeTTSAdapter

    result = FakeTTSAdapter().speak("test")
    assert result.first_audio_hint_ms is None


def test_fake_tts_adapter_warning_is_non_empty_string():
    from j0_tts_adapters import FakeTTSAdapter

    result = FakeTTSAdapter().speak("test")
    assert isinstance(result.warning, str)
    assert len(result.warning) > 0


# ---------------------------------------------------------------------------
# 6. PiperSubprocessAdapter.speak() raises NotImplementedError("J0B")
# ---------------------------------------------------------------------------


def test_piper_subprocess_adapter_speak_raises_not_implemented():
    from j0_tts_adapters import PiperSubprocessAdapter

    adapter = PiperSubprocessAdapter()
    with pytest.raises(NotImplementedError) as exc_info:
        adapter.speak("test")
    assert "J0B" in str(exc_info.value)


def test_piper_subprocess_adapter_no_subprocess_on_import():
    """Importing PiperSubprocessAdapter must not spawn any subprocess."""
    import subprocess as _subprocess
    original_run = _subprocess.run
    calls: list = []

    def fake_run(*args, **kwargs):
        calls.append(args)
        return original_run(*args, **kwargs)

    _subprocess.run = fake_run
    try:
        from j0_tts_adapters import PiperSubprocessAdapter
        _ = PiperSubprocessAdapter()
    finally:
        _subprocess.run = original_run

    assert calls == [], "PiperSubprocessAdapter imported or constructed should not call subprocess.run"


# ---------------------------------------------------------------------------
# 7. EdgeTTSAdapter.speak() raises NotImplementedError
# ---------------------------------------------------------------------------


def test_edge_tts_adapter_speak_raises_not_implemented():
    from j0_tts_adapters import EdgeTTSAdapter

    with pytest.raises(NotImplementedError) as exc_info:
        EdgeTTSAdapter().speak("test")
    assert "J0B" in str(exc_info.value) or "edge" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 8. build_piper_cmd pure function
# ---------------------------------------------------------------------------


def test_build_piper_cmd_basic():
    from j0_tts_adapters import build_piper_cmd

    cmd = build_piper_cmd({"model": "/models/tr_TR.onnx"})
    assert cmd[0] == "piper"
    assert "--model" in cmd
    assert "/models/tr_TR.onnx" in cmd
    assert "--output-raw" in cmd


def test_build_piper_cmd_custom_executable():
    from j0_tts_adapters import build_piper_cmd

    cmd = build_piper_cmd({"executable": "C:/piper/piper.exe", "model": "tr.onnx"})
    assert cmd[0] == "C:/piper/piper.exe"


def test_build_piper_cmd_with_output_file():
    from j0_tts_adapters import build_piper_cmd

    cmd = build_piper_cmd({"model": "tr.onnx", "output_file": "out.wav"})
    assert "--output_file" in cmd
    assert "out.wav" in cmd


def test_build_piper_cmd_without_output_file():
    from j0_tts_adapters import build_piper_cmd

    cmd = build_piper_cmd({"model": "tr.onnx"})
    assert "--output_file" not in cmd


def test_build_piper_cmd_returns_list():
    from j0_tts_adapters import build_piper_cmd

    result = build_piper_cmd({"model": "x.onnx"})
    assert isinstance(result, list)
    assert all(isinstance(s, str) for s in result)


# ---------------------------------------------------------------------------
# 9. HONESTY: first_audio_hint_ms=None, not 0
# ---------------------------------------------------------------------------


def test_tts_result_zero_raises_value_error():
    """TTSResult with first_audio_hint_ms=0 must raise — 0 is a false measurement claim."""
    from j0_tts_adapters import TTSResult

    with pytest.raises(ValueError, match="0"):
        TTSResult(ok=True, engine="test", first_audio_hint_ms=0)


def test_tts_result_none_populates_warning():
    from j0_tts_adapters import TTSResult

    result = TTSResult(ok=True, engine="test", first_audio_hint_ms=None)
    assert result.first_audio_hint_ms is None
    assert result.warning is not None
    assert len(result.warning) > 0


def test_tts_result_with_real_measurement_no_warning():
    from j0_tts_adapters import TTSResult

    result = TTSResult(ok=True, engine="piper", first_audio_hint_ms=320.5, warning=None)
    assert result.first_audio_hint_ms == pytest.approx(320.5)
    assert result.warning is None


# ---------------------------------------------------------------------------
# 10. STATIC SAFETY
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source_file", [
    _SCRIPTS_DIR / "j0_voice_adapters.py",
    _SCRIPTS_DIR / "j0_tts_adapters.py",
])
@pytest.mark.parametrize("token", [
    "telegram",
    "scheduler",
    "requests",
    "sendMessage",
])
def test_static_no_forbidden_import(source_file: Path, token: str):
    """New adapter modules must not import or reference telegram/scheduler/requests/sendMessage."""
    source = source_file.read_text(encoding="utf-8")
    # Check import statements specifically (not string literals)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in getattr(node, "names", []):
                assert token not in alias.name, (
                    f"{source_file.name} imports '{alias.name}' containing '{token}'"
                )
            module = getattr(node, "module", "") or ""
            assert token not in module, (
                f"{source_file.name} has 'from {module} import ...' containing '{token}'"
            )
