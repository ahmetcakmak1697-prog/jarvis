"""3.468 ms'nin ICI -- sentez mi, ag mi, oynatici mi?

`automation/SES_HATTI_COZUMLEME_2026-09-09.md` bes noktali bir regresyondan
`sentez_ve_oynatma_ms = 3.468 + 72,2 x karakter` cikardi. Kesisim **dogrudan
gozlenmedi**; bir cikarimdir. Bugunun dersi tam olarak buydu (FAILURES.md,
2026-09-09): cikarimi olcum gibi sunmak.

Bu dosya kesisimi olcume cevirecek olay damgalarini sinar. `speak()` bes an
kaydeder ve uc tureyen dilim uretir:

    sentez_ms            = t_ses_hazir      - t_istek
    oynatici_kurulum_ms  = t_oynatma_basladi - t_ses_hazir
    oynatma_ms           = t_bitti          - t_oynatma_basladi

Iki sozlesme korunur:

* **Olculemeyen alan `None` doner, `0` degil.** Oynatici kapaliysa
  `oynatma_ms` sifir SURMEDI, hic OLMADI.
* **Mevcut `first_audio_hint_ms` silinmez.** Kendi uyarisinda "synthesis time
  only ... playback start is not measured" diyor ve bu dogruydu; yanina
  gercegi konur, yerine gecilmez.

Ag yok, ses cihazi yok: sentez ve oynatici enjekte edilir.
"""
from __future__ import annotations

import time


def _gecikmeli(sn: float, doner=None):
    def _f(*_a, **_k):
        time.sleep(sn)
        return doner
    return _f


def _oynatici(kurulum_sn: float, oynatma_sn: float):
    """`on_playback_start`'i DESTEKLEYEN sahte oynatici.

    Gercek oynatici da boyle davranir: once kurulum (mixer.init + load),
    sonra calmaya baslar ve bunu haber verir, sonra sesin bitmesini bekler.
    """
    def _f(_path, on_playback_start=None):
        time.sleep(kurulum_sn)
        if on_playback_start is not None:
            on_playback_start()
        time.sleep(oynatma_sn)
    return _f


def _konus(**kw):
    """Enjekte edilmis uclarla tek bir `speak()`; test yalniz ilgilendigini verir."""
    from j0_tts_adapters import EdgeTTSAdapter

    varsayilan = {
        "synth": lambda _metin, _ses: "C:/tmp/olcum.mp3",
        "player": _oynatici(0.0, 0.0),
        "enabled": True,
    }
    metin = kw.pop("metin", "Merhaba efendim")
    varsayilan.update(kw)
    return EdgeTTSAdapter(**varsayilan).speak(metin)


# --------------------------------------------------------------------------- #
# 1. Bes damga ve monotonluk
# --------------------------------------------------------------------------- #

def test_damgalar_monoton_artar():
    """t0 <= t_istek <= t_ses_hazir <= t_oynatma_basladi <= t_bitti.

    Damgalar dilim sureleri olarak disari verilir; hicbiri negatif olamaz,
    yoksa bir dilim komsusunun suresini calmis demektir.
    """
    r = _konus(
        synth=_gecikmeli(0.05, "C:/tmp/olcum.mp3"),
        player=_oynatici(0.03, 0.04),
    )

    assert r.ok is True
    for alan in ("sentez_ms", "oynatici_kurulum_ms", "oynatma_ms", "toplam_ms"):
        deger = getattr(r, alan)
        assert deger is not None, f"{alan} olculmemis"
        assert deger >= 0, f"{alan} negatif: {deger} -- damgalar sirasiz"


def test_her_gecikme_kendi_diliminde_gorunur():
    r = _konus(
        synth=_gecikmeli(0.08, "C:/tmp/olcum.mp3"),
        player=_oynatici(0.03, 0.05),
    )

    assert 60 <= r.sentez_ms < 130, r.sentez_ms
    assert 15 <= r.oynatici_kurulum_ms < 70, r.oynatici_kurulum_ms
    assert 35 <= r.oynatma_ms < 100, r.oynatma_ms


def test_bilesenlerin_toplami_toplam_ms_i_asmaz():
    """Dilimler ust uste binmez, ve turun kayda deger bir parcasi kaybolmaz."""
    r = _konus(
        synth=_gecikmeli(0.05, "C:/tmp/olcum.mp3"),
        player=_oynatici(0.02, 0.03),
    )

    parca = r.sentez_ms + r.oynatici_kurulum_ms + r.oynatma_ms
    assert parca <= r.toplam_ms + 1.0, (
        f"dilimler ust uste biniyor: {parca} > {r.toplam_ms}"
    )
    assert parca >= r.toplam_ms - 5.0, (
        f"turun {r.toplam_ms - parca:.1f} ms'i hicbir dilime atfedilmemis"
    )


# --------------------------------------------------------------------------- #
# 2. Olculemeyen `None` doner, `0` degil
# --------------------------------------------------------------------------- #

def test_oynatici_kapaliyken_oynatma_ms_None_doner():
    """`play=False`: oynatma sifir SURMEDI, hic OLMADI."""
    def patlayan_oynatici(*_a, **_k):
        raise AssertionError("play=False iken oynatici cagrilmamali")

    r = _konus(player=patlayan_oynatici, play=False)

    assert r.ok is True
    assert r.sentez_ms is not None, "sentez yine de olculmeli"
    assert r.oynatma_ms is None, "oynatilmadi; 0 yazmak 'olctum, bedavaydi' demek"
    assert r.oynatma_ms != 0
    assert r.oynatici_kurulum_ms is None
    assert r.toplam_ms is not None


def test_eski_imzali_oynatici_ile_oynatma_damgasi_None():
    """`player(path)` diyen bir oynatici calmaya basladigini HABER VEREMEZ.

    O durumda uydurulmaz: kurulum ve oynatma ayrilamaz, ikisi de `None`
    kalir. `toplam_ms` yine olculur, cunku o duvar saatidir.
    """
    gorulen = {}

    def eski_oynatici(path):           # on_playback_start YOK
        gorulen["path"] = path
        time.sleep(0.02)

    r = _konus(player=eski_oynatici)

    assert gorulen["path"] == "C:/tmp/olcum.mp3", "eski imza calismali"
    assert r.ok is True
    assert r.sentez_ms is not None
    assert r.oynatici_kurulum_ms is None, (
        "oynatici baslangici bildirmedi; ayrim uydurulamaz"
    )
    assert r.oynatma_ms is None
    assert r.toplam_ms >= 20


def test_sentez_patlarsa_zamanlar_uydurulmaz():
    def bozuk_synth(_metin, _ses):
        raise RuntimeError("ag yok")

    r = _konus(synth=bozuk_synth)

    assert r.ok is False
    assert "synthesis_error" in (r.warning or "")
    for alan in ("sentez_ms", "oynatici_kurulum_ms", "oynatma_ms"):
        assert getattr(r, alan) is None, f"{alan} basarisiz turda uydurulmus"


# --------------------------------------------------------------------------- #
# 3. Mevcut alan silinmedi -- yanina konuldu
# --------------------------------------------------------------------------- #

def test_first_audio_hint_ms_korunur_ve_sentez_ms_ile_ayni_seyi_olcer():
    """Eski alan yerinde durur; yeni alan onun ne oldugunu ADIYLA soyler."""
    r = _konus(synth=_gecikmeli(0.05, "C:/tmp/olcum.mp3"))

    assert r.first_audio_hint_ms is not None, "mevcut alan silinmis"
    assert abs(r.first_audio_hint_ms - r.sentez_ms) < 5.0, (
        "iki alan ayni sentez suresini olcmeli; ayrisirlarsa hangisine "
        f"guvenilecegi belirsizlesir: {r.first_audio_hint_ms} vs {r.sentez_ms}"
    )


def test_bos_metin_ve_kapali_bayrak_yollari_bozulmadi():
    """Damga eklemek mevcut kapilari acmamali."""
    from j0_tts_adapters import EDGE_TTS_ENABLE_FLAG, EdgeTTSAdapter

    def patlayan_synth(_m, _s):
        raise AssertionError("kapaliyken sentez cagrilmamali")

    kapali = EdgeTTSAdapter(synth=patlayan_synth, enabled=False).speak("test")
    assert kapali.ok is False
    assert EDGE_TTS_ENABLE_FLAG in (kapali.warning or "")
    assert kapali.sentez_ms is None

    bos = EdgeTTSAdapter(enabled=True).speak("   ")
    assert bos.ok is False
    assert "text_empty" in (bos.warning or "")
    assert bos.toplam_ms is None


# --------------------------------------------------------------------------- #
# 4. Olcum betigi -- sentetik cumleler ve dogrusal uyum
# --------------------------------------------------------------------------- #

def test_sentetik_cumleler_dort_uzunluk_basamagi_verir():
    """Ahmet'in gercek cevaplari DEGIL; uzunlugu bilinen sentetik metinler.

    Uzunluklar burada kilitli: dosya kodlamasi bozulursa (BOM, cp1254)
    karakter sayisi kayar ve ms/karakter olcumu sessizce yanlis olur.
    """
    from scripts.olc_tts_anatomisi import CUMLELER

    uzunluklar = [len(c) for c in CUMLELER]
    assert len(CUMLELER) == 4
    assert uzunluklar == sorted(uzunluklar), "cumleler artan uzunlukta olmali"
    for gercek, hedef in zip(uzunluklar, (20, 60, 120, 240)):
        assert abs(gercek - hedef) <= 6, (
            f"cumle {gercek} karakter, hedef ~{hedef} -- kodlama bozulmus olabilir"
        )
    for c in CUMLELER:
        assert "ç" in c or "ş" in c or "ı" in c or "ğ" in c or "ü" in c, (
            "Turkce karakter kaybolmus -- kodlama bozuk"
        )


def test_dogrusal_uyum_ahmetin_regresyonunu_yeniden_uretir():
    """Ayni bes nokta, ayni sonuc. Uretmiyorsa yontem farkli demektir.

    Regresyonun ARITMETIGI dogru: 72,2 ms/karakter ve 3.468 ms. Sinanan sey
    o degil, MODELIN kendisi -- egimin saf oynatma hizi olup olmadigi. O
    karsilastirma rapora ait, buraya degil.
    """
    from scripts.olc_tts_anatomisi import dogrusal_uyum

    egim, kesisim, r2 = dogrusal_uyum(
        [194, 133, 91, 86, 62],
        [17634, 12523, 10688, 9675, 7698],
    )

    assert abs(egim - 72.2) < 0.1, egim
    assert abs(kesisim - 3468) < 1.0, kesisim
    assert abs(r2 - 0.986) < 0.001, r2


def test_dogrusal_uyum_iki_noktadan_azini_reddeder():
    """Iki noktadan az veriyle egim yoktur; uydurulmaz."""
    from scripts.olc_tts_anatomisi import dogrusal_uyum

    assert dogrusal_uyum([], []) is None
    assert dogrusal_uyum([5.0], [10.0]) is None


def test_dogrusal_uyum_tek_x_degerinde_bolme_yapmaz():
    """Butun x'ler ayniysa egim tanimsizdir; sonsuzluk yerine `None`."""
    from scripts.olc_tts_anatomisi import dogrusal_uyum

    assert dogrusal_uyum([50, 50, 50], [100, 200, 300]) is None
