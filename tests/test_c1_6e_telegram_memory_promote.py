from tools import telegram_agent


class FakePromoterSuccess:
    def promote(self, candidate_id):
        return {
            "ok": True,
            "promoted": True,
            "reason": "promoted",
            "candidate_id": candidate_id,
            "vector_doc_id": "vec_promote_001",
            "queue": {"ok": True},
        }


class FakePromoterFailure:
    def __init__(self, reason="candidate_not_approved"):
        self.reason = reason

    def promote(self, candidate_id):
        return {
            "ok": False,
            "promoted": False,
            "reason": self.reason,
            "candidate_id": candidate_id,
        }


def test_mem_promote_requires_candidate_id():
    result = telegram_agent.cmd_memory_candidate_promote("/mem_promote")

    assert result == "Kullanim: /mem_promote <candidate_id>"


def test_mem_promote_success(monkeypatch):
    monkeypatch.setattr(
        telegram_agent,
        "MemorySynthesisPromoter",
        lambda: FakePromoterSuccess(),
        raising=False,
    )

    result = telegram_agent.cmd_memory_candidate_promote("/mem_promote cand_001")

    assert "Sentez hafiza adayi uzun hafizaya yazildi." in result
    assert "ID: cand_001" in result
    assert "Status: stored" in result
    assert "Vector ID: vec_promote_001" in result


def test_mem_promote_failure(monkeypatch):
    monkeypatch.setattr(
        telegram_agent,
        "MemorySynthesisPromoter",
        lambda: FakePromoterFailure("candidate_not_approved"),
        raising=False,
    )

    result = telegram_agent.cmd_memory_candidate_promote("/mem_promote cand_002")

    assert "Sentez hafiza adayi uzun hafizaya yazilmadi." in result
    assert "ID: cand_002" in result
    assert "Sebep: candidate_not_approved" in result


def test_mem_promote_vector_failure(monkeypatch):
    monkeypatch.setattr(
        telegram_agent,
        "MemorySynthesisPromoter",
        lambda: FakePromoterFailure("vector_write_failed"),
        raising=False,
    )

    result = telegram_agent.cmd_memory_candidate_promote("/mem_promote cand_003")

    assert "Sentez hafiza adayi uzun hafizaya yazilmadi." in result
    assert "Sebep: vector_write_failed" in result
