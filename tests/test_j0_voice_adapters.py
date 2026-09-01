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


def test_realtime_stt_is_available_false_when_spec_missing():
    """is_available() returns False when importlib.util.find_spec cannot locate RealtimeSTT."""
    import importlib.util as _ilu
    from j0_voice_adapters import RealtimeSTTAdapter

    original = _ilu.find_spec

    def _missing(name, *args, **kwargs):
        if name == "RealtimeSTT":
            return None
        return original(name, *args, **kwargs)

    _ilu.find_spec = _missing
    try:
        result = RealtimeSTTAdapter().is_available()
    finally:
        _ilu.find_spec = original

    assert result is False


def test_realtime_stt_is_available_true_when_spec_found():
    """is_available() returns True when importlib.util.find_spec locates the package."""
    import importlib.util as _ilu
    from types import SimpleNamespace
    from j0_voice_adapters import RealtimeSTTAdapter

    original = _ilu.find_spec
    fake_spec = SimpleNamespace(name="RealtimeSTT")

    def _present(name, *args, **kwargs):
        if name == "RealtimeSTT":
            return fake_spec
        return original(name, *args, **kwargs)

    _ilu.find_spec = _present
    try:
        result = RealtimeSTTAdapter().is_available()
    finally:
        _ilu.find_spec = original

    assert result is True


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
# 6. PiperSubprocessAdapter.speak() -- kapi degisti (2026-08-31, Esik 1)
#
# ESKI SOZLESME: speak() kosulsuz NotImplementedError firlatirdi.
# YENI SOZLESME: speak() calisir, ama onkosullar dogrulanmadan CALISMAZ ve
# basarisizligi firlatmak yerine TTSResult olarak dondurur.
#
# Guvenlik ozelligi kaldirilmadi, yer degistirdi: "hic calismaz" ->
# "yalnizca mutlak + var olan yollarla calisir; PATH aranmaz, indirme yapilmaz".
# Bu bir sozlesme degisikligidir ve Ahmet'in acik talimatiyla yapilmistir.
# ---------------------------------------------------------------------------


def test_piper_speak_without_prerequisites_returns_error_not_raises():
    """Onkosul yoksa: exception DEGIL, yapisal hata donmeli."""
    from j0_tts_adapters import PiperSubprocessAdapter

    result = PiperSubprocessAdapter().speak("test")
    assert result.ok is False
    assert result.engine == "piper"
    assert result.first_audio_hint_ms is None
    assert "piper_not_run" in (result.warning or "")


def test_piper_speak_refuses_relative_executable():
    """Mutlak olmayan yol reddedilmeli -- PATH araması yapilmaz."""
    from j0_tts_adapters import PiperSubprocessAdapter

    called = []

    def spy_runner(argv, text, timeout):
        called.append(argv)
        raise AssertionError("onkosul gecmeden runner cagrilmamali")

    result = PiperSubprocessAdapter(
        {"executable": "piper", "model": "voice.onnx"}, runner=spy_runner
    ).speak("test")
    assert result.ok is False
    assert "executable_not_absolute" in (result.warning or "")
    assert called == []


def test_piper_speak_runs_when_prerequisites_are_met(tmp_path):
    """Onkosullar saglandiginda gercek yurutme yolu calisir.

    Piper ikilisi bu makinede YOK; bu yuzden runner enjekte ediliyor.
    Test edilen sey: dogru argv olusuyor, metin stdin'e gidiyor, sonuc ok.
    """
    from j0_tts_adapters import PiperSubprocessAdapter

    exe = tmp_path / "piper.exe"
    exe.write_text("", encoding="utf-8")
    model = tmp_path / "tr_TR-voice.onnx"
    model.write_text("", encoding="utf-8")

    seen = {}

    class _Done:
        returncode = 0
        stderr = b""

    def fake_runner(argv, text, timeout):
        seen["argv"] = argv
        seen["text"] = text
        seen["timeout"] = timeout
        return _Done()

    result = PiperSubprocessAdapter(
        {"executable": str(exe), "model": str(model)}, runner=fake_runner
    ).speak("Merhaba efendim")

    assert result.ok is True
    assert result.engine == "piper"
    assert result.first_audio_hint_ms is not None
    assert seen["text"] == "Merhaba efendim"
    assert seen["argv"][0] == str(exe)
    assert "--model" in seen["argv"] and str(model) in seen["argv"]
    assert seen["timeout"] <= 60.0


def test_piper_speak_reports_nonzero_exit(tmp_path):
    from j0_tts_adapters import PiperSubprocessAdapter

    exe = tmp_path / "piper.exe"
    exe.write_text("", encoding="utf-8")
    model = tmp_path / "v.onnx"
    model.write_text("", encoding="utf-8")

    class _Failed:
        returncode = 3
        stderr = b"model yuklenemedi"

    result = PiperSubprocessAdapter(
        {"executable": str(exe), "model": str(model)},
        runner=lambda a, t, to: _Failed(),
    ).speak("test")

    assert result.ok is False
    assert "exit_3" in (result.warning or "")
    assert "model yuklenemedi" in (result.warning or "")


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
# 7. EdgeTTSAdapter.speak() -- kapi degisti (2026-08-31, Esik 1)
#
# Edge TTS bir BULUT servisidir: metin bu makineden cikar. Kapi kaldirilmadi;
# "hic calismaz" yerine "yalnizca JARVIS_J0_EDGE_TTS_ENABLED=1 ile calisir".
# Veri-egress kurali icin bkz. CLAUDE.md 7.
# ---------------------------------------------------------------------------


def test_edge_tts_disabled_by_default(monkeypatch):
    """Bayrak yoksa: ag'a CIKILMAZ, exception da firlatilmaz."""
    from j0_tts_adapters import EDGE_TTS_ENABLE_FLAG, EdgeTTSAdapter

    monkeypatch.delenv(EDGE_TTS_ENABLE_FLAG, raising=False)

    def exploding_synth(text, voice):
        raise AssertionError("kapaliyken sentez cagrilmamali")

    result = EdgeTTSAdapter(synth=exploding_synth).speak("test")
    assert result.ok is False
    assert "disabled" in (result.warning or "")
    assert EDGE_TTS_ENABLE_FLAG in (result.warning or "")


def test_edge_tts_flag_must_be_exactly_one(monkeypatch):
    from j0_tts_adapters import EDGE_TTS_ENABLE_FLAG, EdgeTTSAdapter

    for deger in ("0", "true", "yes", ""):
        monkeypatch.setenv(EDGE_TTS_ENABLE_FLAG, deger)
        assert EdgeTTSAdapter().is_enabled() is False, f"{deger!r} acmamali"
    monkeypatch.setenv(EDGE_TTS_ENABLE_FLAG, "1")
    assert EdgeTTSAdapter().is_enabled() is True


def test_edge_tts_runs_when_enabled():
    """Acikken tam yol calisir. Ag ve ses cihazi enjekte edilerek atlanir."""
    from j0_tts_adapters import EdgeTTSAdapter

    seen = {}

    def fake_synth(text, voice):
        seen["text"] = text
        seen["voice"] = voice
        return "C:/tmp/ses.mp3"

    def fake_player(path):
        seen["played"] = path

    result = EdgeTTSAdapter(
        voice="tr-TR-AhmetNeural",
        synth=fake_synth,
        player=fake_player,
        enabled=True,
    ).speak("Merhaba efendim")

    assert result.ok is True
    assert result.engine == "edge-tts"
    assert result.first_audio_hint_ms is not None
    assert seen["text"] == "Merhaba efendim"
    assert seen["voice"] == "tr-TR-AhmetNeural"
    assert seen["played"] == "C:/tmp/ses.mp3"


def test_edge_tts_empty_text_refused():
    from j0_tts_adapters import EdgeTTSAdapter

    for bos in ("", "   ", None):
        result = EdgeTTSAdapter(enabled=True).speak(bos)
        assert result.ok is False
        assert "text_empty" in (result.warning or "")


def test_edge_tts_surfaces_synthesis_failure():
    """Hata yutulmaz; TTSResult icinde gorunur kalir."""
    from j0_tts_adapters import EdgeTTSAdapter

    def broken_synth(text, voice):
        raise RuntimeError("ag yok")

    result = EdgeTTSAdapter(synth=broken_synth, enabled=True).speak("test")
    assert result.ok is False
    assert "synthesis_error" in (result.warning or "")
    assert "ag yok" in (result.warning or "")


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


# ---------------------------------------------------------------------------
# 11. LOOP-0E PHASE A — Piper dry-run command planning (no subprocess ever)
# ---------------------------------------------------------------------------


def _make_fake_piper_files(tmp_path):
    exe = tmp_path / "piper.exe"
    exe.write_bytes(b"fake-exe")
    model = tmp_path / "tr_TR.onnx"
    model.write_bytes(b"fake-model")
    return str(exe), str(model)


def test_build_piper_dry_run_plan_argv_is_list_not_shell_string(tmp_path):
    """Req 1: command builder returns a list of individual arguments."""
    from j0_tts_adapters import build_piper_dry_run_plan

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="Merhaba Ahmet. JARVIS ses hattı güvenli testtedir.",
        timeout_seconds=10, allowed_output_root=str(root),
    )

    assert plan.ok is True
    assert isinstance(plan.argv, list)
    assert all(isinstance(a, str) for a in plan.argv)
    assert not isinstance(plan.argv, str)


def test_j0_tts_adapters_source_never_uses_shell_true():
    """Req 2: shell=True must never appear in the Phase A source file."""
    source = (_SCRIPTS_DIR / "j0_tts_adapters.py").read_text(encoding="utf-8")
    assert "shell=True" not in source


def test_validate_piper_paths_executable_not_absolute(tmp_path):
    """Req 3: executable path must be absolute."""
    from j0_tts_adapters import validate_piper_paths

    _, model = _make_fake_piper_files(tmp_path)
    result = validate_piper_paths("piper.exe", model)
    assert result.ok is False
    assert result.reason == "executable_not_absolute"


def test_validate_piper_paths_model_not_absolute(tmp_path):
    """Req 4: model path must be absolute."""
    from j0_tts_adapters import validate_piper_paths

    exe, _ = _make_fake_piper_files(tmp_path)
    result = validate_piper_paths(exe, "tr_TR.onnx")
    assert result.ok is False
    assert result.reason == "model_not_absolute"


def test_validate_piper_output_path_rejects_non_wav(tmp_path):
    """Req 5: output path must end with .wav."""
    from j0_tts_adapters import validate_piper_output_path

    root = tmp_path / "manual_piper_smoke"
    result = validate_piper_output_path(str(root / "out.mp3"), allowed_root=str(root))
    assert result.ok is False
    assert result.reason == "output_not_wav"


def test_validate_piper_output_path_accepts_wav_inside_root(tmp_path):
    from j0_tts_adapters import validate_piper_output_path

    root = tmp_path / "manual_piper_smoke"
    result = validate_piper_output_path(str(root / "out.wav"), allowed_root=str(root))
    assert result.ok is True


def test_validate_piper_output_path_rejects_outside_allowed_root(tmp_path):
    """Req 6: output path restricted to the allowed local output root."""
    from j0_tts_adapters import validate_piper_output_path

    root = tmp_path / "manual_piper_smoke"
    other = tmp_path / "elsewhere" / "out.wav"
    result = validate_piper_output_path(str(other), allowed_root=str(root))
    assert result.ok is False
    assert result.reason == "output_outside_allowed_root"


def test_validate_piper_output_path_rejects_traversal(tmp_path):
    """Req 7: path traversal outside the allowed root is rejected."""
    from j0_tts_adapters import validate_piper_output_path

    root = tmp_path / "manual_piper_smoke"
    traversal = str(root / ".." / "evil.wav")
    result = validate_piper_output_path(traversal, allowed_root=str(root))
    assert result.ok is False
    assert result.reason == "output_outside_allowed_root"


@pytest.mark.parametrize("bad_timeout", [0, -1, 61, 1000, "10", None, True])
def test_validate_piper_timeout_rejects_invalid_values(bad_timeout):
    """Req 8: timeout must be explicit, positive and bounded."""
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(bad_timeout)
    assert result.ok is False
    assert result.reason == "invalid_timeout"


def test_validate_piper_timeout_accepts_valid_value():
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(10)
    assert result.ok is True


# ---------------------------------------------------------------------------
# ISSUE 1 (manual follow-up) — finite timeout regression
# ---------------------------------------------------------------------------
#
# validate_piper_timeout() previously accepted float("nan") because NaN
# comparisons (<=, >) are both False, letting it slip past the bounds check.
# math.isfinite() now rejects NaN/+inf/-inf explicitly. These tests pin that
# fix and its neighboring bool/zero/negative/over-max/valid-value behavior.


def test_validate_piper_timeout_rejects_nan():
    """Req 1: float('nan') must be rejected — never silently accepted."""
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(float("nan"))
    assert result.ok is False
    assert result.reason == "invalid_timeout"


def test_validate_piper_timeout_rejects_positive_infinity():
    """Req 2: float('inf') must be rejected."""
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(float("inf"))
    assert result.ok is False
    assert result.reason == "invalid_timeout"


def test_validate_piper_timeout_rejects_negative_infinity():
    """Req 3: float('-inf') must be rejected."""
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(float("-inf"))
    assert result.ok is False
    assert result.reason == "invalid_timeout"


def test_validate_piper_timeout_rejects_bool_true():
    """Req 4: True must be rejected even though bool is a subclass of int."""
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(True)
    assert result.ok is False
    assert result.reason == "invalid_timeout"


def test_validate_piper_timeout_rejects_bool_false():
    """Req 5: False must be rejected even though bool is a subclass of int."""
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(False)
    assert result.ok is False
    assert result.reason == "invalid_timeout"


def test_validate_piper_timeout_rejects_zero():
    """Req 6: zero must be rejected."""
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(0)
    assert result.ok is False
    assert result.reason == "invalid_timeout"


def test_validate_piper_timeout_rejects_negative_finite_value():
    """Req 7: a negative finite value must be rejected."""
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(-5.0)
    assert result.ok is False
    assert result.reason == "invalid_timeout"


def test_validate_piper_timeout_rejects_value_above_maximum():
    """Req 8: a value above the configured maximum must be rejected."""
    from j0_tts_adapters import validate_piper_timeout, PIPER_DRY_RUN_MAX_TIMEOUT_SECONDS

    result = validate_piper_timeout(PIPER_DRY_RUN_MAX_TIMEOUT_SECONDS + 1)
    assert result.ok is False
    assert result.reason == "invalid_timeout"


def test_validate_piper_timeout_accepts_valid_integer():
    """Req 9: a valid finite integer timeout remains accepted."""
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(15)
    assert result.ok is True


def test_validate_piper_timeout_accepts_valid_finite_float():
    """Req 10: a valid finite float timeout remains accepted."""
    from j0_tts_adapters import validate_piper_timeout

    result = validate_piper_timeout(10.5)
    assert result.ok is True


def test_validate_piper_timeout_does_not_raise_on_invalid_values():
    """No uncontrolled exception for any invalid value — always a structured result."""
    from j0_tts_adapters import validate_piper_timeout

    for bad in (float("nan"), float("inf"), float("-inf"), True, False, 0, -1, 999, "10", None, [], {}):
        result = validate_piper_timeout(bad)
        assert result.ok is False
        assert result.reason == "invalid_timeout"


def test_validate_piper_text_rejects_too_long():
    """Req 9: oversized text returns a structured failure."""
    from j0_tts_adapters import validate_piper_text, PIPER_DRY_RUN_MAX_TEXT_LENGTH

    result = validate_piper_text("x" * (PIPER_DRY_RUN_MAX_TEXT_LENGTH + 1))
    assert result.ok is False
    assert result.reason == "text_too_long"


def test_build_piper_dry_run_plan_text_too_long_is_structured_failure(tmp_path):
    from j0_tts_adapters import build_piper_dry_run_plan, PIPER_DRY_RUN_MAX_TEXT_LENGTH

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="x" * (PIPER_DRY_RUN_MAX_TEXT_LENGTH + 1),
        timeout_seconds=10, allowed_output_root=str(root),
    )
    assert plan.ok is False
    assert plan.reason == "text_too_long"


def test_build_piper_dry_run_plan_shell_like_text_does_not_alter_argv_positions(tmp_path):
    """Req 10: shell-metacharacter text must not change argv positions or shape."""
    from j0_tts_adapters import build_piper_dry_run_plan

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    baseline = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="Merhaba Ahmet. JARVIS ses hattı güvenli testtedir.",
        timeout_seconds=10, allowed_output_root=str(root),
    )
    dangerous = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="; rm -rf / && echo $(whoami) | evil `cmd` > out.txt",
        timeout_seconds=10, allowed_output_root=str(root),
    )

    assert baseline.ok is True and dangerous.ok is True
    assert baseline.argv == dangerous.argv == [exe, "--model", model, "--output_file", out]
    for arg in dangerous.argv:
        assert arg in (exe, "--model", model, "--output_file", out)


def test_validate_piper_paths_executable_missing_is_structured_failure(tmp_path):
    """Req 11: missing executable is a structured prerequisite failure, not a crash."""
    from j0_tts_adapters import validate_piper_paths

    _, model = _make_fake_piper_files(tmp_path)
    missing_exe = str(tmp_path / "does_not_exist_piper.exe")
    result = validate_piper_paths(missing_exe, model)
    assert result.ok is False
    assert result.reason == "executable_missing"


def test_validate_piper_paths_model_missing_is_structured_failure(tmp_path):
    """Req 12: missing model is a structured prerequisite failure, not a crash."""
    from j0_tts_adapters import validate_piper_paths

    exe, _ = _make_fake_piper_files(tmp_path)
    missing_model = str(tmp_path / "does_not_exist.onnx")
    result = validate_piper_paths(exe, missing_model)
    assert result.ok is False
    assert result.reason == "model_missing"


def test_dry_run_plan_never_calls_subprocess_run_or_popen(tmp_path, monkeypatch):
    """Req 13/14: dry-run never calls subprocess.run or subprocess.Popen."""
    import subprocess as _subprocess
    from j0_tts_adapters import build_piper_dry_run_plan

    calls: list = []
    monkeypatch.setattr(_subprocess, "run", lambda *a, **k: calls.append(("run", a, k)))
    monkeypatch.setattr(_subprocess, "Popen", lambda *a, **k: calls.append(("Popen", a, k)))

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="Merhaba Ahmet. JARVIS ses hattı güvenli testtedir.",
        timeout_seconds=10, allowed_output_root=str(root),
    )

    assert plan.ok is True
    assert calls == []


def test_dry_run_plan_never_calls_os_system_or_playback(tmp_path, monkeypatch):
    """Req 15: dry-run never calls os.system or any playback function."""
    import os as _os
    from j0_tts_adapters import build_piper_dry_run_plan

    calls: list = []
    monkeypatch.setattr(_os, "system", lambda *a, **k: calls.append(("system", a, k)))

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="Merhaba Ahmet. JARVIS ses hattı güvenli testtedir.",
        timeout_seconds=10, allowed_output_root=str(root),
    )

    assert plan.ok is True
    assert calls == []


def test_dry_run_plan_never_touches_network_socket(tmp_path, monkeypatch):
    """Req 16: no network call occurs during dry-run planning."""
    import socket as _socket
    from j0_tts_adapters import build_piper_dry_run_plan

    def _forbidden(*a, **k):
        raise AssertionError("dry-run must never open a network socket")

    monkeypatch.setattr(_socket, "socket", _forbidden)
    monkeypatch.setattr(_socket, "create_connection", _forbidden)

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="Merhaba Ahmet. JARVIS ses hattı güvenli testtedir.",
        timeout_seconds=10, allowed_output_root=str(root),
    )
    assert plan.ok is True


def test_dry_run_plan_never_reads_environ(tmp_path, monkeypatch):
    """Req 17: no .env/secrets/environment access occurs during dry-run planning."""
    from j0_tts_adapters import build_piper_dry_run_plan

    class _ForbiddenEnviron(dict):
        def __getitem__(self, key):
            raise AssertionError(f"dry-run must never read os.environ[{key!r}]")

        def get(self, key, default=None):
            raise AssertionError(f"dry-run must never read os.environ.get({key!r})")

    monkeypatch.setattr("os.environ", _ForbiddenEnviron())

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="Merhaba Ahmet. JARVIS ses hattı güvenli testtedir.",
        timeout_seconds=10, allowed_output_root=str(root),
    )
    assert plan.ok is True


def test_real_piper_execution_remains_unreachable_from_dry_run_plan(tmp_path):
    """Req 18: dry-run plan objects have no way to trigger real execution.

    Bu ozellik korunuyor. Degisen tek sey: speak() artik NotImplementedError
    firlatmiyor, onkosul dogrulamasinda duruyor. Plan objesinin kendisi hala
    hicbir yurutme yolu sunmuyor -- kritik olan buydu.
    """
    from j0_tts_adapters import PiperCommandPlan, PiperSubprocessAdapter

    assert not hasattr(PiperCommandPlan, "execute")
    assert not hasattr(PiperCommandPlan, "run")

    # Onkosulsuz speak() yurutmeye gecmez: yapisal hata doner.
    result = PiperSubprocessAdapter().speak("test")
    assert result.ok is False
    assert "piper_not_run" in (result.warning or "")


def test_dry_run_plan_ok_result_metadata_points_to_wav_without_playing(tmp_path, monkeypatch):
    """Req 19: output metadata points to a .wav target but nothing plays it."""
    import os as _os
    from j0_tts_adapters import build_piper_dry_run_plan

    played: list = []
    monkeypatch.setattr(_os, "startfile", lambda *a, **k: played.append(a), raising=False)

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="Merhaba Ahmet. JARVIS ses hattı güvenli testtedir.",
        timeout_seconds=10, allowed_output_root=str(root),
    )

    assert plan.ok is True
    assert plan.output_path.endswith(".wav")
    assert played == []


def test_manual_phase_b_command_can_be_documented_without_execution(tmp_path, monkeypatch):
    """Req 20: the manual Phase B command can be derived/documented without running it."""
    import subprocess as _subprocess
    from j0_tts_adapters import build_piper_dry_run_plan

    calls: list = []
    monkeypatch.setattr(_subprocess, "run", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(_subprocess, "Popen", lambda *a, **k: calls.append(a))

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="Merhaba Ahmet. JARVIS ses hattı güvenli testtedir.",
        timeout_seconds=10, allowed_output_root=str(root),
    )

    assert plan.ok is True
    manual_command_hint = " ".join(plan.argv)
    assert isinstance(manual_command_hint, str)
    assert exe in manual_command_hint
    assert model in manual_command_hint
    assert calls == []


# ---------------------------------------------------------------------------
# ISSUE 2 (manual follow-up) — Phase B manual-handoff argument-mapping regression
# ---------------------------------------------------------------------------
#
# The prior report's manual template used `argv = sys.argv[1:5]` (4 items)
# together with `text = sys.argv[5]` (a 6-argument invocation), which meant
# the output-file value was never placed in argv and the output path was
# treated as synthesis text instead. The corrected mapping is four explicit
# positional values after the script name: executable, model, output_path,
# text — reusing build_piper_dry_run_plan's existing argv shape rather than
# inventing a new command-rendering framework. No subprocess is started by
# any test in this section.


def test_manual_handoff_output_path_immediately_follows_output_file_flag(tmp_path):
    """Output path must sit at argv[index('--output_file') + 1]."""
    from j0_tts_adapters import build_piper_dry_run_plan

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="Merhaba Ahmet. JARVIS ses hattı güvenli testtedir.",
        timeout_seconds=15, allowed_output_root=str(root),
    )

    assert plan.ok is True
    idx = plan.argv.index("--output_file")
    assert plan.argv[idx + 1] == out
    assert out.endswith(".wav")


def test_manual_handoff_text_is_never_part_of_argv(tmp_path):
    """Synthesis text must never appear in argv, whole or as a substring of any arg."""
    from j0_tts_adapters import build_piper_dry_run_plan

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")
    text = "Merhaba Ahmet. JARVIS ses hattı güvenli testtedir."

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text=text, timeout_seconds=15, allowed_output_root=str(root),
    )

    assert plan.ok is True
    assert text not in plan.argv
    for arg in plan.argv:
        assert text not in arg


def test_manual_handoff_four_argument_mapping_has_no_off_by_one(tmp_path):
    """Regression for the fixed off-by-one bug.

    Corrected mapping is exactly four explicit positional values after the
    script name: piper_exe, model_onnx, out_file, text = sys.argv[1:5].
    This must reproduce the identical argv shape produced by
    build_piper_dry_run_plan, and text must be usable only as stdin/input
    metadata, never as a fifth trailing argv slot (the old, wrong
    `text = sys.argv[5]` six-argument invocation is not reproduced here).
    """
    from j0_tts_adapters import build_piper_dry_run_plan

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")
    text = "Merhaba Ahmet. JARVIS ses hattı güvenli testtedir."

    # Simulates the corrected manual wrapper's sys.argv parsing: exactly
    # four values after the script name, no fifth trailing text argument.
    fake_sys_argv = ["manual_wrapper.py", exe, model, out, text]
    assert len(fake_sys_argv) == 5  # script name + 4 positional values only

    piper_exe, model_onnx, out_file, parsed_text = fake_sys_argv[1:5]
    manual_argv = [piper_exe, "--model", model_onnx, "--output_file", out_file]

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text=text, timeout_seconds=15, allowed_output_root=str(root),
    )

    assert plan.ok is True
    assert manual_argv == plan.argv
    assert parsed_text == text
    assert parsed_text not in manual_argv
    assert out_file.endswith(".wav")


def test_manual_handoff_command_plan_targets_wav_without_subprocess(tmp_path, monkeypatch):
    """Command plan targets a .wav file; no subprocess is started to verify this."""
    import subprocess as _subprocess
    from j0_tts_adapters import build_piper_dry_run_plan

    calls: list = []
    monkeypatch.setattr(_subprocess, "run", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(_subprocess, "Popen", lambda *a, **k: calls.append(a))

    exe, model = _make_fake_piper_files(tmp_path)
    root = tmp_path / "manual_piper_smoke"
    out = str(root / "jarvis_loop0e_first_voice.wav")

    plan = build_piper_dry_run_plan(
        executable=exe, model=model, output_path=out,
        text="Merhaba Ahmet. JARVIS ses hattı güvenli testtedir.",
        timeout_seconds=15, allowed_output_root=str(root),
    )

    assert plan.ok is True
    assert plan.output_path.endswith(".wav")
    assert calls == []
