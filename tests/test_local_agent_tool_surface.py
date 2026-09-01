"""LocalJarvisAgent arac yuzeyi — yuklenen her arac ULASILABILIR olmali.

SkillSpector taramasi `tools/tools.py:482`'de bir `exec()` buldu
(`run_python_code`). Ilk degerlendirmem yanlisti: "kullanici cumlesinden
tetiklenebilir" demistim. Dogrulandi ki HAYIR -- `_detect_tool()` yalnizca
TOOL_TRIGGERS'ta karsiligi olan 6 araca yol aciyor.

Gercek bulgu bu yuzden farkli: `run_python_code` ajanin arac sozluguna
YUKLENIYOR ama hicbir yoldan ULASILAMIYOR. Bu bir "olu yuzey" -- risk
tasiyor ama deger uretmiyor. Yuklenmeyen kod calistirilamaz.

`tools/tools.py` DEGISTIRILMEDI (CLAUDE.md 3: onceden var olan koda
dokunulmaz). Yalnizca ajanin yukledigi sozlukten cikarildi.
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def araclar():
    from agent.local_agent import LocalJarvisAgent

    return LocalJarvisAgent.__new__(LocalJarvisAgent)._load_tools()


def test_run_python_code_is_not_loaded(araclar):
    """exec() tabanli arac ajana yuklenmez: ulasilamayan yuzey tasinmaz."""
    assert "run_python_code" not in araclar, (
        "run_python_code hicbir TOOL_TRIGGERS girdisine bagli degil; "
        "yuklenmesi yalnizca olu risk yuzeyi ekler"
    )


def test_reachable_tools_are_still_loaded(araclar):
    """Cumleden ulasilabilen her arac yuklu KALMALI (asiri duzeltme kontrolu)."""
    from agent.local_agent import TOOL_TRIGGERS

    for ad in TOOL_TRIGGERS:
        assert ad in araclar, f"{ad} tetiklenebiliyor ama yuklu degil"


def test_no_loaded_tool_is_unreachable(araclar):
    """Genel kural: yuklenen her arac ya tetiklenebilir ya da bilinen istisna.

    `analyze_file` de su an ulasilamiyor ama exec/eval icermiyor ve bu
    turda KAPSAM DISI birakildi (bkz. AHMET_ONAYI_BEKLEYENLER A5).
    Listeye yeni bir isim eklemek bilincli bir karar olmali.
    """
    from agent.local_agent import TOOL_TRIGGERS

    BILINEN_ULASILAMAZ = {"analyze_file"}
    ulasilamaz = set(araclar) - set(TOOL_TRIGGERS) - BILINEN_ULASILAMAZ
    assert not ulasilamaz, (
        f"su araclar yuklu ama hicbir cumleyle tetiklenemiyor: {ulasilamaz}"
    )


def test_tools_py_still_exports_run_python_code():
    """Kaynak modul DEGISMEDI -- yalnizca ajanin sozlugu daraldi."""
    from tools.tools import run_python_code

    assert callable(run_python_code)
