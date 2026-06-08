"""C1.6E-2A Telegram memory approve command behavior lock tests."""

from __future__ import annotations


def test_mem_approve_reports_stored_when_writer_stores(monkeypatch):
    from tools.telegram_agent import cmd_memory_candidate_decide
    import agents.memory_candidate_writer as writer_mod

    class FakeWriter:
        def approve_and_store(self, candidate_id: str):
            assert candidate_id == "mc_safe"
            return {
                "ok": True,
                "stored": True,
                "candidate_id": candidate_id,
                "status": "stored",
                "policy": {"action": "keep_long_term"},
            }

    monkeypatch.setattr(writer_mod, "MemoryCandidateWriter", FakeWriter)

    result = cmd_memory_candidate_decide("/mem_approve mc_safe", "approve")

    assert "Hafiza adayi onaylandi ve uzun hafizaya yazildi." in result
    assert "ID: mc_safe" in result
    assert "Status: stored" in result
    assert "Policy: keep_long_term" in result


def test_mem_approve_reports_not_stored_when_writer_blocks_synthesis(monkeypatch):
    from tools.telegram_agent import cmd_memory_candidate_decide
    import agents.memory_candidate_writer as writer_mod

    class FakeWriter:
        def approve_and_store(self, candidate_id: str):
            assert candidate_id == "mc_synthesis"
            return {
                "ok": False,
                "stored": False,
                "candidate_id": candidate_id,
                "error": "C1 route vector yazimina izin vermedi.",
                "policy": {
                    "memory_type": "semantic",
                    "storage_target": "review_queue",
                    "requires_review": True,
                },
            }

    monkeypatch.setattr(writer_mod, "MemoryCandidateWriter", FakeWriter)

    result = cmd_memory_candidate_decide("/mem_approve mc_synthesis", "approve")

    assert "Hafiza adayi onaylandi fakat uzun hafizaya yazilmadi." in result
    assert "ID: mc_synthesis" in result
    assert "Neden: C1 route vector yazimina izin vermedi." in result
    assert "Guvenlik/policy nedeniyle otomatik yazim engellenmis olabilir." in result


def test_mem_approve_requires_candidate_id():
    from tools.telegram_agent import cmd_memory_candidate_decide

    result = cmd_memory_candidate_decide("/mem_approve", "approve")

    assert result == "Kullanim: /mem_approve <candidate_id>"
