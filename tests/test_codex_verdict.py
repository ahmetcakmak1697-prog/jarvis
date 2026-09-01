"""
tests/test_codex_verdict.py - codex_verdict.ps1 verdict parser tests.

WHY THIS EXISTS: Get-CodexVerdict is the gate of the autonomous loop.
PASS -> the loop continues; CONCERN/BLOCKER -> it stops and goes to Ahmet.
A misparse either fakes an approval or freezes the loop forever.

The original parser searched the raw codex output for PASS/CONCERN/BLOCKER.
That is wrong: the codex CLI echoes the prompt it was given, and the reviewer
instruction (automation/CODEX_REVIEW_TALIMATI.md) itself contains "BLOCKER"
three times. Every review therefore parsed as BLOCKER. Case 1 below is that
exact regression.

These tests invoke the REAL PowerShell function - not a Python copy of it -
so the test cannot silently drift away from the shipped logic.

Coverage:
  1.  echoed instruction + "Verdict: PASS"        -> PASS   (the regression)
  2.  bold "**Verdict: CONCERN**"                 -> CONCERN
  3.  uppercase "VERDICT: BLOCKER"                -> BLOCKER
  4.  prose mentions BLOCKER, verdict says PASS   -> PASS
  5.  no verdict line at all                      -> BELIRSIZ (never PASS)
  6.  empty output                                -> BELIRSIZ
  7.  two verdict lines -> the last one wins
  8.  markdown list form "- verdict = CONCERN"    -> CONCERN
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FUNC_PS1 = _REPO_ROOT / "scripts" / "codex_verdict.ps1"
_TALIMAT = _REPO_ROOT / "automation" / "CODEX_REVIEW_TALIMATI.md"

_POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")

pytestmark = pytest.mark.skipif(
    _POWERSHELL is None,
    reason="PowerShell not available; codex_verdict.ps1 cannot be exercised",
)


def _cagir(cikti: str, yankilanan: str) -> str:
    """Call the real Get-CodexVerdict and return its answer."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cikti_dosya = tmp_path / "cikti.txt"
        talimat_dosya = tmp_path / "talimat.txt"
        cikti_dosya.write_text(cikti, encoding="utf-8")
        talimat_dosya.write_text(yankilanan, encoding="utf-8")

        komut = (
            f". '{_FUNC_PS1}'; "
            f"$c = [IO.File]::ReadAllText('{cikti_dosya}'); "
            f"$t = [IO.File]::ReadAllText('{talimat_dosya}'); "
            "Write-Output (Get-CodexVerdict -Cikti $c -YankilananTalimat $t)"
        )
        sonuc = subprocess.run(
            [_POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", komut],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert sonuc.returncode == 0, f"PowerShell failed: {sonuc.stderr}"
        return sonuc.stdout.strip()


def _sahte_codex_ciktisi(govde: str, talimat: str) -> str:
    """Reproduce how the codex CLI renders a run: header, echoed prompt, answer."""
    return (
        "OpenAI Codex v0.150.0\n"
        "--------\n"
        "workdir: /repo/jarvis-agent-auto\n"
        "--------\n"
        "user\n"
        f"{talimat}\n"
        "codex\n"
        f"{govde}\n"
        "tokens used\n"
        "12.345\n"
    )


@pytest.fixture(scope="module")
def talimat() -> str:
    """The real reviewer instruction, prefixed the way codex_denetle.ps1 does."""
    govde = _TALIMAT.read_text(encoding="utf-8")
    return "Incelenecek kapsam: calisma agacindaki commit edilmemis degisiklikler.\n\n" + govde


def test_talimat_gercekten_blocker_kelimesi_iceriyor(talimat: str) -> None:
    """The premise of the regression: the instruction itself says BLOCKER."""
    assert talimat.count("BLOCKER") >= 3
    assert talimat.count("PASS") >= 2


@pytest.mark.parametrize(
    "ad, govde, beklenen",
    [
        ("duz_pass", "Somut bir kusur bulamadim.\n\nVerdict: PASS", "PASS"),
        ("kalin_concern", "a.py:12 - sessiz hata yutuluyor.\n\n**Verdict: CONCERN**", "CONCERN"),
        ("buyuk_harf_blocker", "b.py:3 - veri kaybi.\n\nVERDICT: BLOCKER", "BLOCKER"),
        ("metinde_blocker_gecer_ama_pass", "BLOCKER seviyesinde bir sey bulamadim.\n\nVerdict: PASS", "PASS"),
        ("verdict_yok", "Bir seyler yazdim ama karar vermedim.", "BELIRSIZ"),
        ("liste_bicimi", "- verdict = CONCERN", "CONCERN"),
    ],
)
def test_verdict_cozumleme(ad: str, govde: str, beklenen: str, talimat: str) -> None:
    cikti = _sahte_codex_ciktisi(govde, talimat)
    assert _cagir(cikti, talimat) == beklenen, ad


def test_bos_cikti_belirsiz_doner(talimat: str) -> None:
    """Empty output must never be read as approval."""
    assert _cagir("", talimat) == "BELIRSIZ"


def test_son_verdict_kazanir(talimat: str) -> None:
    """A revised verdict later in the text overrides an earlier one."""
    govde = "Verdict: CONCERN\n\nDuzeltmeden sonra tekrar bakildi.\n\nVerdict: PASS"
    assert _cagir(_sahte_codex_ciktisi(govde, talimat), talimat) == "PASS"


def test_yanki_cikarilmazsa_eski_hata_geri_gelir(talimat: str) -> None:
    """
    Guard the fix itself: if the echoed instruction is NOT subtracted, the
    stray BLOCKER words in it are what the parser would land on. Passing an
    empty echo argument simulates that broken state.
    """
    cikti = _sahte_codex_ciktisi("Somut bir kusur bulamadim.\n\nVerdict: PASS", talimat)
    assert _cagir(cikti, talimat) == "PASS"      # echo subtracted -> correct
    assert _cagir(cikti, "") == "PASS"           # explicit verdict line still wins

    # ...but with no explicit verdict line AND no subtraction, the instruction's
    # own words leak through - which is precisely the bug that was shipped.
    kusurlu = _sahte_codex_ciktisi("Bir seyler yazdim ama karar vermedim.", talimat)
    assert _cagir(kusurlu, talimat) == "BELIRSIZ"
    assert _cagir(kusurlu, "") != "BELIRSIZ"
