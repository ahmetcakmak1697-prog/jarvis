"""Regression guard: LocalJarvisAgent must not hallucinate project state.

Tests verify:
1. The prompt actually sent to the model forbids invented project facts.
2. That prompt uses correct Turkish ('erisimim yok', not 'erisimi yok').
3. _load_project_context() always returns a non-empty structured block.
4. _load_project_context() includes git log lines when subprocess returns data.
5. _load_project_context() extracts pending items from HUMAN_NEEDED.md.
6. _load_project_context() reports live state from roadmap_state.json.
7. chat() injects project context into the system prompt.
8. chat() with empty project context does not inject placeholder section.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent_no_ollama(project_ctx: str = "GUNCEL PROJE DURUMU"):
    """Build a LocalJarvisAgent with Ollama and memory stubbed out."""
    with (
        patch("agent.local_agent.LocalJarvisAgent._init_ollama"),
        patch("agent.local_agent.LocalJarvisAgent._load_memory", return_value=None),
        patch("agent.local_agent.LocalJarvisAgent._load_tools", return_value={}),
        patch("agent.local_agent.LocalJarvisAgent._load_project_context", return_value=project_ctx),
        patch("memory.memory_manager.JarvisMemory", return_value=MagicMock(get_context_for_prompt=lambda: "")),
    ):
        from agent.local_agent import LocalJarvisAgent
        agent = LocalJarvisAgent()
        agent.ollama_available = True
        agent.available_models = ["llama3.2:latest"]
        return agent


def _captured_system_prompt(agent, message: str = "Nerede kaldik?") -> str:
    """chat()'in modele FIILEN gonderdigi system prompt'u yakalar.

    Prompt artik tek bir modul sabitinden gelmiyor: kimlik/sadakat/uslup/zemin
    `agents/persona.py` (SSOT) uzerinden, arac ve proje-durumu kurallari
    `LOCAL_AGENT_ADDENDUM` uzerinden, olgular ise `_load_project_context()`
    uzerinden birlesir. Sozlesme bu parcalarin herhangi birinde degil,
    BIRLESIMINDE tutulur -- modelin gordugu sey odur.
    """
    captured: list = []

    def fake_ask_ollama(messages, model):
        captured.extend(messages)
        return "Test yaniti."

    agent._ask_ollama = fake_ask_ollama
    with patch("rich.console.Console.status"):
        agent.chat(message)

    assert captured, "chat() _ask_ollama'yi cagirmadi"
    return captured[0]["content"]


def _gercek_loader(root: Path) -> str:
    """GERCEK `_load_project_context()`'i cagirir -- replika DEGIL.

    Eskiden burada metodun bir KOPYASI vardi ve `patch.object` ile gercegin
    yerine geciyordu; dort test gercek kodu degil o kopyayi olcuyordu ve kopya
    zaten sapmisti (gercekteki T1_S2_FAIL_LOG okumasini ve "Onemli Kural"
    blogunu icermiyordu). Metot artik test icin `root` parametresi aldigi
    icin replikaya gerek yok.

    Yalniz `subprocess.run` sahtelenir: git log'un cikti bicimi test edilir,
    bu makinenin gercek commit gecmisi degil.
    """
    fake_log = "\n".join([
        "abc1234 fix(local-agent): ground project-status answers",
        "def5678 fix(cli): prevent rich markup crash",
    ])
    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = fake_log

    with patch("subprocess.run", return_value=fake_result):
        from agent.local_agent import LocalJarvisAgent
        agent = LocalJarvisAgent.__new__(LocalJarvisAgent)
        return agent._load_project_context(root=root)


# ---------------------------------------------------------------------------
# Test 1: SYSTEM_PROMPT grounding rule is present
# ---------------------------------------------------------------------------

def test_system_prompt_contains_grounding_rule():
    """Uydurma yasagi modele giden prompt'ta bulunmali.

    Kural artik iki kaynaktan gelir: `agents/persona.py`'nin GERCEKLIK KURALI
    blogu ("Bilmedigin seyi uydurmazsin") ve `LOCAL_AGENT_ADDENDUM`'un PROJE
    DURUMU bolumu. Test modul sabitine degil kompoze prompt'a bakar; modelin
    gordugu sey odur ve sozlesme orada tutulur.
    """
    system = _captured_system_prompt(_make_agent_no_ollama())

    assert "uydurma" in system, "uydurma yasagi modele giden prompt'ta yok"
    assert "PROJE DURUMU" in system, "proje durumu zemin bolumu yok"
    assert "erişimim yok" in system, "kayit yoksa ne denecegi yazili degil"


# ---------------------------------------------------------------------------
# Test 2: SYSTEM_PROMPT uses correct Turkish grammar
# ---------------------------------------------------------------------------

def test_system_prompt_turkish_grammar():
    """Birinci tekil iyelik: "erişimim yok", "erişimi yok" degil.

    Ayrica ASCII'ye indirgenmis Turkce geri gelmemeli: persona SSOT calismasi
    tam olarak bunu duzeltti -- model kendi dil kuralini okunamaz bir cumleden
    ogreniyordu (bkz. tests/test_persona_ssot.py).

    Not: eski surum ayrica prompt'ta "zamanlayici" kelimesini sart kosuyordu.
    O iddia, artik yanlis olan bir OLGUYA bagliydi ("Zamanlayici henuz
    tasarlanmadi"); roadmap_state.json'da E1-S5 karari APPROVED ve E1-S6A-E
    adimlari done. Olgular prompt'a sabit yazilmaz, _load_project_context()
    ile canli dosyalardan gelir -- bu yuzden iddia dusuruldu.
    """
    system = _captured_system_prompt(_make_agent_no_ollama())

    assert "erişimim yok" in system, (
        "prompt 'erişimim yok' (birinci tekil iyelik) kullanmali"
    )
    assert "erişimi yok" not in system, (
        "ucuncu tekil 'erişimi yok' yanlis: JARVIS kendinden bahsediyor"
    )

    from tests.test_persona_ssot import corrupted_fragments
    bozuk = corrupted_fragments(system)
    assert not bozuk, f"modele giden prompt'ta bozuk kodlama: {bozuk}"


# ---------------------------------------------------------------------------
# Test 3: _load_project_context always returns a non-empty structured block
# ---------------------------------------------------------------------------

def test_load_project_context_always_returns_nonempty(tmp_path):
    result = _gercek_loader(tmp_path)
    assert result.strip(), "Project context block must never be empty"
    assert "GUNCEL PROJE DURUMU" in result, "Block must start with GUNCEL PROJE DURUMU header"


# ---------------------------------------------------------------------------
# Test 4: _load_project_context includes git log lines when subprocess returns data
# ---------------------------------------------------------------------------

def test_load_project_context_includes_git_log(tmp_path):
    result = _gercek_loader(tmp_path)
    assert "abc1234" in result or "Son Commitler" in result, (
        f"Git log lines must appear in project context. Got:\n{result[:500]}"
    )


# ---------------------------------------------------------------------------
# Test 5: _load_project_context extracts pending items from HUMAN_NEEDED.md
# ---------------------------------------------------------------------------

def test_load_project_context_extracts_human_needed(tmp_path):
    auto = tmp_path / "automation"
    auto.mkdir()
    (auto / "HUMAN_NEEDED.md").write_text(
        "## Pending\n- [ ] [2026-06-24] [T1-S2] Turkish sign-off\n- [ ] [2026-06-24] [E1-S4] Telegram\n",
        encoding="utf-8",
    )
    result = _gercek_loader(tmp_path)
    assert "T1-S2" in result, "Pending HUMAN_NEEDED items must appear in project context"
    assert "E1-S4" in result, "All pending items must appear in project context"


# ---------------------------------------------------------------------------
# Test 6: _load_project_context always includes hardcoded known-state facts
# ---------------------------------------------------------------------------

def test_load_project_context_includes_known_state(tmp_path):
    """SOZLESME DEGISTI (2026-09-01, Ahmet onayi).

    Eski iddia sabit yazilmis "BEKLIYOR" satirlarini kilitliyordu; o olgular
    artik YANLIS (roadmap_state.json: E1-S4 DONE 2026-06-27, E1-S5 APPROVED).
    Yanlis olgu sabitleyen bir test, kodu yanlis tutmaya zorlar.

    Yeni iddia: blok CANLI kaynaktan beslenir ve calisma modunu bildirir.
    Ayrintili kapsam: tests/test_project_context_dynamic.py
    """
    import json

    (tmp_path / "roadmap_state.json").write_text(json.dumps({
        "steps": [
            {"id": "FAZ-0", "title": "Temel", "status": "done", "evidence": {}},
            {"id": "FAZ-3-E1", "title": "Proaktif teslimat",
             "status": "in_progress",
             "evidence": {"e1_s4": {"verdict": "DONE", "date": "2026-06-27"}}},
        ]
    }, ensure_ascii=False), encoding="utf-8")

    result = _gercek_loader(tmp_path)
    assert "Proaktif bildirimler: CANLI DEGIL" in result, "Must state proactive is disabled"
    assert "FAZ-3-E1" in result, "Devam eden adim canli dosyadan gelmeli"
    assert "DONE" in result, "Kanit verdict'i canli dosyadan gelmeli"
    assert "BEKLIYOR" not in result, "Sabit yazilmis eskimis durum geri gelmis"


# ---------------------------------------------------------------------------
# Test 7: chat() injects project context into the system prompt
# ---------------------------------------------------------------------------

def test_chat_injects_project_context_into_system_prompt():
    injected_ctx = "## GUNCEL PROJE DURUMU\n### Bilinen Durum\n  - T1-S2: BEKLIYOR\n  - E1-S4: BEKLIYOR"
    agent = _make_agent_no_ollama(project_ctx=injected_ctx)

    captured_messages: list = []

    def fake_ask_ollama(messages, model):
        captured_messages.extend(messages)
        return "Test yaniti."

    agent._ask_ollama = fake_ask_ollama

    with patch("rich.console.Console.status"):
        agent.chat("Nerede kaldik?")

    assert captured_messages, "No messages captured — chat() did not call _ask_ollama"
    system_content = captured_messages[0]["content"]
    assert "T1-S2" in system_content, (
        f"Project context not injected into system prompt. System:\n{system_content[:500]}"
    )
    assert "GUNCEL PROJE DURUMU" in system_content, "Project state section header missing"


# ---------------------------------------------------------------------------
# Test 8: chat() with empty project context does not inject placeholder section
# ---------------------------------------------------------------------------

def test_chat_no_project_context_does_not_inject_empty_section():
    agent = _make_agent_no_ollama(project_ctx="")

    captured_messages: list = []

    def fake_ask_ollama(messages, model):
        captured_messages.extend(messages)
        return "Test yaniti."

    agent._ask_ollama = fake_ask_ollama

    with patch("rich.console.Console.status"):
        agent.chat("Merhaba")

    system_content = captured_messages[0]["content"]
    assert "## GUNCEL PROJE DURUMU" not in system_content, (
        "Empty project context should not inject the dynamic GUNCEL PROJE DURUMU section"
    )
