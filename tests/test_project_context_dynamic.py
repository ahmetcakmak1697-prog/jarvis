"""_load_project_context() — proje durumu CANLI dosyadan gelmeli.

Neden: durum blogu koda SABIT yazilmisti ve uc satiri artik yanlisti
(E1-S4 "BEKLIYOR" ama roadmap_state.json'da DONE 2026-06-27; E1-S5
"henuz kod yok" ama APPROVED). Model bu tabloyu her turda goruyor ve canli
testte "tasarim asamasindayiz" dedi — halusinasyon degil, eskimis veriyi
sadakatle tekrar etmesi. Olgu koda yazilirsa eskir.

Bu testler GERCEK fonksiyonu cagirir. Onceki test dosyasindaki
`_call_real_loader()` yardimcisi, `patch.object` ile gercek metodu testin
icine yazilmis bir REPLIKA ile degistiriyordu; dort test gercek kodu degil
kopyayi olcuyordu ve kopya zaten sapmisti (gercekteki T1_S2_FAIL_LOG
okumasini ve "Onemli Kural" blogunu icermiyordu).
"""
from __future__ import annotations

import json

import pytest


@pytest.fixture()
def ajan():
    from agent.local_agent import LocalJarvisAgent

    return LocalJarvisAgent.__new__(LocalJarvisAgent)


def roadmap_yaz(kok, steps):
    (kok / "roadmap_state.json").write_text(
        json.dumps({"version": 1, "project": "jarvis", "steps": steps},
                   ensure_ascii=False),
        encoding="utf-8",
    )


ORNEK_STEPS = [
    {"id": "FAZ-0", "title": "Temel sistem", "status": "done", "evidence": {}},
    {"id": "FAZ-3-E1", "title": "Proaktif teslimat", "status": "in_progress",
     "evidence": {"e1_s4": {"verdict": "DONE", "date": "2026-06-27"},
                  "e1_s5_decision": {"verdict": "APPROVED"}}},
    {"id": "FAZ-9-X", "title": "Gelecek is", "status": "pending", "evidence": {}},
]


# --------------------------------------------------------------------------- #
# 1. Eskimis SABIT olgular gitmis olmali
# --------------------------------------------------------------------------- #

def test_no_hardcoded_status_lines_in_source():
    """Olgu koda yazilmaz. Kaynakta sabit durum satiri kalmamali."""
    from pathlib import Path

    kaynak = (Path(__file__).resolve().parents[1]
              / "agent" / "local_agent.py").read_text(encoding="utf-8")
    for eskimis in ("E1-S4: Canli Telegram smoke testi",
                    "E1-S5: Zamanlayici mimari karari",
                    "T1-S2: Turkce kalite subjektif onayi"):
        assert eskimis not in kaynak, (
            f"sabit yazilmis durum satiri hala kodda: {eskimis!r}"
        )


def test_context_does_not_claim_e1s4_is_pending(ajan, tmp_path):
    roadmap_yaz(tmp_path, ORNEK_STEPS)
    blok = ajan._load_project_context(root=tmp_path)
    assert "E1-S4" not in blok or "BEKLIYOR" not in blok


# --------------------------------------------------------------------------- #
# 2. Durum roadmap_state.json'dan gelmeli
# --------------------------------------------------------------------------- #

def test_in_progress_step_is_reported(ajan, tmp_path):
    roadmap_yaz(tmp_path, ORNEK_STEPS)
    blok = ajan._load_project_context(root=tmp_path)
    assert "FAZ-3-E1" in blok
    assert "Proaktif teslimat" in blok


def test_evidence_verdicts_are_reported(ajan, tmp_path):
    roadmap_yaz(tmp_path, ORNEK_STEPS)
    blok = ajan._load_project_context(root=tmp_path)
    assert "e1_s4" in blok and "DONE" in blok
    assert "e1_s5_decision" in blok and "APPROVED" in blok


def test_step_counts_are_reported(ajan, tmp_path):
    roadmap_yaz(tmp_path, ORNEK_STEPS)
    blok = ajan._load_project_context(root=tmp_path)
    assert "1/3" in blok or "1 / 3" in blok, "tamamlanan/toplam sayisi yok"


def test_changing_the_file_changes_the_block(ajan, tmp_path):
    """Asil sozlesme: dosya degisince blok degisir. Sabit metin bunu yapamaz."""
    roadmap_yaz(tmp_path, ORNEK_STEPS)
    once = ajan._load_project_context(root=tmp_path)

    yeni = [dict(s) for s in ORNEK_STEPS]
    yeni[1]["status"] = "done"
    yeni[1]["evidence"] = {"e1_s4": {"verdict": "DONE"}}
    roadmap_yaz(tmp_path, yeni)
    sonra = ajan._load_project_context(root=tmp_path)

    assert once != sonra, "blok canli dosyayi yansitmiyor"


# --------------------------------------------------------------------------- #
# 3. Fail-safe: uydurma durum yerine HIC durum
# --------------------------------------------------------------------------- #

def test_missing_roadmap_file_omits_status_not_invents_it(ajan, tmp_path):
    blok = ajan._load_project_context(root=tmp_path)  # dosya yok
    assert "GUNCEL PROJE DURUMU" in blok, "blok tamamen kaybolmamali"
    for uydurma in ("DONE", "APPROVED", "in_progress", "BEKLIYOR"):
        assert uydurma not in blok, f"dosya yokken {uydurma!r} uydurulmus"


def test_corrupt_roadmap_file_is_survived(ajan, tmp_path):
    (tmp_path / "roadmap_state.json").write_text("{bozuk json", encoding="utf-8")
    blok = ajan._load_project_context(root=tmp_path)
    assert "GUNCEL PROJE DURUMU" in blok
    assert "BEKLIYOR" not in blok


def test_roadmap_without_steps_key_is_survived(ajan, tmp_path):
    (tmp_path / "roadmap_state.json").write_text(
        json.dumps({"version": 1}), encoding="utf-8")
    assert "GUNCEL PROJE DURUMU" in ajan._load_project_context(root=tmp_path)


# --------------------------------------------------------------------------- #
# 4. Korunmasi istenen iddialar
# --------------------------------------------------------------------------- #

def test_proactive_disabled_claim_is_read_live(ajan, tmp_path, monkeypatch):
    """JARVIS_PROACTIVE_ENABLED iddiasi korunur ama CANLI okunur."""
    roadmap_yaz(tmp_path, ORNEK_STEPS)

    monkeypatch.delenv("JARVIS_PROACTIVE_ENABLED", raising=False)
    assert "CANLI DEGIL" in ajan._load_project_context(root=tmp_path)

    monkeypatch.setenv("JARVIS_PROACTIVE_ENABLED", "1")
    assert "CANLI DEGIL" not in ajan._load_project_context(root=tmp_path)


def test_grounding_rule_survives(ajan, tmp_path):
    """'Bu blogun disini UYDURMA' kurali kaybolmamali."""
    roadmap_yaz(tmp_path, ORNEK_STEPS)
    assert "UYDURMA" in ajan._load_project_context(root=tmp_path)


def test_template_placeholder_is_not_reported_as_pending_work(ajan, tmp_path):
    """`HUMAN_NEEDED.md`'deki ornek satir gercek bir is DEGILDIR.

    Canli blokta gorulmustu: model, sablon yer tutucusunu bekleyen bir gorev
    sanip konusabilir.
    """
    (tmp_path / "automation").mkdir()
    (tmp_path / "automation" / "HUMAN_NEEDED.md").write_text(
        "- [ ] [YYYY-MM-DD] [TASK-ID] What is needed and exactly why.\n"
        "- [ ] [2026-06-24] [E1-S4] Gercek bekleyen is\n",
        encoding="utf-8",
    )
    roadmap_yaz(tmp_path, ORNEK_STEPS)
    blok = ajan._load_project_context(root=tmp_path)
    assert "YYYY-MM-DD" not in blok and "TASK-ID" not in blok
    assert "Gercek bekleyen is" in blok


def test_human_needed_pending_items_still_read(ajan, tmp_path):
    (tmp_path / "automation").mkdir()
    (tmp_path / "automation" / "HUMAN_NEEDED.md").write_text(
        "- [ ] bekleyen bir is\n- [x] biten is\n", encoding="utf-8")
    roadmap_yaz(tmp_path, ORNEK_STEPS)
    blok = ajan._load_project_context(root=tmp_path)
    assert "bekleyen bir is" in blok
    assert "biten is" not in blok
