"""Arac tetikleyicileri ve tur siniflandirmasi — Turkce eslesme sozlesmesi.

Canli testte olculen iki kusur:

1. "Ne haber Jarvis?" WEB ARAMASI tetikledi. `TOOL_TRIGGERS["web_search"]`
   icinde "haber" var ve duz alt-dize eslesmesi yapiliyordu.
2. Selamlar `mid` sinifina dusup agir modele gidiyordu; `_classify()`'in
   `fast_kw` listesi yalniz 7 kelimeydi.

Onemli ayrint: "haber" TAM 5 harf. `memory/entity_extractor.py`'deki
kisa-kok kurali (`< 5` ise kelime siniri) bu kelimeyi kapsamaz -- ve zaten
kapsasa da yetmezdi, cunku "ne haber" icinde "haber" TAM KELIME olarak
geciyor. Ayrim kelime sinirinda degil, **deyimde**: "ne haber" bir
selamlamadir, "son dakika haberleri" bir arama isteğidir.

Bu yuzden iki katman birden gerekiyor:
  a) selamlama deyimleri arac tetiklemez ve `fast` sinifina duser
  b) kisa kokler kelime siniriyla eslesir (baska yanlis pozitifleri keser)
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def ajan():
    """Ollama/arac/hafiza yuklemeden yalin bir ajan ornegi."""
    from agent.local_agent import LocalJarvisAgent

    return LocalJarvisAgent.__new__(LocalJarvisAgent)


def arac(ajan, mesaj):
    sonuc = ajan._detect_tool(mesaj)
    return sonuc[0] if sonuc else None


# --------------------------------------------------------------------------- #
# 1. Selamlar arac TETIKLEMEZ
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mesaj", [
    "Ne haber Jarvis?",
    "ne haber",
    "Naber?",
    "naber jarvis",
    "Merhaba",
    "Selam Jarvis",
    "Günaydın",
    "İyi misin?",
    "Nasılsın?",
    "Teşekkürler",
])
def test_greetings_do_not_trigger_any_tool(ajan, mesaj):
    assert arac(ajan, mesaj) is None, f"{mesaj!r} arac tetiklememeli"


# --------------------------------------------------------------------------- #
# 2. Gercek istekler HALA tetikler (asiri duzeltme kontrolu)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mesaj,beklenen", [
    ("Son dakika haberleri neler?", "web_search"),
    ("Bugünkü ekonomi haberlerini araştır", "web_search"),
    ("Polimer fiyatlarını araştır", "web_search"),
    ("Saat kaç?", "get_datetime"),
    ("Notlarımı göster", "get_notes"),
    ("2+2 kaç eder", "calculate"),
])
def test_real_requests_still_trigger(ajan, mesaj, beklenen):
    assert arac(ajan, mesaj) == beklenen, f"{mesaj!r} -> {beklenen} olmali"


def test_deep_research_still_wins_over_web_search(ajan):
    assert arac(ajan, "Bu konuyu derinlemesine araştır") == "deep_research"


# --------------------------------------------------------------------------- #
# 3. Kisa kok kelime siniri (entity_extractor deseni)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mesaj", [
    "Bana bir öğrenme algoritması anlat",   # "öğren" koku icinde saklı
    "Öğrencilerim için bir şey yaz",
])
def test_short_root_does_not_match_inside_other_words(ajan, mesaj):
    assert arac(ajan, mesaj) is None, f"{mesaj!r} yanlis eslesme uretti"


def test_turkish_capital_i_does_not_break_matching(ajan):
    """CLAUDE.md 6: 'İ'.lower() combining dot uretir; fold bunu cozmeli."""
    assert arac(ajan, "İYİ MİSİN") is None
    assert arac(ajan, "SAAT KAÇ") == "get_datetime"


# --------------------------------------------------------------------------- #
# 4. Tur siniflandirmasi
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mesaj", [
    "Merhaba", "Selam", "Ne haber", "Naber", "Günaydın", "İyi akşamlar",
    "Nasılsın?", "İyi misin?", "Teşekkürler", "Sağ ol", "Tamam", "Evet",
    "Hayır", "Saat kaç", "Görüşürüz",
])
def test_greetings_classify_as_fast(ajan, mesaj):
    assert ajan._classify(mesaj) == "fast", f"{mesaj!r} fast olmali"


@pytest.mark.parametrize("mesaj,beklenen", [
    ("Bu kodu derinlemesine analiz et", "deep"),
    ("Kapsamlı bir rapor hazırla", "deep"),
    ("Python'da dekoratör nasıl yazılır?", "mid"),
    ("ESHOT telemetri verisini nasıl işlerim?", "mid"),
])
def test_non_greetings_keep_their_tier(ajan, mesaj, beklenen):
    assert ajan._classify(mesaj) == beklenen


def test_long_message_is_deep_even_if_it_starts_with_greeting(ajan):
    """Uzun mesaj selamla baslasa bile fast degildir."""
    uzun = "Merhaba, " + ("bu konuyu uzun uzun anlatmam gerekiyor. " * 12)
    assert len(uzun) > 300
    assert ajan._classify(uzun) == "deep"


def test_classify_is_case_and_fold_insensitive(ajan):
    for varyant in ("NASILSIN", "nasilsin", "Nasılsın", "NASILSİN"):
        assert ajan._classify(varyant) == "fast", varyant


# --------------------------------------------------------------------------- #
# 5. Paylasilan yardimci gercekten paylasiliyor mu? (adopt-over-build)
# --------------------------------------------------------------------------- #

def test_keyword_matcher_is_shared_not_duplicated():
    """Ayni esleme mantigi iki yerde ayri ayri yazilmamali."""
    from agents.data_classifier import keyword_present
    from memory.entity_extractor import _kelime_var

    assert _kelime_var is keyword_present, (
        "entity_extractor kendi kopyasini tutuyor; paylasilan yardimciya "
        "delege etmeli (adopt-over-build)"
    )


@pytest.mark.parametrize("metin,anahtar,beklenen", [
    ("bana bir fonksiyonu yaz", "fon", False),   # kisa kok, ic eslesme yok
    ("yatirim fon dagilimi", "fon", True),       # tam kelime
    ("alerjim var", "alerji", True),             # uzun kok, ek almis
    ("ne haber", "haber", True),                 # kelime siniri gecer
])
def test_shared_matcher_behaviour(metin, anahtar, beklenen):
    from agents.data_classifier import keyword_present

    assert keyword_present(metin, anahtar) is beklenen
