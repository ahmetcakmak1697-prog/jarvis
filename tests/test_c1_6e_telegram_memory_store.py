"""C1.6E-2B Telegram /mem_store command tests."""

from __future__ import annotations


def test_mem_store_requires_candidate_id():
    from tools.telegram_agent import cmd_memory_candidate_store

    result = cmd_memory_candidate_store("/mem_store")

    assert result == "Kullanim: /mem_store <candidate_id>"


def test_mem_store_rejects_missing_candidate(monkeypatch):
    from tools.telegram_agent import cmd_memory_candidate_store
    import agents.memory_candidate_queue as queue_mod

    class FakeQueue:
        def get(self, candidate_id: str):
            assert candidate_id == "mc_missing"
            return None

    monkeypatch.setattr(queue_mod, "MemoryCandidateQueue", FakeQueue)

    result = cmd_memory_candidate_store("/mem_store mc_missing")

    assert "Islem basarisiz: candidate bulunamadi." in result
    assert "ID: mc_missing" in result


def test_mem_store_requires_approved_status(monkeypatch):
    from tools.telegram_agent import cmd_memory_candidate_store
    import agents.memory_candidate_queue as queue_mod

    class FakeQueue:
        def get(self, candidate_id: str):
            assert candidate_id == "mc_pending"
            return {
                "id": candidate_id,
                "status": "pending_review",
            }

    monkeypatch.setattr(queue_mod, "MemoryCandidateQueue", FakeQueue)

    result = cmd_memory_candidate_store("/mem_store mc_pending")

    assert "Hafiza adayi henuz uzun hafizaya yazilamaz." in result
    assert "ID: mc_pending" in result
    assert "Status: pending_review" in result
    assert "Once /mem_approve <id> ile onaylayin." in result


def test_mem_store_reports_stored_when_writer_stores(monkeypatch):
    from tools.telegram_agent import cmd_memory_candidate_store
    import agents.memory_candidate_queue as queue_mod
    import agents.memory_candidate_writer as writer_mod

    class FakeQueue:
        def get(self, candidate_id: str):
            assert candidate_id == "mc_approved"
            return {
                "id": candidate_id,
                "status": "approved",
            }

    class FakeWriter:
        def approve_and_store(self, candidate_id: str):
            assert candidate_id == "mc_approved"
            return {
                "ok": True,
                "stored": True,
                "candidate_id": candidate_id,
                "status": "stored",
                "policy": {"action": "keep_long_term"},
            }

    monkeypatch.setattr(queue_mod, "MemoryCandidateQueue", FakeQueue)
    monkeypatch.setattr(writer_mod, "MemoryCandidateWriter", FakeWriter)

    result = cmd_memory_candidate_store("/mem_store mc_approved")

    assert "Hafiza adayi uzun hafizaya yazildi." in result
    assert "ID: mc_approved" in result
    assert "Status: stored" in result
    assert "Policy: keep_long_term" in result


def test_mem_store_reports_not_stored_when_writer_blocks(monkeypatch):
    from tools.telegram_agent import cmd_memory_candidate_store
    import agents.memory_candidate_queue as queue_mod
    import agents.memory_candidate_writer as writer_mod

    class FakeQueue:
        def get(self, candidate_id: str):
            assert candidate_id == "mc_synthesis"
            return {
                "id": candidate_id,
                "status": "approved",
                "source_type": "synthesis",
                "storage_target": "review_queue",
            }

    class FakeWriter:
        def approve_and_store(self, candidate_id: str):
            assert candidate_id == "mc_synthesis"
            return {
                "ok": False,
                "stored": False,
                "candidate_id": candidate_id,
                "error": "C1 route vector yazimina izin vermedi.",
            }

    monkeypatch.setattr(queue_mod, "MemoryCandidateQueue", FakeQueue)
    monkeypatch.setattr(writer_mod, "MemoryCandidateWriter", FakeWriter)

    result = cmd_memory_candidate_store("/mem_store mc_synthesis")

    assert "Hafiza adayi uzun hafizaya yazilmadi." in result
    assert "ID: mc_synthesis" in result
    assert "Neden: C1 route vector yazimina izin vermedi." in result
