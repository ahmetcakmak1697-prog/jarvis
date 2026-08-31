"""memory/life_graph.py sozlesmesi — olgulari kalici hafizaya yazma ve geri okuma.

Iki eksenli guvenlik (CLAUDE.md 7) burada uygulanir:

  guven ekseni  : Ahmet'in kendi soyledigi GUVENILIR icerik
  veri sinifi   : saglik/finans HASSAS -> otomatik kalici hafizaya yazilmaz,
                  onay kuyruguna gider

Yani "Esimin adi Dilara" dogrudan yasam grafigine yazilir; "Penisiline
alerjim var" yazilmaz, incelemeye dusulur.

Ve en onemli sozlesme: RECALL UYDURMAZ. Kayit yoksa "kayit yok" der.
"""
from __future__ import annotations

import json

import pytest


@pytest.fixture()
def graf(tmp_path):
    from memory.life_graph import LifeGraph

    people = tmp_path / "people.json"
    people.write_text(
        json.dumps({"schema_version": 1, "people": [
            {"id": "ahmet", "name": "Ahmet", "role": "primary_user"}
        ]}, ensure_ascii=False),
        encoding="utf-8",
    )
    return LifeGraph(people_path=people, events_path=tmp_path / "events.jsonl")


def olgu(**kw):
    from memory.entity_extractor import ExtractedFact

    varsayilan = dict(
        category="family", relation="es", value="Dilara",
        raw_text="Eşimin adı Dilara", attribute="ad", confidence=0.95,
    )
    varsayilan.update(kw)
    return ExtractedFact(**varsayilan)


# --------------------------------------------------------------------------- #
# 1. Yazma — guvenilir + hassas olmayan olgu kalici olur
# --------------------------------------------------------------------------- #

def test_family_fact_is_persisted(graf):
    sonuc = graf.remember(olgu())
    assert sonuc["stored"] is True
    assert sonuc["target"] == "life_graph"

    kisiler = graf.people()
    es = next(k for k in kisiler if k.get("relation") == "es")
    assert es["name"] == "Dilara"


def test_persisted_fact_survives_reload(graf, tmp_path):
    from memory.life_graph import LifeGraph

    graf.remember(olgu())
    yeni = LifeGraph(people_path=graf.people_path, events_path=graf.events_path)
    assert any(k.get("name") == "Dilara" for k in yeni.people())


def test_json_stays_valid_and_versioned(graf):
    graf.remember(olgu())
    veri = json.loads(graf.people_path.read_text(encoding="utf-8"))
    assert veri["schema_version"] == 1
    assert isinstance(veri["people"], list)


def test_birthday_is_stored_as_attribute(graf):
    graf.remember(olgu(attribute="dogum_gunu", value="3 Mart",
                       raw_text="Eşimin doğum günü 3 Mart"))
    es = next(k for k in graf.people() if k.get("relation") == "es")
    assert es["attributes"]["dogum_gunu"] == "3 Mart"


def test_updating_same_attribute_does_not_duplicate_person(graf):
    graf.remember(olgu())
    graf.remember(olgu(value="Dilara Nur"))
    esler = [k for k in graf.people() if k.get("relation") == "es"]
    assert len(esler) == 1
    assert esler[0]["name"] == "Dilara Nur"


# --------------------------------------------------------------------------- #
# 2. Hassas olgu kalici olmaz -- incelemeye gider
# --------------------------------------------------------------------------- #

def test_sensitive_fact_is_not_persisted(graf):
    sonuc = graf.remember(olgu(category="health", sensitive=True,
                               relation="self", value="penisilin",
                               raw_text="Penisiline alerjim var"))
    assert sonuc["stored"] is False
    assert sonuc["target"] == "review_queue"
    assert "sensitive" in sonuc["reason"]
    # yasam grafigine sizmamis olmali
    assert not any("penisilin" in json.dumps(k, ensure_ascii=False).lower()
                   for k in graf.people())


def test_finance_fact_is_not_persisted(graf):
    sonuc = graf.remember(olgu(category="finance", sensitive=True,
                               relation="self", value="THYAO",
                               raw_text="Portföyümün yarısı THYAO'da"))
    assert sonuc["stored"] is False
    assert sonuc["target"] == "review_queue"


# --------------------------------------------------------------------------- #
# 3. Olay kaydi -- "gecen hafta ne konustuk" icin gercek zemin
# --------------------------------------------------------------------------- #

def test_every_fact_writes_an_event(graf):
    graf.remember(olgu())
    olaylar = graf.events()
    assert len(olaylar) == 1
    assert olaylar[0]["raw_text"] == "Eşimin adı Dilara"
    assert olaylar[0]["ts"]


def test_sensitive_fact_event_does_not_contain_value(graf):
    """Hassas deger olay kaydina DUZ METIN olarak yazilmaz."""
    graf.remember(olgu(category="health", sensitive=True, relation="self",
                       value="penisilin", raw_text="Penisiline alerjim var"))
    dokum = json.dumps(graf.events(), ensure_ascii=False).lower()
    assert "penisilin" not in dokum


def test_events_are_append_only(graf):
    graf.remember(olgu())
    graf.remember(olgu(relation="ogul", value="Kerem",
                       raw_text="Oğlumun adı Kerem"))
    assert len(graf.events()) == 2


# --------------------------------------------------------------------------- #
# 4. RECALL -- en kritik sozlesme: UYDURMAZ
# --------------------------------------------------------------------------- #

def test_recall_returns_stored_fact(graf):
    graf.remember(olgu(attribute="dogum_gunu", value="3 Mart",
                       raw_text="Eşimin doğum günü 3 Mart"))
    cevap = graf.recall("Eşimin doğum günü ne zamandı?")
    assert cevap.found is True
    assert "3 Mart" in cevap.answer
    assert cevap.source == "life_graph"


def test_recall_admits_when_nothing_is_known(graf):
    """Kayit yoksa UYDURMA. Bu, tum motorun varlik sebebi."""
    cevap = graf.recall("Eşimin doğum günü ne zamandı?")
    assert cevap.found is False
    assert cevap.answer == ""
    assert "kayıt yok" in (cevap.reason or "").lower()


def test_recall_of_unknown_relation_is_honest(graf):
    graf.remember(olgu())  # yalnız eş kaydı var
    cevap = graf.recall("Oğlumun adı ne?")
    assert cevap.found is False


def test_recall_finds_name(graf):
    graf.remember(olgu())
    cevap = graf.recall("Eşimin adı ne?")
    assert cevap.found is True
    assert "Dilara" in cevap.answer


def test_recall_grounding_text_is_usable_as_prompt_context(graf):
    """recall_context() modele verilecek ZEMIN metnini uretir."""
    graf.remember(olgu())
    graf.remember(olgu(relation="ogul", value="Kerem",
                       raw_text="Oğlumun adı Kerem"))
    zemin = graf.recall_context()
    assert "Dilara" in zemin and "Kerem" in zemin
    assert "eş" in zemin.lower() or "es" in zemin.lower()


def test_recall_context_is_empty_when_no_facts(graf):
    assert graf.recall_context() == ""
