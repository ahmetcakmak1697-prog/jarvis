"""
tests/test_j0_voice_loop.py — Voice loop routing, CLI, and wiring tests.

Coverage:
  1) IMPORT SAFETY — importing j0_voice_loop with env off does not import RealtimeSTT
  2) DEFAULT-OFF CLI subprocess — exit 0, UTF-8 bytes, "disabled", no mojibake
  3) _ascii_fold handles Turkish İ/Ş/Ğ/Ü/Ö/Ç/ı
  4) _matches_status_intent — positive and negative cases
  5) ROUTE BEHAVIOR — injected status_provider called; response contains live marker
  6) LIVE WIRING — different in_progress content changes response (not canned text)
  7) TTS CONTRACT — FakeTTSAdapter.spoken grows by 1 per run_one_turn
  8) STATIC SAFETY — no telegram/scheduler/requests/sendMessage
  9) UTF-8 bytes — subprocess stdout strict decode
 10) Mojibake guard — no \\xc3/\\xc4/\\xc5/\\xef\\xbf\\xbd in output
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pytest

# Ensure scripts/ is on sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VOICE_LOOP_PATH = _SCRIPTS_DIR / "j0_voice_loop.py"
_IMPORT_SAFETY_MODULES = {"RealtimeSTT", "sounddevice", "pyaudio"}

_MOJIBAKE_MARKERS = [
    "Ã",   # UTF-8 MSB from 2-byte sequence decoded as latin-1
    "Ä",
    "Å",
    "�",   # replacement character
]


# ---------------------------------------------------------------------------
# Fake LiveStatus — duck-typed, no real j0_live_status import needed in tests
# ---------------------------------------------------------------------------


@dataclass
class _FakeLiveStatus:
    """Minimal duck-typed LiveStatus for routing tests."""
    _summary: str

    def text_summary(self) -> str:
        return self._summary


def _make_fake_provider(summary: str):
    """Return a callable status_provider returning _FakeLiveStatus(summary)."""
    status = _FakeLiveStatus(summary)

    def provider():
        return status

    return provider


# ---------------------------------------------------------------------------
# 1. IMPORT SAFETY
# ---------------------------------------------------------------------------


def test_import_voice_loop_does_not_load_realtimestt(monkeypatch):
    """Importing j0_voice_loop with env off must not load RealtimeSTT."""
    monkeypatch.setenv("JARVIS_J0_REALTIME_ENABLED", "0")
    for mod in list(_IMPORT_SAFETY_MODULES):
        assert mod not in sys.modules

    import j0_voice_loop  # noqa: F401

    for mod in _IMPORT_SAFETY_MODULES:
        assert mod not in sys.modules, (
            f"importing j0_voice_loop caused {mod} to be imported"
        )


# ---------------------------------------------------------------------------
# 2. DEFAULT-OFF CLI subprocess
# ---------------------------------------------------------------------------


def _run_voice_loop_subprocess(env_override: dict) -> subprocess.CompletedProcess:
    env = {**os.environ, **env_override}
    return subprocess.run(
        [sys.executable, str(_VOICE_LOOP_PATH)],
        capture_output=True,
        env=env,
    )


def test_default_off_cli_exit_zero():
    result = _run_voice_loop_subprocess({"JARVIS_J0_REALTIME_ENABLED": "0"})
    assert result.returncode == 0, (
        f"Expected exit 0; got {result.returncode}. stderr: {result.stderr!r}"
    )


def test_default_off_cli_stdout_is_valid_utf8():
    result = _run_voice_loop_subprocess({"JARVIS_J0_REALTIME_ENABLED": "0"})
    # Strict decode — must not raise
    decoded = result.stdout.decode("utf-8", errors="strict")
    assert len(decoded) > 0


def test_default_off_cli_output_contains_disabled():
    result = _run_voice_loop_subprocess({"JARVIS_J0_REALTIME_ENABLED": "0"})
    decoded = result.stdout.decode("utf-8")
    assert "disabled" in decoded.lower(), (
        f"Expected 'disabled' in output; got: {decoded!r}"
    )


def test_default_off_cli_no_mojibake():
    result = _run_voice_loop_subprocess({"JARVIS_J0_REALTIME_ENABLED": "0"})
    decoded = result.stdout.decode("utf-8")
    for marker in _MOJIBAKE_MARKERS:
        assert marker not in decoded, (
            f"Mojibake marker {marker!r} found in CLI output: {decoded!r}"
        )


def test_default_off_cli_stdout_contains_env_key():
    result = _run_voice_loop_subprocess({"JARVIS_J0_REALTIME_ENABLED": "0"})
    decoded = result.stdout.decode("utf-8")
    assert "JARVIS_J0_REALTIME_ENABLED" in decoded


def test_env_on_no_real_mic_flag_exits_zero():
    """env=1 but no --real-mic: should still exit 0 with disabled status."""
    result = _run_voice_loop_subprocess({"JARVIS_J0_REALTIME_ENABLED": "1"})
    assert result.returncode == 0
    decoded = result.stdout.decode("utf-8")
    assert "disabled" in decoded.lower()
    assert "real-mic" in decoded or "--real-mic" in decoded


# ---------------------------------------------------------------------------
# 3. _ascii_fold
# ---------------------------------------------------------------------------


def test_ascii_fold_lower_turkish_chars():
    from j0_voice_loop import _ascii_fold

    assert _ascii_fold("ç") == "c"
    assert _ascii_fold("ğ") == "g"
    assert _ascii_fold("ı") == "i"
    assert _ascii_fold("ş") == "s"
    assert _ascii_fold("ö") == "o"
    assert _ascii_fold("ü") == "u"


def test_ascii_fold_upper_turkish_chars():
    from j0_voice_loop import _ascii_fold

    assert _ascii_fold("Ç") == "c"
    assert _ascii_fold("Ğ") == "g"
    assert _ascii_fold("İ") == "i"   # U+0130 dotted-I — the tricky one
    assert _ascii_fold("Ş") == "s"
    assert _ascii_fold("Ö") == "o"
    assert _ascii_fold("Ü") == "u"


def test_ascii_fold_mixed_phrase():
    from j0_voice_loop import _ascii_fold

    result = _ascii_fold("Nerede Kaldık")
    assert result == "nerede kaldik"


def test_ascii_fold_preserves_ascii():
    from j0_voice_loop import _ascii_fold

    assert _ascii_fold("abc123") == "abc123"


# ---------------------------------------------------------------------------
# 4. _matches_status_intent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phrase", [
    "nerede kaldık",
    "Nerede kaldık?",      # uppercase N
    "son commit neydi",
    "en son ne yaptık",
    "bugün ne yapacağız",
    "NEREDE KALDIK",       # all caps
])
def test_matches_status_intent_true(phrase: str):
    from j0_voice_loop import _matches_status_intent

    assert _matches_status_intent(phrase) is True, (
        f"Expected True for {phrase!r}"
    )


@pytest.mark.parametrize("phrase", [
    "hava nasıl",
    "müzik çal",
    "alarm kur",
    "",
    "hello world",
])
def test_matches_status_intent_false(phrase: str):
    from j0_voice_loop import _matches_status_intent

    assert _matches_status_intent(phrase) is False, (
        f"Expected False for {phrase!r}"
    )


# ---------------------------------------------------------------------------
# 5. ROUTE BEHAVIOR — injected status_provider called; response contains live marker
# ---------------------------------------------------------------------------


def test_route_and_respond_calls_status_provider():
    from j0_voice_loop import route_and_respond

    called = [False]

    def fake_provider():
        called[0] = True
        return _FakeLiveStatus("LIVE_MARKER_XYZ status here")

    response = route_and_respond("nerede kaldık", status_provider=fake_provider)
    assert called[0] is True


def test_route_and_respond_response_contains_live_marker():
    from j0_voice_loop import route_and_respond

    unique_marker = "SPRINT_J0A_LIVE_MARKER_42"
    provider = _make_fake_provider(f"HEAD: abc123 — {unique_marker} in progress")
    response = route_and_respond("nerede kaldık", status_provider=provider)
    assert unique_marker in response


def test_route_and_respond_son_commit_neydi():
    from j0_voice_loop import route_and_respond

    provider = _make_fake_provider("HEAD: xyz — feat: test commit\nSon commitler: ...")
    response = route_and_respond("son commit neydi", status_provider=provider)
    assert "feat: test commit" in response


def test_route_and_respond_unknown_returns_fallback():
    from j0_voice_loop import route_and_respond

    response = route_and_respond(
        "hava nasıl",
        status_provider=_make_fake_provider("should not appear"),
    )
    # Must NOT contain the injected status (wrong route)
    assert "should not appear" not in response
    assert len(response) > 0  # some fallback response


# ---------------------------------------------------------------------------
# 6. LIVE WIRING — different in_progress content changes response
# ---------------------------------------------------------------------------


def test_different_in_progress_content_changes_response():
    """Proves live-tool wiring: different injected content → different response."""
    from j0_voice_loop import route_and_respond

    provider_a = _make_fake_provider(
        "HEAD: aaa — step-A in progress\n"
        "Şu an devam eden:\n  FAZ-0 - Temel sistem\n"
    )
    provider_b = _make_fake_provider(
        "HEAD: bbb — step-B in progress\n"
        "Şu an devam eden:\n  FAZ-99 - Farklı adım\n"
    )

    resp_a = route_and_respond("nerede kaldık", status_provider=provider_a)
    resp_b = route_and_respond("nerede kaldık", status_provider=provider_b)

    assert resp_a != resp_b, (
        "Different injected statuses must produce different responses (live wiring check)"
    )
    assert "FAZ-0" in resp_a
    assert "FAZ-99" in resp_b


# ---------------------------------------------------------------------------
# 7. TTS CONTRACT — FakeTTSAdapter.spoken grows by 1 per run_one_turn
# ---------------------------------------------------------------------------


def test_run_one_turn_tts_receives_response():
    from j0_voice_loop import run_one_turn
    from j0_voice_adapters import FakeSTTAdapter
    from j0_tts_adapters import FakeTTSAdapter

    stt = FakeSTTAdapter(["nerede kaldık"])
    tts = FakeTTSAdapter()
    provider = _make_fake_provider("HEAD: abc — MARKER_TTS_CONTRACT")

    response = run_one_turn(stt, tts, status_provider=provider)

    assert len(tts.spoken) == 1
    assert tts.spoken[0] == response
    assert "MARKER_TTS_CONTRACT" in response


def test_run_one_turn_unknown_phrase_tts_receives_fallback():
    from j0_voice_loop import run_one_turn
    from j0_voice_adapters import FakeSTTAdapter
    from j0_tts_adapters import FakeTTSAdapter

    stt = FakeSTTAdapter(["müzik çal"])
    tts = FakeTTSAdapter()

    run_one_turn(stt, tts, status_provider=_make_fake_provider("no"))

    assert len(tts.spoken) == 1
    assert len(tts.spoken[0]) > 0  # some fallback was spoken


# ---------------------------------------------------------------------------
# 8. STATIC SAFETY — no telegram/scheduler/requests/sendMessage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("token", [
    "telegram",
    "scheduler",
    "requests",
    "sendMessage",
])
def test_voice_loop_static_no_forbidden_import(token: str):
    source = _VOICE_LOOP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in getattr(node, "names", []):
                assert token not in alias.name, (
                    f"j0_voice_loop.py imports '{alias.name}' containing '{token}'"
                )
            module = getattr(node, "module", "") or ""
            assert token not in module, (
                f"j0_voice_loop.py has 'from {module} import ...' containing '{token}'"
            )


# ---------------------------------------------------------------------------
# 9 + 10. UTF-8 bytes + Mojibake guard (already covered above in CLI tests,
# adding explicit raw-bytes assertion here for completeness)
# ---------------------------------------------------------------------------


def test_cli_stdout_raw_bytes_valid_utf8():
    result = _run_voice_loop_subprocess({"JARVIS_J0_REALTIME_ENABLED": "0"})
    raw: bytes = result.stdout
    assert len(raw) > 0
    # Strict decode — raises UnicodeDecodeError on any invalid sequence
    text = raw.decode("utf-8", errors="strict")
    assert text  # non-empty


def test_cli_stdout_no_cp1254_artifacts():
    """CP1254/CP1252 corruption produces specific byte patterns — guard against them."""
    result = _run_voice_loop_subprocess({"JARVIS_J0_REALTIME_ENABLED": "0"})
    raw: bytes = result.stdout
    # Common mojibake: U+00C3 (0xC3) is the first byte of UTF-8 2-byte sequences
    # decoded as latin-1. If output contains 0xC3 as a character (not a UTF-8 lead byte)
    # that means re-encoding happened. We test via the decoded string.
    text = raw.decode("utf-8")
    for marker in _MOJIBAKE_MARKERS:
        assert marker not in text, (
            f"Mojibake marker {marker!r} (U+{ord(marker):04X}) found in output"
        )


# ---------------------------------------------------------------------------
# BLOCKER-1 FIX: Missing RealtimeSTT must fail cleanly (no traceback)
# ---------------------------------------------------------------------------


def test_real_mic_missing_realtimestt_exits_cleanly_no_traceback():
    """env=1 + --real-mic + RealtimeSTT absent => structured JSON error, no traceback."""
    code = (
        "import sys, importlib.util as _iu\n"
        "sys.path.insert(0, r'" + str(_SCRIPTS_DIR) + "')\n"
        "orig = _iu.find_spec\n"
        "def _miss(name, *a, **kw):\n"
        "    if name == 'RealtimeSTT': return None\n"
        "    return orig(name, *a, **kw)\n"
        "_iu.find_spec = _miss\n"
        "import os; os.environ['JARVIS_J0_REALTIME_ENABLED'] = '1'\n"
        "sys.argv = [sys.argv[0], '--real-mic']\n"
        "from j0_voice_loop import main\n"
        "main()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
    )
    stderr_text = result.stderr.decode("utf-8", errors="replace")
    assert "Traceback" not in stderr_text, (
        f"Unexpected Python traceback in stderr: {stderr_text[:500]}"
    )
    assert "ModuleNotFoundError" not in stderr_text, (
        f"Uncaught ModuleNotFoundError in stderr: {stderr_text[:500]}"
    )
    stdout_bytes = result.stdout
    stdout_text = stdout_bytes.decode("utf-8", errors="strict")
    assert len(stdout_text) > 0, "Expected structured JSON output; got empty stdout"
    assert "missing_dependency" in stdout_text or "error" in stdout_text, (
        f"Expected missing_dependency error in stdout: {stdout_text!r}"
    )
    assert result.returncode == 1, (
        f"Expected exit 1 for missing dep; got {result.returncode}"
    )


def test_real_mic_missing_realtimestt_stdout_is_valid_utf8():
    """Error output for missing dep must be valid strict UTF-8."""
    code = (
        "import sys, importlib.util as _iu\n"
        "sys.path.insert(0, r'" + str(_SCRIPTS_DIR) + "')\n"
        "orig = _iu.find_spec\n"
        "def _miss(name, *a, **kw):\n"
        "    if name == 'RealtimeSTT': return None\n"
        "    return orig(name, *a, **kw)\n"
        "_iu.find_spec = _miss\n"
        "import os; os.environ['JARVIS_J0_REALTIME_ENABLED'] = '1'\n"
        "sys.argv = [sys.argv[0], '--real-mic']\n"
        "from j0_voice_loop import main\n"
        "main()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
    )
    raw = result.stdout
    text = raw.decode("utf-8", errors="strict")  # strict: no invalid sequences
    for marker in _MOJIBAKE_MARKERS:
        assert marker not in text, f"Mojibake in error output: {marker!r}"


# ---------------------------------------------------------------------------
# BLOCKER-3 FIX: Turkish raw UTF-8 bytes from voice loop path
# ---------------------------------------------------------------------------


def _run_turkish_route_subprocess(turkish_input: str, turkish_summary: str) -> bytes:
    """Run route_and_respond with Turkish content in a subprocess; return raw stdout bytes.

    Removes PYTHONIOENCODING so Python uses its default (or our reconfigured) encoding.
    stdout.reconfigure(encoding='utf-8', errors='strict') is applied inside the subprocess.
    """
    code = (
        "import sys\n"
        "sys.path.insert(0, r'" + str(_SCRIPTS_DIR) + "')\n"
        "sys.stdout.reconfigure(encoding='utf-8', errors='strict')\n"
        "sys.stderr.reconfigure(encoding='utf-8', errors='replace')\n"
        "from j0_voice_loop import route_and_respond\n"
        "class S:\n"
        "    def text_summary(self): return " + repr(turkish_summary) + "\n"
        "resp = route_and_respond(" + repr(turkish_input) + ", status_provider=lambda: S())\n"
        "sys.stdout.write(resp)\n"
        "sys.stdout.flush()\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        env=env,
    )
    assert result.returncode == 0, (
        f"Turkish route subprocess failed: {result.stderr.decode('utf-8', 'replace')}"
    )
    return result.stdout


def test_turkish_route_output_is_strict_utf8():
    """route_and_respond with Turkish status summary produces strict UTF-8 bytes."""
    summary = (
        "nerede kaldık - şu an devam eden: TEST_MARKER_TR"
    )
    raw = _run_turkish_route_subprocess("nerede kaldik", summary)
    text = raw.decode("utf-8", errors="strict")
    assert "TEST_MARKER_TR" in text


def test_turkish_route_output_contains_turkish_codepoints():
    """Turkish codepoints in status summary survive the subprocess encoding stack."""
    # Summary contains: ı (U+0131), ş (U+015F), ğ (U+011F), ü (U+00FC), ç (U+00E7)
    summary = (
        "nerede kaldık - Şğışçöü - MARKER_CODEPOINTS"
    )
    raw = _run_turkish_route_subprocess("nerede kaldik", summary)
    text = raw.decode("utf-8", errors="strict")

    # Verify specific Turkish chars present
    assert "ı" in text, "dotless-i (U+0131) missing from output"
    assert "MARKER_CODEPOINTS" in text


def test_turkish_route_output_no_mojibake():
    """Turkish output from route path must not contain mojibake markers."""
    summary = "nerede kaldık - MARKER_MOJIBAKE_CHECK - şçö"
    raw = _run_turkish_route_subprocess("son commit neydi", summary)
    text = raw.decode("utf-8", errors="strict")

    extended_mojibake = ["Ã", "Ä", "Å", "â€", "Ã§", "Ä±", "�"]
    for marker in extended_mojibake:
        assert marker not in text, (
            f"Mojibake marker {marker!r} found in Turkish route output: {text!r}"
        )


def test_ascii_fold_output_via_subprocess_bytes():
    """_ascii_fold on Turkish input including U+0130 (dotted-I) produces correct ASCII bytes."""
    # Test via subprocess to verify no encoding layer mangling
    code = (
        "import sys\n"
        "sys.path.insert(0, r'" + str(_SCRIPTS_DIR) + "')\n"
        "sys.stdout.reconfigure(encoding='utf-8', errors='strict')\n"
        "from j0_voice_loop import _ascii_fold\n"
        "result = _ascii_fold('İŞĞÜÖÇ')\n"  # I S G U O C
        "sys.stdout.write(result)\n"
        "sys.stdout.flush()\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONIOENCODING"}
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, env=env)
    assert result.returncode == 0
    raw = result.stdout
    text = raw.decode("utf-8", errors="strict")
    # After folding: I(U+0130)->i, S(U+015E)->s, G(U+011E)->g, U(U+00DC)->u, O(U+00D6)->o, C(U+00C7)->c
    assert text == "isguoc", f"Expected 'isguoc'; got {text!r}"
