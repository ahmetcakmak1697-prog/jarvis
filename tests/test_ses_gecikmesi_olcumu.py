"""B12 -- ses hatti gecikme olcumu dogru dilimliyor mu?

Olcum betiginin KENDISI test edilir; gercek mikrofon ya da model gerekmez.
Donanima bagli parca (`dinle`, `sor`, `seslendir`) enjekte edilebilir --
`run_turkish_quality.py`'nin ayrimiyla ayni desen.

Neden onemli: PUSULA'nin ucuncu sarti (~1,5 saniye) hic olculmedi ve
mevcut `prompt_eval_ms` alani onun yerine gecemez -- o yalniz Ollama'nin
prompt degerlendirme suresi, STT ve sentez hic gorunmuyor. Yanlis dilimleyen
bir olcum, olcumsuzlukten daha kotudur: yanlis bir sayiya guvenilir.
"""
from __future__ import annotations

import time


def _gecikmeli(sn: float, doner=None):
    def _f(*_a, **_k):
        time.sleep(sn)
        return doner
    return _f


def test_dilimler_dogru_atfediliyor():
    """Her gecikme kendi diliminde gorunmeli, komsusunda degil."""
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    t = olc_tek_tur(
        soru="nerede kaldik",
        dinle=_gecikmeli(0.05, "nerede kaldik"),
        sor=_gecikmeli(0.10, "burada kaldik efendim"),
        seslendir=_gecikmeli(0.03),
    )

    assert 30 <= t["stt_ms"] < 90, f"STT dilimi yanlis: {t['stt_ms']}"
    assert 80 <= t["model_ms"] < 160, f"model dilimi yanlis: {t['model_ms']}"
    assert 15 <= t["ses_ms"] < 70, f"ses dilimi yanlis: {t['ses_ms']}"
    assert t["toplam_ms"] >= t["stt_ms"] + t["model_ms"] + t["ses_ms"] - 5


def test_kuru_modda_stt_sifir_sayilir():
    """Mikrofon yoksa STT dilimi uydurulmaz, sifir kalir."""
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    t = olc_tek_tur("soru", None, _gecikmeli(0.05, "cevap"), lambda _s: None)
    assert t["stt_ms"] == 0.0, "olculmeyen dilim uydurulmus"
    assert t["soru"] == "soru"


def test_ozet_p50_p95_uretir():
    from scripts.olc_ses_gecikmesi import ozetle

    turlar = [{"stt_ms": 100.0, "model_ms": 500.0, "ses_ms": 200.0,
               "toplam_ms": float(x)} for x in (800, 900, 1000, 1100, 5000)]
    o = ozetle(turlar)

    assert o["tur"] == 5
    assert o["toplam_ms"]["p50"] == 1000.0
    assert o["toplam_ms"]["max"] == 5000.0
    assert o["toplam_ms"]["p95"] > o["toplam_ms"]["p50"], (
        "p95 p50'den buyuk olmali -- yoksa dagilim goruncmez"
    )


def test_hedef_karari_p50_ve_p95_icin_AYRI_verilir():
    """Tek bir "gecti/kaldi" yok; hangi istatistigin sinir oldugu Ahmet'in."""
    from scripts.olc_ses_gecikmesi import HEDEF_MS, ozetle

    turlar = [{"toplam_ms": v} for v in (900.0, 950.0, 1000.0, 1050.0, 4000.0)]
    o = ozetle(turlar)

    assert o["hedef_ms"] == HEDEF_MS
    assert o["p50_hedefte_mi"] is True, "p50 hedefin altinda olmali"
    assert o["p95_hedefte_mi"] is False, "p95 hedefin ustunde olmali"


def test_bos_kosu_patlamaz():
    from scripts.olc_ses_gecikmesi import ozetle

    assert ozetle([])["tur"] == 0
