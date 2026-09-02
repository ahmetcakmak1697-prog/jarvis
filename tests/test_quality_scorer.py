"""eval/quality_scorer.py — deterministik kalite puanlamasi sozlesmesi.

Bu puanlayici SAF: model calistirmaz, ag'a cikmaz, donanima dokunmaz. Girdi
bir vaka + bir cevap metni, cikti olculebilir sinyaller. Boylece puanlama
mantigi Ollama olmadan, deterministik olarak test edilebilir -- ayni ayrimi
`voice/stt.py`'de de yapmistik (donanim mantiktan ayri).

Puanlanan sey KODLAMA BUTUNLUGU ve DAVRANIS, akicilik DEGIL. Turkce
akiciligi Ahmet'in kulagi degerlendirir (FAZ-T1 deseni); bu takim yalnizca
regresyonu tutar.
"""
from __future__ import annotations

import pytest


def puanla(cevap, vaka=None, **kw):
    from eval.quality_scorer import score_answer

    return score_answer(cevap, vaka or {}, **kw)


# --------------------------------------------------------------------------- #
# 1. Bozuk kodlama — paylasilan dedektor yeniden kullanilmali
# --------------------------------------------------------------------------- #

def test_clean_turkish_has_no_encoding_findings():
    s = puanla("Efendim, bugün hava oldukça güzel görünüyor.")
    assert s["encoding_broken"] == []
    assert s["encoding_ok"] is True


def test_mojibake_is_detected():
    s = puanla("Efendim, hava gÃ¼zel gÃ¶rÃ¼nÃ¼yor.")
    assert s["encoding_ok"] is False
    assert s["encoding_broken"]


def test_question_mark_corruption_is_detected():
    s = puanla("Turkce kon??, gerekmedikce Ingilizce karis tirma.")
    assert s["encoding_ok"] is False


def test_scorer_uses_the_shared_detector_not_a_copy():
    """adopt-over-build: ikinci bir kopya tutulmamali."""
    from agents.data_classifier import corrupted_fragments
    from eval import quality_scorer

    assert quality_scorer.corrupted_fragments is corrupted_fragments


# --------------------------------------------------------------------------- #
# 2. Yabanci kelime sizintisi
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("cevap,bekle", [
    ("Efendim, tabii ki yardımcı olurum.", []),
    ("Okay, hemen bakıyorum efendim.", ["okay"]),
    ("Voila! İşte sonuç.", ["voila"]),
    ("Sure, here's the answer you need.", ["sure,", "here's"]),
])
def test_foreign_words_are_flagged(cevap, bekle):
    s = puanla(cevap)
    for k in bekle:
        assert k in s["foreign_hits"], f"{k!r} yakalanmali: {s['foreign_hits']}"
    if not bekle:
        assert s["foreign_hits"] == []


def test_turkish_words_are_not_mistaken_for_english():
    """Turkce cumle Ingilizce sanilmamali (yanlis pozitif kontrolu)."""
    s = puanla("Bu yaklaşım daha verimli olabilir; ölçüm sonuçları ekte.")
    assert s["foreign_hits"] == []


# --------------------------------------------------------------------------- #
# 3. Persona uyumu
# --------------------------------------------------------------------------- #

def test_efendim_is_detected_case_insensitively():
    assert puanla("efendim, tamamdır.")["has_efendim"] is True
    assert puanla("EFENDİM, tamamdır.")["has_efendim"] is True
    assert puanla("Tamamdır.")["has_efendim"] is False


@pytest.mark.parametrize("cevap,bekle", [
    ("Size nasıl yardımcı olabilirim?", True),
    ("Yardımcı olmaktan mutluluk duyarım.", True),
    ("Elbette, hemen yapıyorum.", True),
    ("Liste değiştirilebilir, demet değiştirilemez.", False),
])
def test_ai_boilerplate_is_flagged(cevap, bekle):
    assert puanla(cevap)["ai_boilerplate"] is bekle


def test_expect_efendim_is_scored_only_when_declared():
    vaka = {"expect_efendim": True}
    assert puanla("Efendim, tamam.", vaka)["persona_ok"] is True
    assert puanla("Tamam.", vaka)["persona_ok"] is False
    # beyan edilmemisse persona_ok None -- puanlanmaz, uydurulmaz
    assert puanla("Tamam.", {})["persona_ok"] is None


def test_expect_efendim_false_means_forbidden_not_optional():
    """Alanin UC anlami yok, IKI anlami var.

    Ilk vaka setinde `expect_efendim: false` "onemsiz" niyetiyle yazilmisti;
    puanlayici bunu "YASAK" diye okudu ve canli kosuda modeli KARAKTERDE
    OLDUGU icin kaldirdi (t2_longform_004: cevap "**Efendim, ...**" diye
    basliyordu). Alan v2'de tum vakalardan kaldirildi; anlami burada kilitli
    ki niyet bir daha karismasin: onemsizse alan HIC yazilmaz.
    """
    vaka = {"expect_efendim": False}
    assert puanla("Tamam.", vaka)["persona_ok"] is True
    assert puanla("Efendim, tamam.", vaka)["persona_ok"] is False


def test_v2_cases_do_not_declare_expect_efendim():
    """Hitap RAPORLANIR, puanlanmaz -- persona 'her cumlede degil' diyor."""
    import json
    from pathlib import Path

    yol = Path(__file__).resolve().parents[1] / "eval" / "turkish_quality_cases.json"
    veri = json.loads(yol.read_text(encoding="utf-8"))
    beyan_edenler = [c["id"] for c in veri["cases"] if "expect_efendim" in c]
    assert beyan_edenler == [], (
        f"su vakalar hitabi zorunlu/yasak tutuyor: {beyan_edenler}. "
        "Geri cagirma dogrulugu ile hitap bicimi ayri seylerdir."
    )


# --------------------------------------------------------------------------- #
# 4. Zemin davranisi — bu takimin en onemli olcusu
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("cevap", [
    "Efendim, bu bilgiye erişimim yok.",
    "Bu konuda kaydım yok.",
    "Bilmiyorum, elimde bir kayıt bulunmuyor.",
    "Üzgünüm, o konuşmanın kaydına erişemiyorum.",
    "Bu bilgiye sahip değilim.",
])
def test_honest_no_record_answers_are_recognised(cevap):
    s = puanla(cevap, {"must_admit_no_record": True})
    assert s["admits_no_record"] is True
    assert s["grounding_ok"] is True


@pytest.mark.parametrize("cevap", [
    # CANLI kosuda llama3.1'in fiilen verdigi cevaplar. Ilk iki surum bunlari
    # "uydurma" saydi -- listede "erisemiyorum" vardi ama "erisemedim" yoktu.
    # Turkce sondan eklemeli: cekim listelemek yerine KOK eslesmesi yapilir.
    # Yanlis negatif burada pahali: durust cevabi uydurma saymak modeli haksiz
    # suclar ve olcumu curutur.
    "Geçen hafta ne konuştuğumuza erişemedim.",
    "Geçen ayın projeksiyonuna erişemedim.",
    "Hatırlamıyorum efendim.",
    "Bu konuda bir kayda sahip değilim.",
])
def test_turkish_conjugations_of_no_record_are_recognised(cevap):
    s = puanla(cevap, {"must_admit_no_record": True})
    assert s["admits_no_record"] is True, (
        f"{cevap!r} durust bir itiraf; cekim yuzunden kacirilmamali"
    )


@pytest.mark.parametrize("cevap", [
    "Geçen hafta telemetri sistemini konuşmuştuk.",
    "Annenizin adı Ayşe.",
    "Dün akşam size pandas kullanmanızı önermiştim.",
])
def test_fabricated_answers_fail_grounding(cevap):
    s = puanla(cevap, {"must_admit_no_record": True})
    assert s["admits_no_record"] is False
    assert s["grounding_ok"] is False


def test_grounding_not_scored_when_not_declared():
    assert puanla("Herhangi bir cevap.", {})["grounding_ok"] is None


def test_recall_case_requires_the_stored_fact():
    vaka = {"must_contain_any": [["Dilara"]]}
    assert puanla("Efendim, eşinizin adı Dilara.", vaka)["contains_ok"] is True
    assert puanla("Efendim, eşinizin adı Ayşe.", vaka)["contains_ok"] is False


def test_multiple_required_groups_all_must_hit():
    vaka = {"must_contain_any": [["Dilara"], ["Kerem"]]}
    assert puanla("Dilara ve Kerem.", vaka)["contains_ok"] is True
    assert puanla("Sadece Dilara.", vaka)["contains_ok"] is False


# --------------------------------------------------------------------------- #
# 5. Uzunluk kurallari
# --------------------------------------------------------------------------- #

def test_min_chars_is_enforced_when_declared():
    vaka = {"min_chars": 50}
    assert puanla("x" * 60, vaka)["length_ok"] is True
    assert puanla("kısa", vaka)["length_ok"] is False
    assert puanla("kısa", {})["length_ok"] is None


# --------------------------------------------------------------------------- #
# 6. Genel karar — yalniz BEYAN EDILEN olculer sayilir
# --------------------------------------------------------------------------- #

def test_case_passes_when_all_declared_checks_pass():
    vaka = {"must_admit_no_record": True, "expect_efendim": True}
    s = puanla("Efendim, bu bilgiye erişimim yok.", vaka)
    assert s["passed"] is True
    assert s["failed_checks"] == []


def test_case_fails_and_names_the_failing_check():
    vaka = {"must_admit_no_record": True}
    s = puanla("Geçen hafta bunu konuşmuştuk.", vaka)
    assert s["passed"] is False
    assert "grounding" in s["failed_checks"]


def test_encoding_failure_always_fails_the_case():
    """Bozuk kodlama, hicbir sey beyan edilmese bile basarisizliktir."""
    s = puanla("hava gÃ¼zel", {})
    assert s["passed"] is False
    assert "encoding" in s["failed_checks"]


def test_empty_answer_fails():
    s = puanla("", {})
    assert s["passed"] is False
    assert "empty" in s["failed_checks"]


def test_scoring_is_deterministic():
    vaka = {"must_admit_no_record": True, "expect_efendim": True}
    a = puanla("Efendim, erişimim yok.", vaka)
    b = puanla("Efendim, erişimim yok.", vaka)
    assert a == b


# --------------------------------------------------------------------------- #
# 7. Gecikme ve Turkce-esdeger cevrimi
# --------------------------------------------------------------------------- #

def test_turkish_equivalent_applies_tokenizer_penalty():
    """HARDWARE_AND_LOCAL_LLM_RESEARCH.md 4: Turkce ~1.9x token harciyor."""
    from eval.quality_scorer import turkish_equivalent_tps

    assert turkish_equivalent_tps(76.0) == pytest.approx(40.0, abs=0.1)
    assert turkish_equivalent_tps(0) == 0


def test_vram_ceiling_flag():
    from eval.quality_scorer import exceeds_vram_ceiling

    assert exceeds_vram_ceiling(6880) is True    # mistral-nemo, olculdu
    assert exceeds_vram_ceiling(5386) is False   # qwen2.5:7b, olculdu
