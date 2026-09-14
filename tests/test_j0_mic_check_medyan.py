"""KART_STT_TURKCE ADIM 1 -- j0_mic_check'in medyan teshisi.

Olculdu (2026-09-14, 15 cumlelik kayit; automation/STT_TURKCE_OLCUM_2026-09-14.md):
kartin "ortalama esigin altinda" onculu bu kayitta TUTMADI -- 15 cumlenin
15'inde ortalama rms 0,0137-0,0352 (esik 0,01). Ortalama, yuksek tepeler
yuzunden esigin ustunde kalirken parcalarin cogu altinda olabilir; bir
ortalama kontrolu o durumda HIC ateslemez. Medyan ise "konusma suresinin
yarisindan fazlasi kaydediciye sessizlik gibi gorunuyor" demenin dogrudan
olcusudur.

2026-09-09 j0_mic_check olcumu: tepe 0,07968, ortalama 0,00781, esik ustu
%19 -- yani medyan esigin altindaydi. Eski teshis "UYUMLU" dedi (tepe esigi
gecti, oran %5'in ustunde); yeni dal orada uyarirdi.

Mevcut `tepe * 0.4` dali DEGISMEDI; yeni dal yalniz tepe esigi gectiginde
ve medyan esigin altindayken ateslenir.
"""
from __future__ import annotations

import statistics
import warnings

import pytest


def _modul():
    # scripts/j0_mic_check.py docstring'inde gecersiz kacis dizisi var ('\.')
    # -- K13, ayri madde. Import aninda uyari uretir; bu test onu olcmez ve
    # suitin uyari sayisini kirletmemeli.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        warnings.simplefilter("ignore", SyntaxWarning)
        import j0_mic_check
    return j0_mic_check


def test_medyan_esigin_altindaysa_tepe_gecse_bile_uyarir():
    assert _modul().medyan_teshisi(medyan=0.005, tepe=0.08, esik=0.01) == pytest.approx(0.0025)


def test_medyan_esigin_ustundeyse_uyari_yok():
    assert _modul().medyan_teshisi(medyan=0.02, tepe=0.08, esik=0.01) is None


def test_tepe_esigin_altindaysa_yeni_dal_ateslemez():
    """O durum mevcut `tepe * 0.4` dalinin isi; ayni vaka iki kez teshis edilmez."""
    assert _modul().medyan_teshisi(medyan=0.0002, tepe=0.005, esik=0.01) is None


def test_onerilen_esik_mevcut_tabanin_altina_inmez():
    """`tepe * 0.4` dalinin kullandigi 0.0005 tabani burada da gecerli."""
    assert _modul().medyan_teshisi(medyan=0.0006, tepe=0.08, esik=0.01) == 0.0005


def test_2026_09_09_olcumu_yeni_dalda_uyarirdi():
    """%19 esik ustu -> medyan esigin altinda; eski teshis 'UYUMLU' demisti."""
    seviyeler = [0.05] * 38 + [0.003] * 162      # 200 parcanin 38'i esik ustu (%19)
    assert _modul().medyan_teshisi(
        statistics.median(seviyeler), max(seviyeler), 0.01) is not None
