"""K1 -- `_detect_tool` arama sorgusunu bozmamali.

Olculdu (2026-09-08), gercek `_detect_tool` uzerinden:

    "son haberler nedir"           -> query: "son ler nedir"
    "yapay zeka haberleri arastir" -> query: "yapay zeka leri arastir"

Sebep: anahtar kelimeler ham `str.replace` ile siliniyordu ve "haber"
koku "haberler" kelimesinin ORTASINDAN kesiliyordu. Arama saglayicisina
anlamsiz bir dize gidiyor, kullanici bunu hic gormuyor.

Iki commit mesajinda adi konmus borctu (`a39dca6`, `be8faaf`):
"[AYRI KUSUR, DUZELTILMEDI] Bozuk sorgu arama saglayicisina o haliyle
gidiyor."

Asil ayrim: kirpilacak sey KOMUT'tur, KONU degil. "arastir" bir
komuttur ve cikarilabilir; "haber" kullanicinin aradigi seyin ta
kendisidir. Ikisi ayni listede toplanmisti.

KAPSAM: bu dosya yalniz konu kelimelerinin korunmasini kilitler.
Komut kaliplarinin kelime siniriyla eslesmesi (ham `str.replace`
yerine) ayri bir istir ve A-04 sozlesme testini etkiledigi icin
Ahmet'e soruldu -- bkz. `automation/IMZASIZ_IS_KUYRUGU.md` K1b.
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def ajan():
    from agent.local_agent import LocalJarvisAgent

    return LocalJarvisAgent.__new__(LocalJarvisAgent)


def _sorgu(ajan, mesaj: str) -> str:
    """Kullanici cumlesinden arama sorgusuna kadar gercek yol."""
    algi = ajan._detect_tool(mesaj)
    assert algi is not None, f"on kosul: cumle bir arac secmeli: {mesaj!r}"
    ad, kwargs = algi
    assert ad == "web_search", f"on kosul: web_search beklendi, gelen {ad}"
    return kwargs["query"]


# ─── 1. Konu kelimesi kesilmiyor ────────────────────────


@pytest.mark.parametrize("mesaj", [
    "son haberler nedir",
    "yapay zeka haberleri arastir",
    "bugunku haberleri ozetle",
    "deprem haberi var mi",
    "ekonomi haberlerinde ne var",
])
def test_haber_koku_kelime_ortasindan_kesilmiyor(ajan, mesaj):
    """"haberler" -> "ler" olmamali: konu kullanicinin aradigi seydir."""
    sorgu = _sorgu(ajan, mesaj)

    assert "haber" in sorgu.lower(), (
        f"konu kelimesi sorgudan silindi: {mesaj!r} -> {sorgu!r}"
    )
    assert " ler" not in sorgu and not sorgu.startswith("ler"), (
        f"kelime ortasindan kesilmis artik kalmis: {sorgu!r}"
    )


def test_ne_oldu_konusu_korunur(ajan):
    """"ne oldu" bir soru bicimidir, komut degil -- konuyu bosaltmamali."""
    sorgu = _sorgu(ajan, "Ankara'da ne oldu")

    assert "ne oldu" in sorgu.lower(), (
        f"soru bicimi silinip sorgu bosaltildi: {sorgu!r}"
    )


@pytest.mark.parametrize("mesaj", [
    "son haberler nedir",
    "deprem haberi var mi",
    "Ankara'da ne oldu",
])
def test_sorgu_orijinalin_kelimelerinden_olusur(ajan, mesaj):
    """Sorguda, orijinal cumlede OLMAYAN bir kelime turememeli.

    Kirpma yalnizca silebilir; yeni kelime uretirse (ornegin "haberler"
    -> "ler") o artik arama sorgusu degil, gurultudur.
    """
    sorgu = _sorgu(ajan, mesaj)
    kaynak = set(mesaj.lower().split())

    for kelime in sorgu.lower().split():
        assert kelime in kaynak, (
            f"sorguda orijinalde olmayan kelime uredi: {kelime!r} "
            f"({mesaj!r} -> {sorgu!r})"
        )


# ─── 2. Asiri duzeltme kontrolu ─────────────────────────


def test_komut_kalibi_hala_kirpilir(ajan):
    """Kirpma mekanizmasi kaldirilmadi: komut hala cikarilir.

    "X hakkinda arastir" cumlesinde "arastir" komuttur; arama
    saglayicisina gitmesi gereksizdir.
    """
    sorgu = _sorgu(ajan, "yapay zeka hakkında araştır")

    assert "yapay zeka" in sorgu.lower()
    assert "araştır" not in sorgu.lower(), (
        f"komut kalibi kirpilmadi: {sorgu!r}"
    )


def test_bos_kalan_sorgu_orijinale_doner(ajan):
    """Kirpma her seyi yerse sorgu orijinale doner -- bos sorgu gitmez."""
    sorgu = _sorgu(ajan, "araştır")

    assert len(sorgu) >= 3, f"bos/kirik sorgu disari cikiyor: {sorgu!r}"


# ─── 3. K1b: komut kaliplari da kelime sinirinda ────────
#
# K1a konu kelimelerini listeden cikardi ama kalan kaliplar hala ham
# `str.replace` ile siliniyordu. Olculdu 2026-09-08:
#
#     "para araci haberleri" -> "paraci haberleri"
#
# "ara " kalibi "para "nin ortasindan kesiyor ve iki kelime KAYNASIYOR.
# Kirpma yalnizca silebilmeli; yeni kelime uretmesi onu arama sorgusu
# olmaktan cikarir.


@pytest.mark.parametrize("mesaj,olmamali", [
    ("para araci haberleri", "paraci"),
    ("kara para haberleri", "kap"),
    # Kaynasmis hali yazilir, koku degil: "ank" dogru ciktinin da
    # icinde ("ankara") ve iddiayi bos yere kirmizi yakardi.
    ("ankara haberleri", "ankhaberleri"),
])
def test_komut_kalibi_kelime_ortasindan_kesmiyor(ajan, mesaj, olmamali):
    """Bitisik iki kelime kaynasmamali: "para araci" -> "paraci" YASAK."""
    sorgu = _sorgu(ajan, mesaj)

    assert olmamali not in sorgu.lower(), (
        f"kelime ortasindan kesilip yeni kelime uredi: {mesaj!r} -> {sorgu!r}"
    )
    assert sorgu == mesaj, (
        f"komut icermeyen cumle degistirilmemeli: {mesaj!r} -> {sorgu!r}"
    )


def test_komut_kalibi_buyuk_harfle_de_kirpilir(ajan):
    """Kirpma fold'lanmis metinde eslesir: BUYUK harf de yakalanir.

    Ham `str.replace` harfe duyarliydi; "ARAŞTIR" hic kirpilmiyordu.
    CLAUDE.md 6: eslestirme her iki tarafa ayni fold uygulanarak yapilir.
    """
    from agents.data_classifier import _fold_tr

    sorgu = _sorgu(ajan, "YAPAY ZEKA HAKKINDA ARAŞTIR")

    # Duz `.lower()` ile karsilastirmak YANILTIR: "ARAŞTIR".lower() noktali
    # "araştir" verir, "araştır" ile eslesmez ve iddia bos yere gecerdi.
    # Iki taraf da ayni fold'dan gecirilir (CLAUDE.md 6).
    assert "arastir" not in _fold_tr(sorgu), (
        f"buyuk harfli komut kirpilmadi: {sorgu!r}"
    )
    assert "yapay zeka" in _fold_tr(sorgu)


def test_komut_silinince_kelimeler_birlesmez(ajan):
    """Kalip iki kelimenin arasindan cikinca komsular yapismaz."""
    sorgu = _sorgu(ajan, "deprem araştır bolgesi haberleri")

    assert "depremboigesi" not in sorgu.lower().replace(" ", "")[:14]
    for kelime in sorgu.lower().split():
        assert kelime in {"deprem", "bolgesi", "haberleri"}, (
            f"beklenmeyen kelime: {kelime!r} ({sorgu!r})"
        )
