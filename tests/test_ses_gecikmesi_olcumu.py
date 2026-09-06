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

    assert 30 <= t["girdi_ms"] < 90, f"girdi dilimi yanlis: {t['girdi_ms']}"
    assert 80 <= t["model_ms"] < 160, f"model dilimi yanlis: {t['model_ms']}"
    assert 15 <= t["sentez_ve_oynatma_ms"] < 70, (
        f"ses dilimi yanlis: {t['sentez_ve_oynatma_ms']}"
    )
    assert t["tur_ms"] >= (
        t["girdi_ms"] + t["model_ms"] + t["sentez_ve_oynatma_ms"] - 5
    )


def test_kuru_modda_girdi_dilimi_sifir_sayilir():
    """Mikrofon yoksa girdi dilimi uydurulmaz, sifir kalir."""
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    t = olc_tek_tur("soru", None, _gecikmeli(0.05, "cevap"), lambda _s: None)
    assert t["girdi_ms"] == 0.0, "olculmeyen dilim uydurulmus"
    assert t["soru"] == "soru"


def test_ozet_p50_p95_uretir():
    from scripts.olc_ses_gecikmesi import ozetle

    turlar = [{"girdi_ms": 100.0, "model_ms": 500.0,
               "sentez_ve_oynatma_ms": 200.0, "tur_ms": float(x)}
              for x in (800, 900, 1000, 1100, 5000)]
    o = ozetle(turlar)

    assert o["tur"] == 5
    assert o["tur_ms"]["p50"] == 1000.0
    assert o["tur_ms"]["max"] == 5000.0
    assert o["tur_ms"]["p95"] > o["tur_ms"]["p50"], (
        "p95 p50'den buyuk olmali -- yoksa dagilim goruncmez"
    )


def test_hedef_karari_p50_ve_p95_icin_AYRI_verilir():
    """Tek bir "gecti/kaldi" yok; hangi istatistigin sinir oldugu Ahmet'in."""
    from scripts.olc_ses_gecikmesi import HEDEF_MS, ozetle

    turlar = [{"tur_ms": v} for v in (900.0, 950.0, 1000.0, 1050.0, 4000.0)]
    o = ozetle(turlar)

    assert o["hedef_ms"] == HEDEF_MS
    assert o["p50_hukum"] == "HEDEFTE", "p50 ust siniri hedefin altinda"
    assert o["p95_hukum"] == "BELIRSIZ", "p95 ust siniri asildi -- hukum yok"


def test_bos_kosu_patlamaz():
    from scripts.olc_ses_gecikmesi import ozetle

    assert ozetle([])["tur"] == 0


# --------------------------------------------------------------------------- #
# A-02 -- olculen aralik PUSULA araligi DEGIL; etiketler bunu soylemeli
# --------------------------------------------------------------------------- #
#
# Codex'in deterministik senaryosu: gercek aralik 700 ms, betigin olctugu
# 7200 ms -- on kat. Saat `dinle()` oncesinde basliyor (mikrofon beklemesi,
# kullanicinin konusmasi ve STT dahil) ve `say()` DONUNCE aliniyor
# (varsayilan oynatici sesin bitmesini bekliyor).
#
# Gercek sinirlar mevcut arayuzlerle olculemiyor: `STTResult` VAD
# konusma-sonu anini vermiyor, `TTSResult.first_audio_hint_ms` ise kendi
# uyarisinda "synthesis time only ... playback start is not measured" diyor.
# Ikisi de bu kartin dosya kumesi disinda. B11'in dersi geregi ETIKET
# gercege indiriliyor: yanlis etiketli bir olcum, dogru bir olcum gibi
# karar verdirir.

def test_alan_adlari_olctukleri_seyi_soyler():
    """`stt_ms` STT'yi olcmuyordu, `toplam_ms` PUSULA araligi degildi."""
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    t = olc_tek_tur(
        soru="nerede kaldik",
        dinle=_gecikmeli(0.05, "nerede kaldik"),
        sor=_gecikmeli(0.10, "burada kaldik efendim"),
        seslendir=_gecikmeli(0.03),
    )

    assert {"girdi_ms", "model_ms", "sentez_ve_oynatma_ms", "tur_ms"} <= set(t)
    assert "stt_ms" not in t, "STT dilimi olculmuyor; bu ad fazla iddiali"
    assert "toplam_ms" not in t, "olculen sey PUSULA toplami degil, tur suresi"


def test_ozet_pusula_araliginin_olculmedigini_ACIKCA_yazar():
    """Olculemeyen sey uydurulmaz, ADIYLA yazilir."""
    from scripts.olc_ses_gecikmesi import ozetle

    o = ozetle([{"tur_ms": 900.0}])

    assert o["pusula_araligi_olculdu"] is False
    metin = o["olculmeyen_sinirlar"]
    assert "VAD" in metin and "ilk ses" in metin, (
        f"hangi sinirlarin olculmedigi yazilmamis: {metin!r}"
    )


def test_hedef_hukmu_UST_SINIR_olarak_verilir():
    """Tur suresi PUSULA araliginin ust siniridir; asimi hedef disi KANITI degil.

    Olculen aralik gercek araligi kapsar: altinda kalmak PUSULA'nin
    saglandigini KANITLAR, ustune cikmak hicbir sey kanitlamaz.
    """
    from scripts.olc_ses_gecikmesi import ozetle

    alt = ozetle([{"tur_ms": v} for v in (900.0, 950.0, 1000.0, 1050.0, 1100.0)])
    assert alt["p50_hukum"] == "HEDEFTE"

    ust = ozetle([{"tur_ms": v} for v in (4000.0, 4100.0, 4200.0, 4300.0, 4400.0)])
    assert ust["p50_hukum"] == "BELIRSIZ", (
        "ust sinirin asilmasi 'hedef disi' demek degildir -- gercek aralik "
        "olculmuyor"
    )
