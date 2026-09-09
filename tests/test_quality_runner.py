"""eval/run_turkish_quality.py — kosucu sozlesmesi.

Kosucu, YAVAS ve donanima bagli olan tek parcadir; bu yuzden model cagrisi,
VRAM olcumu ve hafiza grafigi enjekte edilebilir. Boylece kosucunun MANTIGI
(vaka secimi, zemin enjeksiyonu, toplama, cikti bicimi) Ollama olmadan test
edilir -- puanlayicida ve voice/stt.py'de yaptigimiz ayrimin aynisi.
"""
from __future__ import annotations

import json

import pytest


VAKALAR = {
    "schema_version": 2,
    "cases": [
        {"id": "g1", "category": "grounding", "prompt": "Geçen hafta ne konuştuk?",
         "seed_memory": {}, "must_admit_no_record": True},
        {"id": "m1", "category": "memory", "prompt": "Eşimin adı ne?",
         "seed_memory": {"es": {"ad": "Dilara"}},
         "must_contain_any": [["Dilara"]], "expect_efendim": True},
        {"id": "l1", "category": "longform", "prompt": "Uzun anlat.",
         "seed_memory": {}, "min_chars": 50},
    ],
}


def kosucu():
    from eval.run_turkish_quality import run_suite

    return run_suite


def sahte_ask(cevaplar):
    """id -> cevap eslemesinden bir model sahtesi kurar; cagrilari kaydeder.

    `num_predict` sozlesmeye 2026-09-05'te eklendi (kart: terazinin uc
    kusuru): kesilmelerin hepsi butce sinirindan geliyordu, bu yuzden butce
    vaka basina ayarlanabilir oldu. Iddialar degismedi, imza genisledi.
    """
    gorulen = []

    def ask(model, prompt, level, system_extra=None, num_predict=None):
        gorulen.append({"model": model, "prompt": prompt, "level": level,
                        "system_extra": system_extra,
                        "num_predict": num_predict})
        return {"text": cevaplar.get(len(gorulen) - 1, "bos"),
                "raw_tps": 50.0, "first_token_ms": 40.0, "total_s": 1.0}

    ask.gorulen = gorulen
    return ask


# --------------------------------------------------------------------------- #
# 1. Temel akis
# --------------------------------------------------------------------------- #

def test_runs_every_case_once():
    ask = sahte_ask({})
    sonuc = kosucu()(VAKALAR["cases"], ask, model="test-model")
    assert len(sonuc["results"]) == 3
    assert len(ask.gorulen) == 3


def test_result_carries_case_id_and_category():
    sonuc = kosucu()(VAKALAR["cases"], sahte_ask({}), model="m")
    ilk = sonuc["results"][0]
    assert ilk["id"] == "g1"
    assert ilk["category"] == "grounding"
    assert "score" in ilk


def test_model_name_is_recorded():
    sonuc = kosucu()(VAKALAR["cases"], sahte_ask({}), model="qwen2.5:7b")
    assert sonuc["model"] == "qwen2.5:7b"


# --------------------------------------------------------------------------- #
# 2. Zemin enjeksiyonu — hafiza vakasi olgu GORMELI, zemin vakasi GORMEMELI
# --------------------------------------------------------------------------- #

def test_memory_case_receives_seeded_facts_as_grounding():
    ask = sahte_ask({})
    kosucu()(VAKALAR["cases"], ask, model="m")
    hafiza_cagrisi = ask.gorulen[1]
    assert "Dilara" in (hafiza_cagrisi["system_extra"] or ""), (
        "hafiza vakasi zemini gormeli, yoksa 'geri cagirma' testi degil"
    )


def test_grounding_case_receives_no_facts():
    """Kayit YOKKEN zemin bos olmali; doluysa test anlamsizlasir."""
    ask = sahte_ask({})
    kosucu()(VAKALAR["cases"], ask, model="m")
    assert not (ask.gorulen[0]["system_extra"] or "").strip()


def test_seeded_memory_does_not_leak_between_cases():
    """Bir vakanin olgusu digerine sizmamali -- her vaka izole."""
    ask = sahte_ask({})
    kosucu()(VAKALAR["cases"], ask, model="m")
    assert "Dilara" not in (ask.gorulen[2]["system_extra"] or "")


# --------------------------------------------------------------------------- #
# 3. Puanlama ve toplama
# --------------------------------------------------------------------------- #

def test_honest_answer_passes_grounding_case():
    ask = sahte_ask({0: "Efendim, bu bilgiye erişimim yok."})
    sonuc = kosucu()(VAKALAR["cases"], ask, model="m")
    assert sonuc["results"][0]["score"]["passed"] is True


def test_fabricated_answer_fails_grounding_case():
    ask = sahte_ask({0: "Geçen hafta telemetriyi konuştuk."})
    sonuc = kosucu()(VAKALAR["cases"], ask, model="m")
    g = sonuc["results"][0]
    assert g["score"]["passed"] is False
    assert "grounding" in g["score"]["failed_checks"]


def test_summary_aggregates_per_category():
    ask = sahte_ask({0: "Efendim, erişimim yok.",
                     1: "Efendim, eşinizin adı Dilara.",
                     2: "kısa"})
    s = kosucu()(VAKALAR["cases"], ask, model="m")["summary"]
    assert s["by_category"]["grounding"] == {"passed": 1, "total": 1}
    assert s["by_category"]["memory"] == {"passed": 1, "total": 1}
    assert s["by_category"]["longform"] == {"passed": 0, "total": 1}
    assert s["passed"] == 2 and s["total"] == 3


def test_latency_is_aggregated_with_turkish_equivalent():
    s = kosucu()(VAKALAR["cases"], sahte_ask({}), model="m")["summary"]
    assert s["avg_raw_tps"] == pytest.approx(50.0)
    assert s["avg_turkish_tps"] == pytest.approx(50.0 / 1.9, abs=0.1)


# --------------------------------------------------------------------------- #
# 4. VRAM — olculmediyse UYDURULMAZ
# --------------------------------------------------------------------------- #

def test_vram_absent_when_no_probe_given():
    s = kosucu()(VAKALAR["cases"], sahte_ask({}), model="m")["summary"]
    assert s["peak_vram_mb"] is None
    assert s["exceeds_vram_ceiling"] is None


def test_vram_ceiling_flag_when_probe_given():
    s = kosucu()(VAKALAR["cases"], sahte_ask({}), model="m",
                 gpu_probe=lambda: 6880)["summary"]
    assert s["peak_vram_mb"] == 6880
    assert s["exceeds_vram_ceiling"] is True


# --------------------------------------------------------------------------- #
# 5. Dayaniklilik — bir vaka patlarsa kosu durmaz
# --------------------------------------------------------------------------- #

def test_model_error_is_recorded_not_raised():
    def patlayan(model, prompt, level, system_extra=None, num_predict=None):
        raise RuntimeError("ollama kapali")

    sonuc = kosucu()(VAKALAR["cases"], patlayan, model="m")
    assert len(sonuc["results"]) == 3
    assert all(r["error"] for r in sonuc["results"])
    assert sonuc["summary"]["passed"] == 0


def test_partial_failure_still_scores_the_rest():
    cagri = {"n": 0}

    def bazen(model, prompt, level, system_extra=None, num_predict=None):
        cagri["n"] += 1
        if cagri["n"] == 1:
            raise RuntimeError("gecici hata")
        return {"text": "Efendim, eşinizin adı Dilara.", "raw_tps": 40.0,
                "first_token_ms": 30.0, "total_s": 1.0}

    sonuc = kosucu()(VAKALAR["cases"], bazen, model="m")
    assert sonuc["results"][0]["error"]
    assert sonuc["results"][1]["score"]["passed"] is True


# --------------------------------------------------------------------------- #
# 6. Makine okunur cikti — sonraki kosuyla karsilastirilabilmeli
# --------------------------------------------------------------------------- #

def test_report_is_json_serialisable_and_versioned(tmp_path):
    from eval.run_turkish_quality import write_report

    sonuc = kosucu()(VAKALAR["cases"], sahte_ask({}), model="m")
    yollar = write_report(sonuc, out_dir=tmp_path, stamp="20260901-1200")

    veri = json.loads(yollar["json"].read_text(encoding="utf-8"))
    assert veri["schema_version"] >= 1
    assert veri["model"] == "m"
    assert len(veri["results"]) == 3
    assert yollar["markdown"].exists()
    assert "20260901-1200" in yollar["json"].name


def test_markdown_report_names_failing_cases(tmp_path):
    from eval.run_turkish_quality import write_report

    ask = sahte_ask({0: "Geçen hafta telemetriyi konuştuk."})
    sonuc = kosucu()(VAKALAR["cases"], ask, model="m")
    yollar = write_report(sonuc, out_dir=tmp_path, stamp="x")
    metin = yollar["markdown"].read_text(encoding="utf-8")
    assert "g1" in metin, "kalan vaka raporda adiyla gecmeli"
    assert "grounding" in metin


# --------------------------------------------------------------------------- #
# 7. Kusur 2 — butce: kesilmenin sebebi TAHMIN degil OLCUM olmali
# --------------------------------------------------------------------------- #
#
# Kiyas kosusundaki 10 kesilmenin hepsi `num_predict=400` sinirina carpmisti
# (`automation/MODEL_KIYASI_2026-09-04.md` §4b). "longform 0/4"u model
# dejenerasyonu diye okumak bu yuzden yanlisti. Iki duzeltme: sebep olculur
# (`done_reason`) ve uzun anlatim vakasi hak ettigi butceyi alir.

def test_done_reason_is_recorded():
    """Ollama'nin `done_reason`'i sonuca yazilir: 'length' butce, 'stop' model."""
    def ask(model, prompt, level, system_extra=None, num_predict=None):
        return {"text": "bir cevap", "raw_tps": 50.0, "first_token_ms": 40.0,
                "total_s": 1.0, "done_reason": "length"}

    sonuc = kosucu()(VAKALAR["cases"], ask, model="m")
    assert all(r["done_reason"] == "length" for r in sonuc["results"])
    assert sonuc["summary"]["budget_exhausted"] == 3


def test_done_reason_is_none_when_the_runner_does_not_report_it():
    """Olculmediyse UYDURULMAZ -- `peak_vram_mb` ile ayni disiplin."""
    sonuc = kosucu()(VAKALAR["cases"], sahte_ask({}), model="m")
    assert all(r["done_reason"] is None for r in sonuc["results"])
    assert sonuc["summary"]["budget_exhausted"] == 0


def test_longform_case_receives_its_declared_budget():
    """Vaka `num_predict` beyan ederse o gecer; etmezse varsayilan."""
    from eval.run_turkish_quality import DEFAULT_NUM_PREDICT

    vakalar = [dict(VAKALAR["cases"][2], num_predict=1200), VAKALAR["cases"][0]]
    gorulen = []

    def ask(model, prompt, level, system_extra=None, num_predict=None):
        gorulen.append(num_predict)
        return {"text": "x", "raw_tps": 1.0, "first_token_ms": 1.0, "total_s": 1.0}

    kosucu()(vakalar, ask, model="m")
    assert gorulen == [1200, DEFAULT_NUM_PREDICT]


def test_only_longform_cases_declare_a_larger_budget():
    """Cerrahi degisiklik (§3): 60 vakanin kosulu hic degismez.

    Butce 1200 -> 4000 (2026-09-10). Bu bir OLCUM TANIMI degisikligidir ve
    Ahmet'in imzasiyla yapildi (`KART_DEEPSEEK_10_KUSUR.md` PARCA B, imza
    2026-09-09; kosul: llama3.1 de ayni tanimla yeniden kosulur).

    Sayi tahminle secilmedi: 1200'de dort vakanin dordu de
    `done_reason="length"` ile kesiliyordu; 4000'de dordu de `"stop"` ile
    bitti ve en uzun cevap 2977 cikis tokeni tuttu. Olcum:
    `automation/TERAZI_ETAP1_2026-09-10.md` §1.

    Testin KORUDUGU sozlesme degismedi: butceyi yalniz longform beyan eder,
    diger 60 vaka varsayilanda kalir.
    """
    from pathlib import Path

    from eval.run_turkish_quality import CASES_PATH, DEFAULT_NUM_PREDICT

    veri = json.loads(Path(CASES_PATH).read_text(encoding="utf-8"))
    beyan = {c["id"]: c["num_predict"] for c in veri["cases"] if "num_predict" in c}
    assert sorted(beyan) == ["t2_longform_001", "t2_longform_002",
                             "t2_longform_003", "t2_longform_004"]
    assert set(beyan.values()) == {4000}
    assert DEFAULT_NUM_PREDICT == 400


def test_report_separates_budget_stops_from_model_stops(tmp_path):
    from eval.run_turkish_quality import write_report

    def ask(model, prompt, level, system_extra=None, num_predict=None):
        return {"text": "x" * 300, "raw_tps": 50.0, "first_token_ms": 40.0,
                "total_s": 1.0, "done_reason": "length"}

    sonuc = kosucu()(VAKALAR["cases"], ask, model="m")
    metin = write_report(sonuc, out_dir=tmp_path,
                         stamp="y")["markdown"].read_text(encoding="utf-8")
    assert "done_reason=length" in metin, (
        "kesilmenin sebebi raporda ayri gosterilmeli, yoksa tahmin kalir"
    )
