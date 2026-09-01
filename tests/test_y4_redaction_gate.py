"""Y4 Redaction-before-external gate testleri."""
from __future__ import annotations


class FakeVectorMemory:
    def find_similar(self, *a, **kw):
        return []

class FakeLedgerAllow:
    def check_and_consume(self, *a, **kw):
        return {"allowed": True, "reason": "within_limit"}


def _router(tmp_path, redact=True):
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    store = KnowledgeCardStore(data_root=tmp_path)
    return LocalFirstRouter(
        kc_store=store,
        vector_memory=FakeVectorMemory(),
        cost_ledger=FakeLedgerAllow(),
        redact_before_external=redact,
    )


def test_normal_question_passes_through(tmp_path):
    r = _router(tmp_path)
    result = r.route("Jarvis projesi nasil calisuyor?")
    assert result["decision"] in ("ask_external", "answer_local")
    assert result["decision"] != "redacted_blocked"


def test_sensitive_question_blocked(tmp_path):
    r = _router(tmp_path)
    result = r.route("OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456 ile ne yapabilirim?")
    assert result["decision"] == "redacted_blocked"
    assert result["route"] == "redacted_blocked"


def test_email_in_question_blocked(tmp_path):
    r = _router(tmp_path)
    result = r.route("ahmet@example.com adresine nasil mail atarim?")
    assert result["decision"] == "redacted_blocked"


def test_redaction_disabled_passes_through(tmp_path):
    r = _router(tmp_path, redact=False)
    result = r.route("OPENAI_API_KEY=sk-test ile ne yapabilirim?")
    assert result["decision"] != "redacted_blocked"


def test_redacted_result_has_reason(tmp_path):
    r = _router(tmp_path)
    result = r.route("password=supersecret123 nedir?")
    if result["decision"] == "redacted_blocked":
        assert "reason" in result
        assert "redact" in result["reason"].lower() or "sensitive" in result["reason"].lower()
