"""C1.6H-4 Telegram knowledge card commands tests."""
from __future__ import annotations


def test_kc_add_requires_args():
    from tools.telegram_agent import cmd_kc_add
    result = cmd_kc_add("/kc_add")
    assert "Kullanim" in result


def test_kc_list_returns_string():
    from tools.telegram_agent import cmd_kc_list
    result = cmd_kc_list()
    assert isinstance(result, str)
    assert len(result) > 0


def test_kc_approve_requires_id():
    from tools.telegram_agent import cmd_kc_approve
    result = cmd_kc_approve("/kc_approve")
    assert "Kullanim" in result


def test_kc_promote_requires_id():
    from tools.telegram_agent import cmd_kc_promote
    result = cmd_kc_promote("/kc_promote")
    assert "Kullanim" in result


def test_kc_add_creates_card(monkeypatch, tmp_path):
    import agents.knowledge_card_store as store_mod
    import agents.answer_crystallizer as cr_mod
    from agents.knowledge_card_store import KnowledgeCardStore
    from agents.answer_crystallizer import AnswerCrystallizer

    store = KnowledgeCardStore(data_root=tmp_path)
    monkeypatch.setattr(store_mod, "KnowledgeCardStore", lambda **kw: store)
    monkeypatch.setattr(cr_mod, "AnswerCrystallizer", lambda **kw: AnswerCrystallizer(store=store))

    from tools.telegram_agent import cmd_kc_add
    result = cmd_kc_add("/kc_add soru: RTX 3070 kac watt? | cevap: 220W TDP. | model: claude-opus-4")
    assert "olusturuldu" in result.lower() or "kc_" in result


def test_kc_approve_success(monkeypatch, tmp_path):
    from agents.knowledge_card_store import KnowledgeCardStore
    import agents.knowledge_card_store as store_mod

    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(question="Soru?", answer="Cevap.", source_model="m")
    monkeypatch.setattr(store_mod, "KnowledgeCardStore", lambda **kw: store)

    from tools.telegram_agent import cmd_kc_approve
    result = cmd_kc_approve(f"/kc_approve {card['id']}")
    assert "onaylandi" in result.lower() or card["id"] in result


def test_kc_promote_not_approved(monkeypatch, tmp_path):
    from agents.knowledge_card_store import KnowledgeCardStore
    from agents.knowledge_card_promoter import KnowledgeCardPromoter
    import agents.knowledge_card_store as store_mod
    import agents.knowledge_card_promoter as promoter_mod

    store = KnowledgeCardStore(data_root=tmp_path)
    card = store.add(question="Soru?", answer="Cevap.", source_model="m")
    monkeypatch.setattr(store_mod, "KnowledgeCardStore", lambda **kw: store)
    monkeypatch.setattr(promoter_mod, "KnowledgeCardPromoter", lambda **kw: KnowledgeCardPromoter(store=store))

    from tools.telegram_agent import cmd_kc_promote
    result = cmd_kc_promote(f"/kc_promote {card['id']}")
    assert "not_approved" in result or "onaylandi" not in result.lower()
