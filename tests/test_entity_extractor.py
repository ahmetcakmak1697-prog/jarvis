"""memory/entity_extractor.py sozlesmesi — konusmadan varlik/olgu cikarma.

Tasarim karari: cikarim DETERMINISTIK, LLM'siz. Nedeni CLAUDE.md 7:
"Deterministik routing = guvenlik ozelligi." Bir LLM'e "bu cumleden olgu cikar"
demek, hafizaya ne yazilacagini modelin kaprisine birakmak olurdu; ayni cumle
iki kez farkli sey uretebilir ve halusinasyon dogrudan kalici hafizaya sizar.
Kural tabanli cikarim ise test edilebilir, ucretsiz ve tekrarlanabilir.

Turkce ozellikleri (CLAUDE.md 6): esleme ASCII-fold uzerinden yapilir,
'İ'.lower() tuzagina dusulmez, sondan eklemeli yapida substring kullanilir.
"""
from __future__ import annotations

import pytest


def cikar(metin):
    from memory.entity_extractor import extract

    return extract(metin)


def tek(metin):
    """Tek olgu bekleyen testler icin kisayol."""
    olgular = cikar(metin)
    assert len(olgular) == 1, f"tam 1 olgu bekleniyordu, {len(olgular)} geldi: {olgular}"
    return olgular[0]


# --------------------------------------------------------------------------- #
# 1. Aile
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("metin,iliski,deger", [
    ("Eşimin adı Dilara", "es", "Dilara"),
    ("Karımın adı Dilara", "es", "Dilara"),
    ("Eşim Dilara ile sinemaya gittik", "es", "Dilara"),
    ("Oğlumun adı Kerem", "ogul", "Kerem"),
    ("Kızımın adı Zeynep", "kiz", "Zeynep"),
    ("Annemin adı Ayşe", "anne", "Ayşe"),
    ("Babamın adı Mehmet", "baba", "Mehmet"),
])
def test_family_names_are_extracted(metin, iliski, deger):
    olgu = tek(metin)
    assert olgu.category == "family"
    assert olgu.relation == iliski
    assert olgu.value == deger


def test_spouse_birthday_is_extracted():
    olgu = tek("Eşimin doğum günü 3 Mart")
    assert olgu.category == "family"
    assert olgu.relation == "es"
    assert olgu.attribute == "dogum_gunu"
    assert "3 Mart" in olgu.value


def test_capital_i_does_not_break_matching():
    """CLAUDE.md 6: 'İ'.lower() combining dot uretir; fold bunu cozmeli."""
    olgu = tek("İkiz kızımın adı Zeynep")
    assert olgu.relation == "kiz"
    assert olgu.value == "Zeynep"


# --------------------------------------------------------------------------- #
# 2. Is, spor, saglik, finans, hobi
# --------------------------------------------------------------------------- #

def test_work_is_extracted():
    olgu = tek("ESHOT'ta tekniker olarak çalışıyorum")
    assert olgu.category == "work"
    assert "ESHOT" in olgu.value


def test_sport_is_extracted():
    olgu = tek("Haftada üç gün koşuyorum")
    assert olgu.category == "sport"
    assert "koş" in olgu.value.lower() or "koşu" in olgu.raw_text.lower()


def test_hobby_is_extracted():
    olgu = tek("Hobim Arduino ile uğraşmak")
    assert olgu.category == "hobby"
    assert "Arduino" in olgu.value


def test_health_is_marked_sensitive():
    """Saglik verisi hassas: otomatik kalici hafizaya YAZILMAZ."""
    olgu = tek("Penisiline alerjim var")
    assert olgu.category == "health"
    assert olgu.sensitive is True


def test_finance_is_marked_sensitive():
    olgu = tek("Portföyümün yarısı THYAO hissesinde")
    assert olgu.category == "finance"
    assert olgu.sensitive is True


def test_family_and_work_are_not_sensitive():
    assert tek("Eşimin adı Dilara").sensitive is False
    assert tek("ESHOT'ta tekniker olarak çalışıyorum").sensitive is False


# --------------------------------------------------------------------------- #
# 3. Yanlis pozitif olmamali
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("metin", [
    "Merhaba",
    "Bugün hava nasıl?",
    "Bana bir Python fonksiyonu yaz",
    "Nerede kaldık?",
    "",
    "   ",
])
def test_no_facts_from_ordinary_chat(metin):
    assert cikar(metin) == []


def test_question_about_spouse_is_not_a_fact():
    """'Esimin dogum gunu ne zaman?' bir SORU, kaydedilecek bir olgu degil."""
    assert cikar("Eşimin doğum günü ne zaman?") == []


def test_negation_is_not_stored_as_fact():
    assert cikar("Eşim yok") == []


# --------------------------------------------------------------------------- #
# 4. Olgu yapisi ve kaynak izlenebilirligi
# --------------------------------------------------------------------------- #

def test_fact_carries_provenance():
    """Her olgu hangi cumleden geldigini tasimali -- denetlenebilirlik."""
    metin = "Eşimin adı Dilara"
    olgu = tek(metin)
    assert olgu.raw_text == metin
    assert olgu.confidence > 0.0
    assert olgu.to_dict()["relation"] == "es"


def test_multiple_facts_in_one_sentence():
    olgular = cikar("Eşimin adı Dilara, oğlumun adı Kerem")
    iliskiler = {o.relation for o in olgular}
    assert iliskiler == {"es", "ogul"}


def test_extract_is_deterministic():
    """Ayni girdi -> ayni cikti. LLM olmadigi icin garanti."""
    metin = "Eşimin adı Dilara ve haftada üç gün koşuyorum"
    a = [o.to_dict() for o in cikar(metin)]
    b = [o.to_dict() for o in cikar(metin)]
    assert a == b
