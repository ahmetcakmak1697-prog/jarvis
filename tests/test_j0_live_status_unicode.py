"""
tests/test_j0_live_status_unicode.py — Unicode/mojibake regression tests for j0_live_status.

Regression guard against:
- stdout encoding defaulting to cp1252/cp1254 (Windows pipe encoding)
- ensure_ascii=True stripping Turkish chars in JSON/text output
- accidental encode/decode roundtrips producing mojibake
- ASCII-degraded labels (TEMIZ instead of TEMİZ, Calisma instead of Çalışma)

These tests would have caught the original bug (test_cli_utf8_subprocess asserting
'Sıra' which only appears with TODO roadmap steps, masking the real check).

Two sections:
  1. Subprocess (real CLI, real roadmap): tests always-present strings
  2. Unit (injected data): tests chars that appear only in specific sections
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from j0_live_status import _REPO_ROOT, _default_git_runner, collect_status


# ---------------------------------------------------------------------------
# Subprocess fixture — real CLI output captured once per session
# ---------------------------------------------------------------------------

def _run_cli_raw() -> tuple[bytes, int]:
    spath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "j0_live_status.py")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, spath],
        capture_output=True,
        text=False,
        env=env,
    )
    return result.stdout, result.returncode


@pytest.fixture(scope="module")
def cli_text() -> str:
    raw, code = _run_cli_raw()
    assert code == 0, f"j0_live_status CLI exited with code {code}"
    return raw.decode("utf-8")  # strict by default — raises if not valid UTF-8


# ---------------------------------------------------------------------------
# Subprocess tests: always-present assertions regardless of roadmap state
# ---------------------------------------------------------------------------

def test_cli_exits_zero():
    _, code = _run_cli_raw()
    assert code == 0


def test_cli_stdout_is_valid_utf8():
    raw, _ = _run_cli_raw()
    raw.decode("utf-8")  # strict — raises UnicodeDecodeError if bytes not valid UTF-8


def test_cli_no_utf8_replacement_chars(cli_text):
    assert "�" not in cli_text, "U+FFFD replacement char in output — stdout encoding broken"


def test_cli_calisma_agaci_present(cli_text):
    # "Çalışma ağacı" always emitted by _ensure_summary()
    # covers: Ç (U+00C7), ı (U+0131), ş (U+015F), ğ (U+011F)
    assert "Çalışma ağacı" in cli_text


def test_cli_c_cedilla_present(cli_text):
    assert "Ç" in cli_text, "Ç (U+00C7) missing from CLI output"


def test_cli_dotless_i_present_via_footer(cli_text):
    # "kaldık" is in the footer: ('nerede kaldık' ...) — always present
    assert "kaldık" in cli_text, "'kaldık' missing — ı (U+0131) not in footer"


def test_cli_c_cedilla_lowercase_present_via_footer(cli_text):
    # "araçtır" is in the footer — always present; covers ç (U+00E7)
    assert "araçtır" in cli_text, "'araçtır' missing — ç (U+00E7) not in footer"


def test_cli_i_with_dot_present(cli_text):
    # İ (U+0130) appears in TEMİZ or KİRLİ — always emitted
    assert ("TEMİZ" in cli_text) or ("KİRLİ" in cli_text), "İ (U+0130) missing from CLI output"


def test_cli_g_breve_present(cli_text):
    # ğ appears in "ağacı" — always in "Çalışma ağacı" line
    assert "ğ" in cli_text, "ğ (U+011F) missing from CLI output"


def test_cli_s_cedilla_present(cli_text):
    # ş appears in "Çalışma" — always present
    assert "ş" in cli_text, "ş (U+015F) missing from CLI output"


# ---------------------------------------------------------------------------
# Subprocess tests: no mojibake
# ---------------------------------------------------------------------------

def test_cli_no_mojibake_a_tilde(cli_text):
    # "Ã" appears when UTF-8 Ç (0xC3 0x87) is decoded as cp1252 → Ã‡
    assert "Ã" not in cli_text, "Mojibake 'Ã' found — UTF-8 bytes read as cp1252"


def test_cli_no_mojibake_a_umlaut(cli_text):
    # "Ä" appears when UTF-8 ı (0xC4 0xB1) decoded as cp1252 → Ä±
    assert "Ä" not in cli_text, "Mojibake 'Ä' found"


def test_cli_no_mojibake_a_ring(cli_text):
    assert "Å" not in cli_text, "Mojibake 'Å' found"


def test_cli_no_ascii_degraded_temiz(cli_text):
    # "TEMIZ" (without İ) would appear if İ was stripped
    # "TEMİZ" uses İ (U+0130); TEMIZ uses plain I — these are different strings
    assert "TEMIZ" not in cli_text or "TEMİZ" in cli_text, (
        "ASCII-degraded 'TEMIZ' found without 'TEMİZ' — İ was lost"
    )


def test_cli_no_ascii_degraded_calisma(cli_text):
    # "Calisma" is the ASCII-degraded form of "Çalışma"
    assert "Calisma" not in cli_text, "ASCII-degraded 'Calisma' found"


# ---------------------------------------------------------------------------
# Unit tests: Turkish chars in injected summaries (independent of real roadmap)
# ---------------------------------------------------------------------------

def _fake_git(lines: List[str], clean: bool = True):
    porcelain = "" if clean else " M x.py\n"

    def _run(args: List[str]) -> str:
        if args[0] == "log":
            return "\n".join(lines) + "\n"
        if args[0] == "status":
            return porcelain
        raise ValueError(f"unexpected: {args}")

    return _run


def _fake_roadmap(steps: List[dict]):
    def _load() -> Any:
        return {"steps": steps}

    return _load


_GIT_LOG = ["abc1234 test commit", "def5678 second"]
_FAZ3E1_STEP = {"id": "FAZ-3-E1", "title": "Proaktif davranış motoru", "status": "in_progress"}


def test_unit_u_umlaut_in_faz3e1_section():
    # ü = ü — appears in "henüz devrede değil"
    status = collect_status(_fake_git(_GIT_LOG), _fake_roadmap([_FAZ3E1_STEP]))
    assert "ü" in status.text_summary(), "ü (U+00FC) missing — 'henüz' not in FAZ-3-E1 summary"


def test_unit_o_umlaut_in_faz3e1_section():
    # ö = ö — appears in "Telegram gönderme"
    status = collect_status(_fake_git(_GIT_LOG), _fake_roadmap([_FAZ3E1_STEP]))
    assert "ö" in status.text_summary(), "ö (U+00F6) missing — 'gönderme' not in FAZ-3-E1 summary"


def test_unit_all_lowercase_turkish_special_chars():
    # When FAZ-3-E1 is in_progress all 6 lowercase special chars appear
    status = collect_status(_fake_git(_GIT_LOG), _fake_roadmap([_FAZ3E1_STEP]))
    summary = status.text_summary()
    for char, name in [
        ("ç", "ç c-cedilla"),
        ("ğ", "ğ g-breve"),
        ("ı", "ı dotless-i"),
        ("ö", "ö o-umlaut"),
        ("ş", "ş s-cedilla"),
        ("ü", "ü u-umlaut"),
    ]:
        assert char in summary, f"{name} ({char!r}) missing from summary"


def test_unit_uppercase_turkish_chars_in_summary():
    status = collect_status(_fake_git(_GIT_LOG), _fake_roadmap([_FAZ3E1_STEP]))
    summary = status.text_summary()
    for char, name in [
        ("Ç", "Ç C-cedilla"),
        ("Ş", "Ş S-cedilla"),
        ("İ", "İ I-with-dot"),
    ]:
        assert char in summary, f"{name} ({char!r}) missing from summary"


def test_unit_no_mojibake_in_summary():
    status = collect_status(_fake_git(_GIT_LOG), _fake_roadmap([_FAZ3E1_STEP]))
    summary = status.text_summary()
    for bad in ["â", "Ã", "Ä", "Å", "�"]:
        assert bad not in summary, f"Mojibake {bad!r} found in summary"


def test_unit_no_ascii_degraded_in_summary():
    status = collect_status(_fake_git(_GIT_LOG), _fake_roadmap([]))
    summary = status.text_summary()
    for bad in ["Calisma", "agaci", "TEMIZ", "KIRLI"]:
        assert bad not in summary, f"ASCII-degraded '{bad}' found in summary"


def test_unit_footer_always_contains_dotless_i_and_c_cedilla():
    # Footer line always present; contains ı and ç
    status = collect_status(_fake_git(_GIT_LOG), _fake_roadmap([]))
    summary = status.text_summary()
    assert "kaldık" in summary, "kaldık missing from footer — ı lost"
    assert "araçtır" in summary, "araçtır missing from footer — ç lost"


def test_unit_todo_step_produces_sira_bekleyen():
    # When there ARE todo steps, "Sıra bekleyen:" appears correctly
    steps = [{"id": "FAZ-X", "title": "Test", "status": "todo"}]
    status = collect_status(_fake_git(_GIT_LOG), _fake_roadmap(steps))
    summary = status.text_summary()
    assert "Sıra bekleyen:" in summary, "Sıra bekleyen: missing when todo steps exist"
    assert "FAZ-X" in summary


# ---------------------------------------------------------------------------
# Safe.directory regression — git exit 128 fix
# ---------------------------------------------------------------------------

def test_default_git_runner_includes_safe_directory_flag():
    """_default_git_runner must pass -c safe.directory=<posix_path> to avoid git exit 128.

    POSIX (forward-slash) path is required: git on Windows rejects backslash safe.directory
    values with exit 128. The old backslash form f"safe.directory={_REPO_ROOT}" was broken.
    """
    with patch("subprocess.check_output", return_value="abc1234 test\n") as mock_co:
        _default_git_runner(["log", "--oneline", "-1"])
    cmd = mock_co.call_args[0][0]
    assert cmd[0] == "git"
    assert "-c" in cmd, "git -c flag missing — safe.directory override not present"
    safe_idx = cmd.index("-c")
    safe_val = cmd[safe_idx + 1]
    assert safe_val.startswith("safe.directory="), (
        f"expected safe.directory=... after -c, got {safe_val!r}"
    )
    # Must be POSIX (forward-slash) path — backslash form causes git exit 128 on Windows
    assert "\\" not in safe_val, (
        f"backslash in safe.directory value — git will reject it: {safe_val!r}"
    )
    assert "/" in safe_val, f"no forward slash in safe.directory value: {safe_val!r}"
    assert _REPO_ROOT.as_posix() in safe_val, (
        f"expected posix path {_REPO_ROOT.as_posix()!r} in {safe_val!r}"
    )


def test_default_git_runner_exit_128_propagates():
    """Git exit 128 (permission/ownership) must propagate as CalledProcessError, not be silently lost."""
    exc = subprocess.CalledProcessError(128, ["git", "log"], output="fatal: unsafe repository")
    with patch("subprocess.check_output", side_effect=exc):
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            _default_git_runner(["log", "--oneline", "-1"])
    assert exc_info.value.returncode == 128
