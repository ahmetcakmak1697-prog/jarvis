"""Aciklanamayan 2.615 ms -- canli tur kaydi neyi kaybediyordu?

`automation/TTS_ANATOMISI_2026-09-09.md` §1: sentetik olcum ilk sese kadar
577-1052 ms buldu, canli bes tur ~3.500 ms verdi ve fark **bes noktanin
hepsinde ayni yonde** (ortalama +2.615 ms). Uc aday yazildi; ikisi acik kaldi
cunku canli kayit iki seyi tasimiyordu:

1. **Cevap METNI.** Yalniz `cevap_uzunluk` kaydediliyordu. Metin olmadan o
   akssamki turlar tekrar oynatilamaz ve "gercek cevaplar Microsoft'a farkli
   bir bedel odetiyor mu" sorusu sinanamaz. Olctugu girdiyi saklamayan bir
   olcum araci, kendi sonucunu bir daha uretemez.
2. **TTS damgalari.** `sentez_ve_oynatma_ms` tek bir sayiydi; icindeki ag
   payi (`sentez_ms`) ile calinan sesin suresi (`oynatma_ms`) ayrilmiyordu.
   `EdgeTTSAdapter.speak()` bu bes damgayi 2026-09-09'dan beri uretiyor ama
   tur kaydina hic girmiyordu.

Bu dosya iki kaybi da kapatan sozlesmeyi sinar. Sozlesme degismedi:
**olculemeyen alan `None` doner, `0` degil.**
"""
from __future__ import annotations

import time
from types import SimpleNamespace


def _gecikmeli(sn: float, doner=None):
    def _f(*_a, **_k):
        time.sleep(sn)
        return doner
    return _f


def _ses_sonucu(sentez=None, kurulum=None, oynatma=None, ok=True):
    """`TTSResult` benzeri; yalniz VERILEN damgalari tasir."""
    return SimpleNamespace(
        ok=ok, engine="sahte",
        sentez_ms=sentez, oynatici_kurulum_ms=kurulum, oynatma_ms=oynatma,
    )


# --------------------------------------------------------------------------- #
# ADIM 0 -- cevap metni kayboluyordu
# --------------------------------------------------------------------------- #

def test_tur_kaydi_cevap_metnini_tasir():
    """Uzunluk yeterli degil: metin olmadan tur tekrar oynatilamaz."""
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    t = olc_tek_tur(
        soru="nerede kaldik",
        dinle=None,
        sor=lambda _m: "Burada kaldik efendim, B10 kapandi.",
        seslendir=lambda _s: None,
    )

    assert t["cevap"] == "Burada kaldik efendim, B10 kapandi."
    assert t["cevap_uzunluk"] == len("Burada kaldik efendim, B10 kapandi."), (
        "uzunluk alani KALMALI -- eski kayitlarla kiyas onun uzerinden yapiliyor"
    )


def test_bos_cevap_metni_uydurulmaz():
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    t = olc_tek_tur("soru", None, lambda _m: "", lambda _s: None)

    assert t["cevap"] == ""
    assert t["cevap_uzunluk"] == 0


# --------------------------------------------------------------------------- #
# ADIM 1 -- TTS damgalari tur kaydina gecmeli
# --------------------------------------------------------------------------- #

def test_tts_damgalari_tur_kaydina_gecer():
    """`sentez_ve_oynatma_ms` tek sayi kalmaz; ag payi ayri gorunur."""
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    t = olc_tek_tur(
        soru="nerede kaldik",
        dinle=None,
        sor=lambda _m: "Burada kaldik efendim.",
        seslendir=lambda _s: _ses_sonucu(sentez=812.4, kurulum=4.6,
                                         oynatma=2503.9),
    )

    assert t["sentez_ms"] == 812.4
    assert t["oynatici_kurulum_ms"] == 4.6
    assert t["oynatma_ms"] == 2503.9
    assert t["ses_kaniti"] is True, "TTSResult.ok=True kanit sayilmali"


def test_damga_veremeyen_seslendirici_None_birakir():
    """Eski `seslendir` sozlesmesi (bool/None doner) bozulmaz, uydurulmaz."""
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    t = olc_tek_tur("soru", None, lambda _m: "cevap", lambda _s: True)

    assert t["ses_kaniti"] is True
    for alan in ("sentez_ms", "oynatici_kurulum_ms", "oynatma_ms"):
        assert t[alan] is None, f"{alan} uydurulmus: {t[alan]!r}"
        assert t[alan] != 0


def test_kismi_damga_sadece_olculeni_yazar():
    """Oynatici baslangicini bildiremediyse yalniz o alan `None` kalir."""
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    t = olc_tek_tur(
        "soru", None, lambda _m: "cevap",
        lambda _s: _ses_sonucu(sentez=640.0, kurulum=None, oynatma=None),
    )

    assert t["sentez_ms"] == 640.0
    assert t["oynatici_kurulum_ms"] is None
    assert t["oynatma_ms"] is None


def test_basarisiz_ses_sonucu_kanit_sayilmaz():
    """`ok=False` bir TTSResult ses kaniti DEGILDIR (A-01)."""
    import pytest

    from scripts.olc_ses_gecikmesi import OlcumBasarisiz, olc_tek_tur

    with pytest.raises(OlcumBasarisiz):
        olc_tek_tur(
            "soru", None, lambda _m: "cevap",
            lambda _s: _ses_sonucu(sentez=None, ok=False),
            ses_bekleniyor=True,
        )


def test_tts_damgalari_dilim_suresini_asmaz():
    """Adapter'in bildirdigi sureler, betigin olctugu duvara sigar.

    Sigmiyorsa ya birim cevrimi yanlistir ya da damgalar baska bir turdan
    gelmistir -- ikisi de sessizce yanlis bir rapor uretir.
    """
    from scripts.olc_ses_gecikmesi import olc_tek_tur

    def _seslendir(_s):
        time.sleep(0.12)
        return _ses_sonucu(sentez=40.0, kurulum=5.0, oynatma=60.0)

    t = olc_tek_tur("soru", None, lambda _m: "cevap", _seslendir)

    bildirilen = t["sentez_ms"] + t["oynatici_kurulum_ms"] + t["oynatma_ms"]
    assert bildirilen <= t["sentez_ve_oynatma_ms"], (
        f"bildirilen {bildirilen} ms > olculen dilim "
        f"{t['sentez_ve_oynatma_ms']} ms"
    )


# --------------------------------------------------------------------------- #
# Ozet yeni alanlari da tasimali
# --------------------------------------------------------------------------- #

def test_ozet_tts_dilimlerinin_dagilimini_verir():
    from scripts.olc_ses_gecikmesi import ozetle

    turlar = [{"tur_ms": 5000.0, "sentez_ms": float(v), "oynatma_ms": 2000.0}
              for v in (600, 700, 800, 900, 3000)]
    o = ozetle(turlar)

    assert o["sentez_ms"]["p50"] == 800.0
    assert o["sentez_ms"]["max"] == 3000.0
    assert o["oynatma_ms"]["p50"] == 2000.0


def test_ozet_olculmemis_dilimi_ortalamaya_katmaz():
    from scripts.olc_ses_gecikmesi import ozetle

    o = ozetle([{"tur_ms": 100.0, "sentez_ms": None},
                {"tur_ms": 200.0, "sentez_ms": 640.0}])

    assert o["sentez_ms"]["ort"] == 640.0, (
        "olculmemis tur ortalamaya 0 olarak girmis"
    )


# --------------------------------------------------------------------------- #
# ADIM 1 -- kuru mod TTS'i KOSTURABILMELI (kartin varsaydigi sey bugun YOK)
# --------------------------------------------------------------------------- #

def test_kuru_modda_ses_cikisi_secenegi_vardir():
    """`--kuru` bugun TTS'i HIC calistirmiyor; STT'siz TTS icin ayri kapi sart.

    Kart "--kuru modu STT'yi atlar ama model + TTS'i gercekten calistirir"
    diyor. Kaynak bunu soylemiyordu: kuru modda `seslendir` sabit `False`
    donen bir no-op'tu. Yani o varsayimla alinacak her olcum, TTS'i hic
    olcmeden "olctum" derdi.
    """
    import argparse
    import inspect

    from scripts import olc_ses_gecikmesi as m

    kaynak = inspect.getsource(m.main)
    assert "--ses-cikisi" in kaynak, (
        "kuru modda TTS kosturan acik bir secenek yok"
    )

    ap = argparse.ArgumentParser()
    for ad, kw in (("--kuru", {"action": "store_true"}),
                   ("--ses-cikisi", {"action": "store_true"})):
        ap.add_argument(ad, **kw)
    a = ap.parse_args(["--kuru", "--ses-cikisi"])
    assert a.kuru is True and a.ses_cikisi is True
