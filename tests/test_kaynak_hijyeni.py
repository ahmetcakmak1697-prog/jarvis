"""K3 -- Python kaynak dosyasi BOM tasimaz.

`docs/JARVIS_ENVANTER.md` §I "Ayristirilamayan dosyalar" uc dosya
sayiyor; olculdu (2026-09-08) ve dogrulandi:

    agents/api_executor.py    ilk 3 bayt EF BB BF
    tests/conftest.py         ilk 3 bayt EF BB BF
    tests/test_api_executor.py ilk 3 bayt EF BB BF

Ucunde de `ast.parse` "invalid non-printable character U+FEFF" ile
dusuyor. 324 `.py` dosyasi tarandi; BOM disinda ayristirma hatasi YOK.

Neden onemli: Python dosyasi BOM tasimaz. Yorumlayici `utf-8-sig` ile
okudugu icin dosyalar CALISIYOR, ama kaynagi metin olarak okuyup
`ast.parse` eden her arac onlari goremiyor -- envanter, gelecek her
statik denetim, ve `graphify`. Ozellikle `tests/conftest.py` suitin TEK
izolasyon garantisidir (`FAILURES.md` -> "Test State Pollution &
Isolation"); denetim araclarinin tam orada kor noktasi vardi.

`CLAUDE.md` §5 bu tuzagin adini koymus: "PowerShell paste Turkce
karakteri bozar (s->?, i->?) + BOM ekler."

KAPSAM: `agents/api_executor.py` bu turda DUZELTILMEDI -- Codex su an
`agents/` icinde (B10). Kusur silinmedi, GORUNUR birakildi: strict
xfail, duzeltildigi an kirmizi yanar ve isaret kaldirilir.
"""
from __future__ import annotations

import ast
import os
import warnings
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent

#: Taramaya girmeyen dizinler -- ucuncu parti kod ve uretilmis ciktilar.
_ATLANAN = {
    ".venv", "venv", "__pycache__", "node_modules", ".git",
    "graphify-out", ".pytest_cache", "build", "dist",
}

#: Codex'in alaninda oldugu icin bu turda dokunulmayan dosya (K3).
#: Codex bitirdiginde bu kume BOSALIR.
_CODEX_TE_BEKLEYEN = {"agents/api_executor.py"}

_BOM = b"\xef\xbb\xbf"


def _python_dosyalari():
    for dizin, altlar, dosyalar in os.walk(KOK):
        altlar[:] = [a for a in altlar if a not in _ATLANAN]
        for ad in dosyalar:
            if ad.endswith(".py"):
                yol = Path(dizin) / ad
                yield yol, yol.relative_to(KOK).as_posix()


# ─── 1. Adi konmus uc dosya ─────────────────────────────


@pytest.mark.parametrize("goreli", [
    "tests/conftest.py",
    "tests/test_api_executor.py",
    pytest.param(
        "agents/api_executor.py",
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "CODEX'TE -- B10 su an agents/ icinde calisiyor; bu turda "
                "dokunulmadi (KART_IMZASIZ_KUYRUK.md sinirlari). Kusur "
                "silinmedi, gorunur birakildi: BOM kaldirildigi an bu "
                "xfail kirmizi yanar ve isaret kaldirilir."
            ),
        ),
    ),
])
def test_bilinen_dosyalar_bom_tasimaz(goreli):
    """Envanterin ayristiramadigi uc dosya."""
    ham = (KOK / goreli).read_bytes()

    assert not ham.startswith(_BOM), (
        f"{goreli} BOM (U+FEFF) tasiyor -- Python dosyasi BOM tasimaz"
    )


# ─── 2. Depo geneli: yeni BOM eklenmesin ────────────────


def test_depoda_baska_BOM_tasiyan_dosya_yok():
    """Yeni bir BOM'lu dosya sessizce eklenemesin."""
    bulunan = {
        goreli for yol, goreli in _python_dosyalari()
        if yol.read_bytes().startswith(_BOM)
    }

    assert bulunan <= _CODEX_TE_BEKLEYEN, (
        f"beklenmeyen BOM'lu dosya(lar): {sorted(bulunan - _CODEX_TE_BEKLEYEN)}"
    )


def test_her_python_dosyasi_ast_ile_ayristirilabilir():
    """Denetim araclarinin kor noktasi kalmasin.

    Dosyanin calismasi yetmez: kaynagi metin olarak okuyup `ast.parse`
    eden araclar (envanter, graphify, gelecek denetimler) onu
    GOREBILMELI.
    """
    dusenler: list[str] = []
    for yol, goreli in _python_dosyalari():
        if goreli in _CODEX_TE_BEKLEYEN:
            continue
        try:
            # Uyari susturuluyor cunku bu test AYRISTIRILABILIRLIGI olcer,
            # kaynak kalitesini degil. Susturulmazsa suitin uyari ozetine
            # baskasinin borcu benim testim uzerinden dusuyor:
            # `scripts/j0_mic_check.py` gecersiz kacis dizisi '\.' tasiyor
            # (olculdu 2026-09-08, ayri madde -- bkz. IMZASIZ_IS_KUYRUGU).
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                ast.parse(yol.read_bytes().decode("utf-8"))
        except (SyntaxError, UnicodeDecodeError) as exc:
            dusenler.append(f"{goreli}: {exc}")

    assert not dusenler, "ayristirilamayan dosyalar:\n" + "\n".join(dusenler)


# ─── 3. Istisna listesi kendiliginden buyumesin ─────────


def test_bekleyen_listesi_bilincli_kalir():
    """Listeye yeni ad eklemek bilincli bir karar olmali."""
    assert _CODEX_TE_BEKLEYEN == {"agents/api_executor.py"}, (
        "bekleyen listesi degistirildi -- neden degistigi commit "
        "mesajinda yazili olmali"
    )
