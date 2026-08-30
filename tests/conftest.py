"""Governance test import bridge + test izolasyonu.

This file lives under tests/ and adds the repo scripts/ directory to sys.path.

Ayrica testler arasi durum sizintisini (test pollution) kapatir. Iki gercek
sizinti sinifi vardi ve ikisi de burada engellenir:

1. **Belirsiz modul adi (`import orchestrator`).** Repoda ayni ada sahip iki
   modul var: `scripts/orchestrator.py` ve `agents/orchestrator.py`.
   `tests/test_blackbox_log.py` modul duzeyinde `agents/` dizinini
   `sys.path[0]`'a sokuyor; alfabetik olarak sonra toplanan
   `tests/test_orchestrator.py` ve `tests/test_contractpath_schema_alignment.py`
   ise `import orchestrator` ile *scripts* surumunu bekliyor. Sonuc: yanlis
   modul baglaniyor ve `AttributeError: module 'orchestrator' has no attribute
   '_read_verdict'` gibi hatalar cikiyor. Hasar **toplama (collection)**
   aninda olustugu icin bir fixture cok gec kalir; bu yuzden
   `pytest_collectstart` kancasi kullaniliyor.

2. **Opsiyonel ses kutuphanelerinin sizmasi.** `scripts/j0_spike_b_latency_probe.py`
   calisma aninda `sounddevice` import ediyor; modul `sys.modules`'te kaliyor.
   `tests/test_j0_voice_adapters.py` ve `tests/test_j0_voice_loop.py` ise
   "voice adapter'i import etmek agir ses kutuphanelerini yuklememeli" seklinde
   *import guvenligi* iddia ediyor ve kirli `sys.modules` yuzunden coeuyor.

Hicbir test dosyasi degistirilmedi; izolasyon tek noktadan, burada saglanir.
"""
from pathlib import Path
import sys

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


# --------------------------------------------------------------------------- #
# 1) Belirsiz (birden fazla dizinde ayni ada sahip) modul adlari
# --------------------------------------------------------------------------- #

#: Testlerin `sys.path`'e soktugu dizinler. Bir modul adi bunlardan birden
#: fazlasinda geciyorsa `import <ad>` sonucu sys.path sirasina baglidir —
#: yani sizintiya aciktir.
_IMPORTABLE_DIRS = (
    _REPO_ROOT,
    _SCRIPTS,
    _REPO_ROOT / "agents",
    _REPO_ROOT / "tools",
)


def _find_ambiguous_module_names() -> frozenset[str]:
    """Birden fazla enjekte edilebilir dizinde bulunan modul adlarini bulur.

    Sabit liste yerine hesaplanir: repoya yeni bir cakisma eklendiginde bu
    koruma kendiliginden kapsar.
    """
    first_seen: dict[str, Path] = {}
    duplicates: set[str] = set()
    for directory in _IMPORTABLE_DIRS:
        if not directory.is_dir():
            continue
        for path in directory.glob("*.py"):
            name = path.stem
            if name == "__init__":
                continue
            if name in first_seen:
                duplicates.add(name)
            else:
                first_seen[name] = directory
    return frozenset(duplicates)


_AMBIGUOUS_MODULE_NAMES = _find_ambiguous_module_names()


def _prioritise_scripts_dir() -> None:
    """`scripts/` dizinini `agents/` ve `tools/`'un onunde tutar.

    `agents/` dizinini sys.path'ten **cikarmaz** — `test_blackbox_log.py` ona
    ihtiyac duyuyor. Yalnizca belirsiz adlarda `scripts/` surumunun kazanmasini
    garanti eder; bugun bare `import orchestrator` yazan iki test de scripts
    surumunu bekliyor.
    """
    scripts = str(_SCRIPTS)
    if scripts in sys.path:
        sys.path.remove(scripts)
    sys.path.insert(0, scripts)


def pytest_collectstart(collector) -> None:
    """Her toplama adiminda import onceligini ve modul onbellegini sifirlar.

    Modul duzeyi `import orchestrator` toplama aninda calistigi icin bu
    temizlik fixture'da degil, burada yapilmak zorunda.
    """
    del collector  # kanca imzasi geregi; karar collector'a bagli degil
    _prioritise_scripts_dir()
    for name in _AMBIGUOUS_MODULE_NAMES:
        sys.modules.pop(name, None)


# --------------------------------------------------------------------------- #
# 2) Test basina durum izolasyonu
# --------------------------------------------------------------------------- #

#: Import-guvenligi testlerinin "yuklenmemis olmali" diye iddia ettigi agir
#: opsiyonel ses kutuphaneleri. Bunlar bir testten digerine sizmamali.
_AUDIO_GUARD_MODULES = ("RealtimeSTT", "sounddevice", "pyaudio", "openwakeword")


def _purge_audio_modules() -> None:
    for name in list(sys.modules):
        for guard in _AUDIO_GUARD_MODULES:
            if name == guard or name.startswith(guard + "."):
                del sys.modules[name]
                break


@pytest.fixture(autouse=True)
def _isolate_module_state():
    """Her testi temiz `sys.path` ve temiz ses-modulu durumuyla baslatir.

    Hem kurulumda hem sokumde temizlik yapilir; boylece koruma test sirasindan
    **bagimsiz** olur — sizdiran testin once mi sonra mi kostugu onemli degil.
    """
    saved_path = list(sys.path)
    _purge_audio_modules()
    try:
        yield
    finally:
        sys.path[:] = saved_path
        _purge_audio_modules()
        for name in _AMBIGUOUS_MODULE_NAMES:
            sys.modules.pop(name, None)
