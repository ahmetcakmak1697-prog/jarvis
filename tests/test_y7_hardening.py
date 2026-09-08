"""Y7 AssistantExecutor hardening + redaction-before-cost invariant."""
from __future__ import annotations
import tempfile
from pathlib import Path


class _BlockLedger:
    def check_and_consume(self, *a, **kw):
        return {"allowed": False, "reason": "daily_limit_exceeded"}


class _AllowLedger:
    def check_and_consume(self, *a, **kw):
        return {"allowed": True, "reason": "within_limit"}


class _EmptyVM:
    def find_similar(self, *a, **kw):
        return []


def _make_executor(ledger=None, tmp_path=None):
    from agents.assistant_executor import AssistantExecutor
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    from agents.query_cache import QueryCache

    root = Path(tmp_path) if tmp_path else Path(tempfile.mkdtemp())
    store = KnowledgeCardStore(data_root=root)
    cache = QueryCache(data_root=root)
    router = LocalFirstRouter(
        kc_store=store,
        vector_memory=_EmptyVM(),
        cost_ledger=ledger or _AllowLedger(),
        query_cache=cache,
    )
    return AssistantExecutor(router=router)


# ----------------------------------------------------------------
# 1. Default runtime: unknown soru external_blocked'a saplamemali
# ----------------------------------------------------------------
def test_default_runtime_unknown_routes_external(tmp_path):
    ex = _make_executor(ledger=_AllowLedger(), tmp_path=tmp_path)
    result = ex.ask("Django REST framework nasil kurulur xyz999?")
    assert result["source"] != "external_blocked", (
        f"Default config problemi: {result['source']}"
    )
    assert result["ok"] is True or result.get("source") == "ollama_error"


# ----------------------------------------------------------------
# 2. Redaction-before-cost invariant
# Secret + blocking ledger -> redacted_blocked kazanmali
# ----------------------------------------------------------------
def test_secret_wins_over_budget_block(tmp_path):
    ex = _make_executor(ledger=_BlockLedger(), tmp_path=tmp_path)
    result = ex.ask("OPENAI_API_KEY=sk-test123 gonder")
    assert result["source"] == "redacted_blocked", (
        f"KRITIK: secret maliyet kap?s?ndan kacti! source={result['source']}"
    )
    assert result["ok"] is False
    assert result.get("blocked") is True


def test_secret_blocked_contains_safe_message(tmp_path):
    ex = _make_executor(ledger=_BlockLedger(), tmp_path=tmp_path)
    result = ex.ask("password=supersecret123 nedir?")
    assert result["source"] == "redacted_blocked"
    assert result.get("answer") is not None
    assert "supersecret" not in str(result.get("answer", ""))


# ----------------------------------------------------------------
# 3. Budget block sadece secret olmayan sorguda devreye girmeli
# ----------------------------------------------------------------
def test_budget_denial_on_clean_query_falls_back_local(tmp_path, monkeypatch):
    from agents.local_first_router import LocalFirstRouter
    from b10_execution_support import pipeline

    router = LocalFirstRouter(cost_ledger=_BlockLedger(), vector_memory=_EmptyVM(), data_root=tmp_path)
    ex, ledger, local, api = pipeline(tmp_path, monkeypatch, cloud=True, router=router)
    ledger.check_and_consume("prior_api")
    result = ex.ask("Django nasil kurulur xyz999?")
    assert result["ok"] is True
    assert result["source"] == "ollama"
    assert result["answer"] == "local answer"
    assert result["primary_failed_executor"] == "api"
    assert api.calls == []
    assert local.calls == ["Django nasil kurulur xyz999?"]
    assert ledger.stats()["today_count"] == 1


# ----------------------------------------------------------------
# 4. KC hit AssistantExecutor'dan direkt d?nmeli
# ----------------------------------------------------------------
def test_kc_hit_returns_directly(tmp_path):
    from agents.assistant_executor import AssistantExecutor
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore

    root = Path(tmp_path)
    store = KnowledgeCardStore(data_root=root)
    card = store.add(
        question="RTX 3070 kac watt tuketiyor?",
        answer="220W TDP.",
        source_model="test",
        confidence=90,
    )
    store.mark_approved(card["id"])
    store.mark_stored(card["id"], vector_doc_id="v1")
    router = LocalFirstRouter(
        kc_store=store,
        vector_memory=_EmptyVM(),
        cost_ledger=_BlockLedger(),
    )
    ex = AssistantExecutor(router=router)
    result = ex.ask("RTX 3070 kac watt tuketiyor?")
    assert result["ok"] is True
    assert result["source"] == "knowledge_card"
    assert "220W" in result["answer"]


# ----------------------------------------------------------------
# 5. Redaction check cache/KC'den sonra, cost'tan kesin once olmali
# Bu router seviyesinde invariant testi
# ----------------------------------------------------------------
def test_router_redaction_before_cost_invariant(tmp_path):
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore

    root = Path(tmp_path)
    store = KnowledgeCardStore(data_root=root)
    router = LocalFirstRouter(
        kc_store=store,
        vector_memory=_EmptyVM(),
        cost_ledger=_BlockLedger(),
        redact_before_external=True,
    )
    result = router.route("TELEGRAM_BOT_TOKEN=1234567890:ABCDEF gonder")
    assert result["decision"] == "redacted_blocked", (
        f"Router guvenlik sirasi hatasi: {result['decision']}"
    )
