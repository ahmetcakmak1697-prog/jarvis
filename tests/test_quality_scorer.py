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

import json
from pathlib import Path

import pytest


def puanla(cevap, vaka=None, **kw):
    from eval.quality_scorer import score_answer

    return score_answer(cevap, vaka or {}, **kw)


#: 2026-09-01 canli kosusunun makine okunur ciktisi. Repoda kayitli; uc yeni
#: dedektorun fixture'lari BURADAN gelir, elle yazilmaz. Elle yazilmis "ornek
#: bozuk cevap" dedektoru degil, yazarin hayalini olcer.
_CANLI_KOSU = (Path(__file__).resolve().parents[1] / "automation"
               / "KALITE_llama3.1_latest_20260901-2314.json")

_VAKALAR = (Path(__file__).resolve().parents[1] / "eval"
            / "turkish_quality_cases.json")


#: 2026-09-04 kiyas kosusunun iki ciktisi. Terazinin uc kusuru bu iki
#: dosyanin elle okunmasindan cikti (`automation/MODEL_KIYASI_2026-09-04.md`).
_KOSULAR = {
    "llama-0901": _CANLI_KOSU,
    "llama-0904": _CANLI_KOSU.with_name("KALITE_llama3.1_latest_20260904-2053.json"),
    "qwen-0904": _CANLI_KOSU.with_name("KALITE_qwen2.5_7b_20260904-2057.json"),
}


@pytest.fixture(scope="module")
def gercek_cevap():
    """(id[, kosu]) -> o vakada modelin GERCEKTEN verdigi cevap."""
    onbellek: dict = {}

    def al(vaka_id: str, kosu: str = "llama-0901") -> str:
        if kosu not in onbellek:
            veri = json.loads(_KOSULAR[kosu].read_text(encoding="utf-8"))
            onbellek[kosu] = {r["id"]: r.get("answer") or "" for r in veri["results"]}
        return onbellek[kosu][vaka_id]

    return al


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


# --- Kusur 3a: yabanci sizinti artik PUANLANIYOR -------------------------- #
#
# `foreign_hits` olculuyor ama puanlanmiyordu. Kiyasta bedeli gorulmustu:
# qwen `t2_memory_002`'de Turkce cumlenin ortasina bosluksuz bir Ingilizce
# cumle yapistirdi ve vaka GECTI. Ama listeyi oldugu gibi puanlamak da
# olmuyor: 192 cevapta 5 eslesmenin 3'u yanlis pozitifti (albüm adlari,
# Python anahtar kelimesi). Puanlanan sey bu yuzden tek kelime degil,
# ARDISIK Ingilizce DIZISI.

def test_an_english_sentence_spliced_into_turkish_fails(gercek_cevap):
    """qwen `t2_memory_002` -- kartin gosterdigi vaka. Onceden GECIYORDU."""
    s = puanla(gercek_cevap("t2_memory_002", "qwen-0904"))
    assert s["foreign_ok"] is False
    assert "foreign" in s["failed_checks"]


def test_a_whole_english_answer_to_a_turkish_prompt_fails(gercek_cevap):
    """qwen `t1_tone_017`: soru Turkce, cevabin tamami Ingilizce."""
    vaka = {"prompt": "Seni İngilizce konuş diye eğitmek istiyorum"}
    assert puanla(gercek_cevap("t1_tone_017", "qwen-0904"), vaka)["foreign_ok"] is False


def test_english_proper_nouns_are_not_a_foreign_leak(gercek_cevap):
    """llama `t1_tone_014`: AC/DC albüm adlari. OLCULEN yanlis pozitif.

    Eski kural ' the ' ve ' and ' parcalariyla bu cevabi isaretliyordu;
    "Highway to Hell", "The Razors Edge" ozel isimdir ve persona
    "GEREKMEDIKCE Ingilizce karistirmazsin" diyor -- burada gerekli.
    """
    assert puanla(gercek_cevap("t1_tone_014", "llama-0904"))["foreign_ok"] is True


def test_english_inside_a_code_block_is_not_a_foreign_leak(gercek_cevap):
    """qwen `t1_tech_005`: `with open(...)` -- Python anahtar kelimesi.

    Kod blogu tekrar dedektorunde zaten haric tutuluyordu; ayni ayrim
    burada da gecerli (adopt-over-build, `_prose_only`).
    """
    assert puanla(gercek_cevap("t1_tech_005", "qwen-0904"))["foreign_ok"] is True


def test_english_answer_to_an_english_prompt_is_allowed():
    """Persona: "Ahmet İngilizce yazarsa İngilizce yanıt verirsin."

    `t1_mix_001` vaka setindeki tek Ingilizce prompt. Ingilizce cevabi
    kusur saymak, personanin kendi kuralina uyan modeli dusurmek olurdu --
    `expect_efendim` hatasinin ucuncu tekrari.
    """
    vaka = {"prompt": "hey can you check the system status?"}
    cevap = "Sure, I can check the system status for you right now, sir."
    assert puanla(cevap, vaka)["foreign_ok"] is True


def test_foreign_is_not_scored_below_the_run_threshold():
    """Tek bir Ingilizce kelime cumle sizintisi degildir; raporlanir."""
    s = puanla("Efendim, bu bir okay durumu değil; ölçümü tekrarlayalım.")
    assert s["foreign_hits"], "raporlanan sinyal kaybolmamali"
    assert s["foreign_ok"] is True


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


# --- Kusur 3b: kalip artik PUANLANIYOR ------------------------------------ #

def test_ai_boilerplate_now_fails_the_case():
    """Persona kalibi ACIKCA yasakliyor; olculuyor ama puanlanmiyordu.

    Kiyasta bedeli: qwen 11/64 vakada kalip kullandi ve hepsi gecti
    (llama 0/64). 192 cevapta olculdu, yanlis pozitif YOK -- 11 eslesmenin
    hepsi persona'nin adiyla yasakladigi ifadeler.
    """
    s = puanla("Merhaba, nasıl yardımcı olabilirim?")
    assert s["ai_boilerplate"] is True
    assert "boilerplate" in s["failed_checks"]
    assert s["passed"] is False


def test_a_direct_answer_carries_no_boilerplate_penalty():
    s = puanla("Liste değiştirilebilir, demet değiştirilemez.")
    assert s["ai_boilerplate"] is False
    assert "boilerplate" not in s["failed_checks"]


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
# 7. Sistem prompt'u sizintisi
# --------------------------------------------------------------------------- #
#
# Asagidaki cevaplarin HEPSI 2026-09-01 canli kosusundan alinmadir (rapor:
# automation/KALITE_llama3.1_latest_20260901-2314.json). Uydurma ornek yok:
# makine bu kusurlarin hicbirini goremedigi icin altisi da "gecti" sayilmisti.

def test_prompt_leak_catches_a_recited_persona_sentence():
    """t1_tech_008: "aktif profil hangisi?" -> persona'nin bir cumlesi."""
    s = puanla("Reaktif değil, proaktifsin.")
    assert s["prompt_leak"] is True
    assert "prompt_leak" in s["failed_checks"]
    assert s["passed"] is False


def test_prompt_leak_catches_the_you_are_me_confusion():
    """t1_tone_013: persona'yi geri okuyup 'sen'i kullaniciya yapistiriyor."""
    s = puanla("Ahmet'in hedefi senin hedefin değil, onun hedefi senin hedefin.")
    assert s["prompt_leak"] is True


def test_prompt_leak_catches_a_whole_block_dump(gercek_cevap):
    """t1_mix_003: persona'nin tamamini markdown olarak dokmus."""
    assert puanla(gercek_cevap("t1_mix_003"))["prompt_leak"] is True


def test_using_an_identity_fact_is_not_a_leak():
    """t1_tone_012 -- OLCULEN esik siniri, kartin uyardigi yanlis pozitif.

    Cevap kimlik onsozundeki bir olguyu ("polimer ve İSG") KULLANIYOR;
    talimat cumlesi geri okumuyor. "Hafizanda benim hakkimda ne var?"
    sorusuna dogru davranis budur. Bunu sizinti saymak, `expect_efendim`
    hatasinin tekrari olurdu: modeli DOGRU davrandigi icin kaldirmak.
    Dedektor bu yuzden yalnizca "## " baslikli TALIMAT bloklarina bakar.
    """
    s = puanla("Efendim, senin teknik uzmanı olarak polimer ve İSG "
               "konularında çalıştığımı hatırlıyorum. Son olarak, ESHOT'ta "
               "teknik görevini sürdürdüğünü biliyorum.")
    assert s["prompt_leak"] is False


@pytest.mark.parametrize("cevap", [
    "Merhaba Efendim.",
    "Evet, sonunda çalıştı.",
    "O zaman bu, bir test miydi? Beni test ettin, geçtim!",
    "`[]` içinde elemanları yazarak. Örnek:\n```python\nliste = [1, 2, 3]\n```",
])
def test_clean_answers_do_not_trip_the_leak_detector(cevap):
    assert puanla(cevap)["prompt_leak"] is False


def test_a_forbidden_example_phrase_is_not_a_leak():
    """Kusur 1: qwen'in 6 "sizintisinin" 4'u tam olarak buydu.

    Persona bu cumleyi YASAK ORNEGI olarak tasiyor ("... gibi yapay zeka
    kaliplari kullanma"). Modelin onu kurmasi bir kusur -- ama `ai_boilerplate`
    kusuru, sizinti degil. Iki ayri sey ayni sayaca giriyordu, ustelik ayni
    ifade iki sutunda birden sayiliyordu.
    """
    s = puanla("Efendim, size yardımcı olmaktan mutluluk duyarım.")
    assert s["prompt_leak"] is False
    assert "prompt_leak" not in s["failed_checks"]
    assert s["ai_boilerplate"] is True, "kusur kaybolmamali, YER degistirmeli"


def test_a_phrase_the_persona_tells_jarvis_to_say_is_not_a_leak():
    """Persona `## GERÇEKLİK KURALI`: '"bu konusmanin kaydina erisimim yok" de'.

    Model bunu soyleyince DOGRU davranmis olur. Sizinti saymak, durust
    itirafi cezalandirmak demekti -- ve tam olarak zemin kategorisinde,
    yani en cok onemsedigimiz yerde patlardi. Olculmus gizli tuzak.
    """
    assert puanla("Efendim, bu konuşmanın kaydına erişimim yok.")["prompt_leak"] is False


def test_style_examples_are_not_leaks():
    """`## KİŞİLİĞİN` bloğundaki ornekler modelin KURMASI istenen cumleler."""
    s = puanla("Efendim, hesaplarıma göre bu yaklaşım daha verimli olabilir.")
    assert s["prompt_leak"] is False


def test_quoted_examples_leave_the_corpus_but_instructions_stay():
    """Kural metinden turer: tirnakli olan ORNEK, tirnaksiz olan TALIMAT.

    Persona'nin talimat bolumundeki her tirnakli parca -- yasak kalip,
    soylenmesi istenen cumle, uslup ornegi -- ornektir; hicbiri talimat
    degildir. Olculdu: 13 tirnakli parca, hepsi ornek.
    """
    import re

    from agents.persona import build_system_prompt

    p = build_system_prompt()
    talimat = p[p.find("## "):]
    for m in re.finditer(r'"([^"\n]{22,})"', talimat):
        assert puanla(m.group(1))["prompt_leak"] is False, (
            f"tirnakli ornek sizinti sayilmis: {m.group(1)!r}"
        )


def test_leak_corpus_is_derived_from_the_persona_ssot():
    """Metin KOPYALANMAZ, `build_system_prompt()`'tan turetilir.

    Persona degisirse dedektor de degisir. Bir kopya tutulsaydi bu test
    persona guncellendigi anda sessizce yalan soylemeye baslardi.
    """
    from agents.persona import build_system_prompt

    prompt = build_system_prompt(level="L2")
    madde = next(s for s in prompt.splitlines()
                 if s.startswith("- ") and len(s.split()) >= 8)
    assert puanla(madde)["prompt_leak"] is True


# --------------------------------------------------------------------------- #
# 8. Tekrar (dejenerasyon)
# --------------------------------------------------------------------------- #

def test_repetition_flags_the_degenerate_longform(gercek_cevap):
    """t2_longform_001: ayni 15 kelimelik dizi kelimesi kelimesine 4 kez."""
    s = puanla(gercek_cevap("t2_longform_001"))
    assert s["repetition_ok"] is False
    assert "repetition" in s["failed_checks"]


def test_repetition_flags_the_second_degenerate_longform(gercek_cevap):
    """t2_longform_003: "enerji verimliliğini artırmak için..." 4 kez."""
    assert puanla(gercek_cevap("t2_longform_003"))["repetition_ok"] is False


def test_two_occurrences_are_tolerated(gercek_cevap):
    """t1_tr_005 bir paragrafi IKI kez tekrarliyor -- esik 3'te KALIR.

    Karara baglandi: A13, 2026-09-04, Ahmet. 2x'in "yanlis pozitif yok"
    olcumu TEK modelin 64 cevabi uzerinde yapildi; bu takimin varlik sebebi
    modelleri kiyaslamak, ve llama3.1'de temiz olan esik baska modelde
    paralel kurulu bir listede tokezleyebilir. Iyi bir cevabi haksiz yere
    dusurmek olcumun kendisini curutur (`_NO_RECORD_ROOTS` notuyla ayni
    asimetri). 2x sayisi yine de kaybolmasin diye RAPORLANIR:
    bkz. `test_two_times_repetition_is_reported_but_not_scored`.
    """
    assert puanla(gercek_cevap("t1_tr_005"))["repetition_ok"] is True


def test_two_times_repetition_is_reported_but_not_scored(gercek_cevap):
    """A13: 2x olculur ve yazilir, ama vakayi DUSURMEZ.

    `has_efendim` / `ai_boilerplate` ile ayni siniftadir. Amaci sayiyi
    kaybetmemek: ikinci bir model olculdugunde "esik 2 olsaydi ne olurdu"
    sorusuna, takimi yeniden kosturmadan cevap verilebilsin.
    """
    s = puanla(gercek_cevap("t1_mix_002"))
    assert s["repeated_phrase_2x"] is not None
    assert s["repetition_ok"] is True
    assert "repetition" not in s["failed_checks"]
    assert s["passed"] is True


def test_three_times_repetition_is_both_reported_and_scored(gercek_cevap):
    """Raporlanan esik puanlananin ust kumesidir: 4x olan 2x'i de asar."""
    s = puanla(gercek_cevap("t2_longform_001"))
    assert s["repeated_phrase_2x"] is not None
    assert s["repetition_ok"] is False


@pytest.mark.parametrize("id_", ["t1_tr_001", "t1_tr_010", "t1_tone_001"])
def test_clean_answers_have_nothing_to_report(gercek_cevap, id_):
    assert puanla(gercek_cevap(id_))["repeated_phrase_2x"] is None


def test_repetition_thresholds_are_locked():
    """A13'un karari koda kilitlenir: puanlanan 3, raporlanan 2.

    Sayiyi degistirmek bir sozlesme degisikligidir (CLAUDE.md 13.1) --
    ne asagi ne yukari, Ahmet'e sorulmadan.
    """
    from eval.quality_scorer import (
        REPETITION_MIN_HITS,
        REPETITION_REPORT_MIN_HITS,
    )

    assert REPETITION_MIN_HITS == 3
    assert REPETITION_REPORT_MIN_HITS == 2


def test_repetition_ignores_code_block_content():
    """Kod blogunda tekrar mesrudur -- ayni satiri 4 kez yazmak kusur degil."""
    kod = "\n".join(["```", *["df = df.fillna(0)  # ayni satir tekrar tekrar yazilir"] * 4, "```"])
    assert puanla("Örnek:\n" + kod)["repetition_ok"] is True


@pytest.mark.parametrize("id_", ["t1_tr_001", "t1_tr_007", "t1_tr_010",
                                 "t1_tone_001", "t1_tone_019", "t1_tone_020"])
def test_good_answers_are_not_called_repetitive(gercek_cevap, id_):
    assert puanla(gercek_cevap(id_))["repetition_ok"] is True


# --------------------------------------------------------------------------- #
# 9. Kesilme
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("id_", ["t1_tech_003", "t1_mix_004", "t1_tr_014",
                                 "t2_longform_001", "t2_longform_002",
                                 "t2_longform_003", "t2_longform_004"])
def test_mid_sentence_cut_is_detected(gercek_cevap, id_):
    """`min_chars` yalniz ASGARI uzunluga bakar; kesilmeyi goremez."""
    s = puanla(gercek_cevap(id_))
    assert s["truncated"] is True, f"{id_} cumle ortasinda bitiyor"
    assert "truncated" in s["failed_checks"]


@pytest.mark.parametrize("id_", ["t1_tone_001", "t1_tr_010", "t1_tr_001",
                                 "t1_tech_008", "t1_mix_002"])
def test_finished_answers_are_not_called_truncated(gercek_cevap, id_):
    assert puanla(gercek_cevap(id_))["truncated"] is False


def test_short_answers_are_never_called_truncated():
    """Uzunluk sarti kisa ve uslupca bitirilmis cevaplari korur."""
    assert puanla("Evet")["truncated"] is False


def test_a_closed_code_fence_is_a_valid_ending():
    """Sinir testi (canli cevap degil): 200 karakteri asan hicbir cevap bu
    kosuda kod citiyle bitmedi, ama kural kartta yazili ve kilitlenmeli."""
    govde = ("Verileri okumak icin asagidaki parcayi kullanabilirsiniz; "
             "dosya yolunu kendi dizininize gore degistirmeniz yeterli "
             "olacaktir, geri kalan adimlar aynidir ve ek bir ayar "
             "gerektirmez.\n```python\nimport pandas as pd\ndf = pd.read_csv('a.csv')\n```")
    assert len(govde) > 200
    assert puanla(govde)["truncated"] is False


# --------------------------------------------------------------------------- #
# 10. Uydurma kapsami — `technical` kategorisi
# --------------------------------------------------------------------------- #

def test_technical_fabrication_cases_declare_no_record():
    """Canli veri okuyamayan dort teknik vaka artik zemin beyani tasiyor."""
    yol = Path(__file__).resolve().parents[1] / "eval" / "turkish_quality_cases.json"
    veri = json.loads(yol.read_text(encoding="utf-8"))
    beyan = sorted(c["id"] for c in veri["cases"]
                   if c["category"] == "technical"
                   and c.get("must_admit_no_record"))
    assert beyan == ["t1_tech_002", "t1_tech_003", "t1_tech_004", "t1_tech_010"]


def test_invented_record_count_fails_grounding():
    """t1_tech_002: "ChromaDB'de 1.234.567 kayıt var." -- kayit yok, sayi uydurma."""
    s = puanla("ChromaDB'de 1.234.567 kayıt var.", {"must_admit_no_record": True})
    assert s["grounding_ok"] is False


def test_invented_policy_state_fails_grounding():
    """t1_tech_010: politika varsayilan KAPALI; "aktif" cevabi uydurma."""
    s = puanla("Evet, web araştırma politikası şu an aktif.",
               {"must_admit_no_record": True})
    assert s["grounding_ok"] is False


# --------------------------------------------------------------------------- #
# 11. Gecikme ve Turkce-esdeger cevrimi
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


# --------------------------------------------------------------------------- #
# 12. Taban kilidi — kayitli kosu, kayitli sayi
# --------------------------------------------------------------------------- #

def test_the_recorded_run_still_scores_49_of_64():
    """Puanlayici v2 + 2026-09-01 cevaplari = 49/64. Taban budur.

    Bu test bir REGRESYON KAPISI degil, bir SOZLESME kilididir: puanlamaya
    dokunan her degisiklik burada gorunur. Yeni bir dedektor eklemek ya da
    bir esigi oynatmak bu sayiyi degistirir -- o zaman sayi bilerek, kanitla
    ve `automation/KALITE_TABAN_*.md`'ye yazilarak guncellenir. Sessizce
    kaymasi yasak (CLAUDE.md 13.1).

    Cevaplar sabit ve repoda kayitli oldugu icin modelin oynakligi (A11) bu
    olcume karismaz: burada olculen model degil, PUANLAYICI.
    """
    from eval.quality_scorer import score_answer

    kosu = json.loads(_CANLI_KOSU.read_text(encoding="utf-8"))
    vakalar = {c["id"]: c
               for c in json.loads(_VAKALAR.read_text(encoding="utf-8"))["cases"]}
    gecen = sum(1 for r in kosu["results"]
                if score_answer(r.get("answer") or "", vakalar[r["id"]])["passed"])
    assert gecen == 49


def test_passing_threshold_block_records_a_baseline_not_a_target():
    """A14, 2026-09-04, Ahmet: hedef sayi YAZILMAZ, alan taban kaydi olur.

    Blogu hicbir Python kodu okumuyor; insan icin bir yorum. Eski hedefleri
    (`">=57/64"`) yeni hedeflerle degistirmek "sayiyi tutturmaya oynama"
    baskisini geri getirirdi. Bu yuzden hedef sozdizimi hic kalmaz: blok
    yalnizca OLCULMUS tabani tasir.
    """
    blok = json.loads(_VAKALAR.read_text(encoding="utf-8"))["passing_threshold"]
    hedefler = sorted(k for k, v in blok.items() if ">=" in str(v))
    assert hedefler == [], f"hedef sozdizimi kalmis: {hedefler}"
    assert "49/64" in blok["overall_v2"]
