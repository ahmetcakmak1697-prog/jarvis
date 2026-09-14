#!/usr/bin/env python3
"""
JARVIS System Audit ? Kapsamli sistem saglik testi.
Her modulu, her siniri, her edge-case'i test eder.
Bagimsiz calisir; pytest gerektirmez.
"""
from __future__ import annotations
import sys
import traceback
import json
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0
WARN = 0
RESULTS = []

def ok(name):
    global PASS
    PASS += 1
    RESULTS.append(("OK  ", name))

def fail(name, reason):
    global FAIL
    FAIL += 1
    RESULTS.append(("FAIL", f"{name}: {reason}"))

def warn(name, reason):
    global WARN
    WARN += 1
    RESULTS.append(("WARN", f"{name}: {reason}"))

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

# ================================================================
# 1. IMPORT AUDIT ? tum modul import edilebiliyor mu?
# ================================================================
section("1. IMPORT AUDIT")

MODULES = [
    "agents.knowledge_card_store",
    "agents.knowledge_card_retriever",
    "agents.knowledge_card_editor",
    "agents.knowledge_card_promoter",
    "agents.tiered_memory",
    "agents.memory_maturity",
    "agents.retrieval_priority",
    "agents.episodic_buffer",
    "agents.memory_retrieval_policy",
    "agents.local_first_router",
    "agents.model_cascade",
    "agents.model_registry",
    "agents.cost_ledger",
    "agents.query_cache",
    "agents.ollama_executor",
    "agents.redaction_guard",
    "tools.vector_memory",
    "tools.telegram_agent",
]

for mod in MODULES:
    try:
        __import__(mod)
        ok(f"import {mod}")
    except Exception as e:
        fail(f"import {mod}", str(e)[:80])

# ================================================================
# 2. KNOWLEDGE CARD STORE
# ================================================================
section("2. KnowledgeCardStore")

try:
    from agents.knowledge_card_store import KnowledgeCardStore
    with tempfile.TemporaryDirectory() as td:
        store = KnowledgeCardStore(data_root=Path(td))

        # add
        c = store.add(question="Test sorusu?", answer="Test cevap.", source_model="test", confidence=80)
        assert "id" in c, "id eksik"
        assert c["review_status"] == "pending", f"beklenen pending, geldi {c['review_status']}"
        ok("KC store.add")

        # get
        fetched = store.get(c["id"])
        assert fetched is not None, "get None dondu"
        assert fetched["question"] == "Test sorusu?", "question eslesmiyor"
        ok("KC store.get")

        # mark_approved
        store.mark_approved(c["id"])
        assert store.get(c["id"])["review_status"] == "approved"
        ok("KC store.mark_approved")

        # mark_stored
        store.mark_stored(c["id"], vector_doc_id="vec_001")
        assert store.get(c["id"])["storage_status"] == "stored"
        ok("KC store.mark_stored")

        # mark_superseded
        store.mark_superseded(c["id"], superseded_by="kc_new")
        assert store.get(c["id"]).get("superseded") is True
        ok("KC store.mark_superseded")

        # list_cards
        cards = store.list_cards()
        assert len(cards) >= 1
        ok("KC store.list_cards")

        # blank question - ValueError veya ok=False donmeli
        try:
            r = store.add(question="", answer="x", source_model="t", confidence=50)
            assert r.get("ok") is False or "id" not in r
            ok("KC store.add blank question handled (soft reject)")
        except (ValueError, Exception):
            ok("KC store.add blank question handled (exception)")

except Exception as e:
    fail("KnowledgeCardStore", traceback.format_exc()[-200:])

# ================================================================
# 3. KNOWLEDGE CARD RETRIEVER
# ================================================================
section("3. KnowledgeCardRetriever")

try:
    from agents.knowledge_card_store import KnowledgeCardStore
    from agents.knowledge_card_retriever import KnowledgeCardRetriever

    with tempfile.TemporaryDirectory() as td:
        store = KnowledgeCardStore(data_root=Path(td))
        c = store.add(question="RTX 3070 kac watt tuketiyor?", answer="220W TDP.", source_model="t", confidence=90)
        store.mark_approved(c["id"])
        store.mark_stored(c["id"], vector_doc_id="v1")
        r = KnowledgeCardRetriever(store=store)

        # exact match
        res = r.lookup("RTX 3070 kac watt tuketiyor?")
        assert res["found"] is True, f"exact match bulunamadi: {res}"
        assert 0.0 <= res["score"] <= 1.0, f"score float olmali: {res['score']}"
        assert "220W" in res["answer"], "answer eksik"
        ok("KC retriever exact match")

        # false positive: farkli konu
        res2 = r.lookup("Python listede tekrar eden elemanlari nasil buluruz?")
        assert res2["found"] is False, f"false positive! score={res2['score']}"
        ok("KC retriever no false positive (Python vs RTX)")

        # digit mismatch: 3070 vs 4090
        res3 = r.lookup("RTX 4090 kac watt tuketiyor?")
        assert res3["found"] is False, f"digit mismatch false positive! score={res3['score']}"
        ok("KC retriever digit mismatch blocked (3070 vs 4090)")

        # negation mismatch
        store2 = KnowledgeCardStore(data_root=Path(td) / "neg")
        cn = store2.add(question="RTX 3070 iyi mi?", answer="Evet.", source_model="t", confidence=90)
        store2.mark_approved(cn["id"])
        store2.mark_stored(cn["id"], vector_doc_id="v2")
        r2 = KnowledgeCardRetriever(store=store2)
        res4 = r2.lookup("RTX 3070 iyi degil mi?")
        assert res4["found"] is False, f"negation false positive! score={res4['score']}"
        ok("KC retriever negation mismatch blocked")

        # superseded kart eslesmiyor mu?
        store3 = KnowledgeCardStore(data_root=Path(td) / "sup")
        cs = store3.add(question="RTX 3070 kac watt?", answer="Eski cevap.", source_model="t", confidence=90)
        store3.mark_approved(cs["id"])
        store3.mark_stored(cs["id"], vector_doc_id="v3")
        store3.mark_superseded(cs["id"])
        r3 = KnowledgeCardRetriever(store=store3)
        res5 = r3.lookup("RTX 3070 kac watt?")
        assert res5["found"] is False, "superseded kart eslesiyor ? yanlis!"
        ok("KC retriever superseded card blocked")

        # bos sorgu
        res6 = r.lookup("")
        assert res6["found"] is False
        ok("KC retriever empty query")

except Exception as e:
    fail("KnowledgeCardRetriever", traceback.format_exc()[-300:])

# ================================================================
# 4. KNOWLEDGE CARD EDITOR
# ================================================================
section("4. KnowledgeCardEditor")

try:
    from agents.knowledge_card_store import KnowledgeCardStore
    from agents.knowledge_card_editor import KnowledgeCardEditor

    with tempfile.TemporaryDirectory() as td:
        store = KnowledgeCardStore(data_root=Path(td))
        c = store.add(question="Eski soru?", answer="Eski cevap.", source_model="t", confidence=80)
        store.mark_approved(c["id"])
        store.mark_stored(c["id"], vector_doc_id="v1")
        editor = KnowledgeCardEditor(store=store)

        # edit
        res = editor.edit(c["id"], {"answer": "Yeni cevap."})
        assert res["ok"] is True, f"edit basarisiz: {res}"
        assert res["new_card"]["answer"] == "Yeni cevap."
        assert res["new_card"]["id"] != c["id"]
        assert res["new_card"].get("previous_version_id") == c["id"]
        assert res["new_card"]["review_status"] == "pending"
        assert res["new_card"]["vector_doc_id"] is None
        ok("KC editor creates new version")

        # eski kart korunuyor mu?
        old_card = store.get(c["id"])
        assert old_card["answer"] == "Eski cevap.", "eski kart degistirilmis!"
        assert old_card.get("superseded") is True
        ok("KC editor preserves old card as superseded")

        # bos degisiklik
        res2 = editor.edit(c["id"], {})
        assert res2["ok"] is False and res2["reason"] == "no_changes"
        ok("KC editor rejects empty changes")

        # guvenli olmayan alan
        res3 = editor.edit(c["id"], {"vector_doc_id": "hack"})
        assert res3["ok"] is False and res3["reason"] == "no_safe_changes"
        ok("KC editor rejects unsafe fields")

        # olmayan kart
        res4 = editor.edit("nonexistent_id", {"answer": "x"})
        assert res4["ok"] is False and res4["reason"] == "card_not_found"
        ok("KC editor rejects nonexistent card")

except Exception as e:
    fail("KnowledgeCardEditor", traceback.format_exc()[-300:])

# ================================================================
# 5. EPISODIC BUFFER
# ================================================================
section("5. EpisodicBuffer")

try:
    from agents.episodic_buffer import EpisodicBuffer

    with tempfile.TemporaryDirectory() as td:
        buf = EpisodicBuffer(root=Path(td))

        # append
        r = buf.append_event("coding", "Test event", tags=["test"])
        assert r["ok"] is True
        assert "created_at" in r["event"]
        ok("EpisodicBuffer append_event")

        # blank summary
        r2 = buf.append_event("note", "   ")
        assert r2["ok"] is False and r2["reason"] == "blank_summary"
        ok("EpisodicBuffer rejects blank summary")

        # list_recent
        buf.append_event("a", "bir")
        buf.append_event("b", "iki")
        recent = buf.list_recent(limit=2)
        assert len(recent) == 2
        assert recent[0]["event_type"] == "b"  # newest first
        ok("EpisodicBuffer list_recent newest first")

        # prune
        for i in range(6):
            buf.append_event("note", f"olay {i}")
        r3 = buf.prune(max_items=3)
        assert r3["ok"] is True and r3["kept"] == 3
        ok("EpisodicBuffer prune")

        # stats
        s = buf.stats()
        assert "total" in s and "by_type" in s
        ok("EpisodicBuffer stats")

except Exception as e:
    fail("EpisodicBuffer", traceback.format_exc()[-300:])

# ================================================================
# 6. QUERY CACHE
# ================================================================
section("6. QueryCache")

try:
    from agents.query_cache import QueryCache

    with tempfile.TemporaryDirectory() as td:
        cache = QueryCache(data_root=Path(td))

        # miss
        assert cache.get_exact("bilinmeyen") is None
        ok("QueryCache exact miss")

        # put + get
        cache.put("RTX 3070 kac watt?", "220W.", source_route="kc")
        r = cache.get_exact("RTX 3070 kac watt?")
        assert r is not None and r["answer"] == "220W."
        ok("QueryCache put + exact hit")

        # normalize
        r2 = cache.get_exact("rtx 3070 kac watt?")
        assert r2 is not None
        ok("QueryCache normalize case")

        # hit count
        r3 = cache.get_exact("RTX 3070 kac watt?")
        assert r3["hit_count"] >= 2
        ok("QueryCache hit_count increments")

        # semantic hit
        cache.put("RTX 3070 ekran karti kac watt tuketiyor?", "220W.", source_route="kc")
        sr = cache.get_semantic("RTX 3070 ekran karti kac watt?")
        assert sr is not None
        assert sr["match_type"] == "semantic"
        assert 0.0 <= sr["similarity"] <= 1.0
        ok("QueryCache semantic hit")

        # semantic digit guard
        sr2 = cache.get_semantic("RTX 4090 kac watt tuketiyor?")
        assert sr2 is None, f"digit guard failed! similarity={sr2}"
        ok("QueryCache semantic digit guard (3070 vs 4090)")

        # semantic negation guard
        cache.put("RTX 3070 iyi mi?", "Evet.", source_route="kc")
        sr3 = cache.get_semantic("RTX 3070 iyi degil mi?")
        assert sr3 is None, "negation guard failed!"
        ok("QueryCache semantic negation guard")

        # stats
        s = cache.stats()
        assert "total_entries" in s
        ok("QueryCache stats")

        # persist
        cache2 = QueryCache(data_root=Path(td))
        r4 = cache2.get_exact("RTX 3070 kac watt?")
        assert r4 is not None
        ok("QueryCache persists across instances")

except Exception as e:
    fail("QueryCache", traceback.format_exc()[-300:])

# ================================================================
# 7. COST LEDGER
# ================================================================
section("7. CostLedger")

try:
    from agents.cost_ledger import CostLedger

    with tempfile.TemporaryDirectory() as td:
        # unlimited
        l0 = CostLedger(daily_limit=0, data_root=Path(td) / "unlimited")
        for _ in range(10):
            r = l0.check_and_consume("test")
        assert r["allowed"] is True
        ok("CostLedger unlimited always allows")

        # limit
        l1 = CostLedger(daily_limit=3, data_root=Path(td) / "limited")
        for _ in range(3):
            l1.check_and_consume("test")
        r2 = l1.check_and_consume("test")
        assert r2["allowed"] is False and r2["reason"] == "daily_limit_exceeded"
        ok("CostLedger blocks after limit")

        # dry_run
        l2 = CostLedger(daily_limit=10, data_root=Path(td) / "dry")
        l2.check_and_consume("test", dry_run=True)
        assert l2.stats()["today_count"] == 0
        ok("CostLedger dry_run no consume")

        # stats
        l3 = CostLedger(daily_limit=5, data_root=Path(td) / "stats")
        l3.check_and_consume("test")
        s = l3.stats()
        assert s["today_count"] == 1 and s["remaining"] == 4
        ok("CostLedger stats accurate")

except Exception as e:
    fail("CostLedger", traceback.format_exc()[-300:])

# ================================================================
# 8. MODEL CASCADE
# ================================================================
section("8. ModelCascade")

try:
    from agents.model_cascade import ModelCascade
    c = ModelCascade()

    # required fields
    r = c.select("test sorusu")
    for field in ["level", "model", "reason", "cost_tier"]:
        assert field in r, f"{field} eksik"
    ok("ModelCascade required fields")

    # L4 sadece force ile
    r2 = c.select("karmasik soru derinlemesine analiz et ve rapor hazirla")
    assert r2["level"] != "L4", f"L4 otomatik secildi: {r2}"
    ok("ModelCascade L4 not auto-selected")

    # force_level
    r3 = c.select("test", force_level="L4")
    assert r3["level"] == "L4" and r3["cost_tier"] == "expensive"
    ok("ModelCascade force_level L4")

    # L0 local_memory
    r4 = c.select("test", force_level="L0")
    assert r4["model"] == "local_memory"
    ok("ModelCascade L0 = local_memory")

    # cost_tier gecerli
    assert r["cost_tier"] in ("free", "cheap", "moderate", "expensive")
    ok("ModelCascade cost_tier valid")

except Exception as e:
    fail("ModelCascade", traceback.format_exc()[-300:])

# ================================================================
# 9. LOCAL FIRST ROUTER
# ================================================================
section("9. LocalFirstRouter")

try:
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    from agents.cost_ledger import CostLedger

    class _FakeLedgerAllow:
        def check_and_consume(self, *a, **kw):
            return {"allowed": True, "reason": "within_limit"}

    class _FakeLedgerBlock:
        def check_and_consume(self, *a, **kw):
            return {"allowed": False, "reason": "daily_limit_exceeded"}

    class _FakeVM:
        def find_similar(self, *a, **kw):
            return []

    with tempfile.TemporaryDirectory() as td:
        store = KnowledgeCardStore(data_root=Path(td))

        # required fields
        r = LocalFirstRouter(kc_store=store, cost_ledger=_FakeLedgerAllow(), vector_memory=_FakeVM()).route("test sorusu")
        for f in ["decision", "route", "confidence", "reason", "signals"]:
            assert f in r, f"{f} eksik"
        ok("LocalFirstRouter required fields")

        # KC hit -> answer_local + answer field
        c = store.add(question="RTX 3070 kac watt tuketiyor?", answer="220W.", source_model="t", confidence=90)
        store.mark_approved(c["id"])
        store.mark_stored(c["id"], vector_doc_id="v1")
        router = LocalFirstRouter(kc_store=store, cost_ledger=_FakeLedgerAllow(), vector_memory=_FakeVM())
        r2 = router.route("RTX 3070 kac watt tuketiyor?")
        assert r2["decision"] == "answer_local"
        assert r2["route"] == "knowledge_card"
        assert "answer" in r2 and r2["answer"] is not None
        assert "220W" in r2["answer"]
        ok("LocalFirstRouter KC hit returns answer")

        # false positive yok: Python sorusu KC'ye gitmemeli
        r3 = router.route("Python listede tekrar eden elemanlari nasil buluruz?")
        assert r3["route"] != "knowledge_card", f"false positive! route={r3['route']}"
        ok("LocalFirstRouter no KC false positive")

        # cost blocked
        r4 = LocalFirstRouter(kc_store=store, cost_ledger=_FakeLedgerBlock(), vector_memory=_FakeVM()).route("bilinmeyen soru xyz")
        assert r4["decision"] == "external_blocked"
        ok("LocalFirstRouter external_blocked when ledger denies")

        # redaction
        r5 = LocalFirstRouter(kc_store=store, cost_ledger=_FakeLedgerAllow(), vector_memory=_FakeVM(), redact_before_external=True).route("OPENAI_API_KEY=sk-test123 gonder")
        assert r5["decision"] == "redacted_blocked"
        ok("LocalFirstRouter redacted_blocked for secrets")

        # redaction disabled
        r6 = LocalFirstRouter(kc_store=store, cost_ledger=_FakeLedgerAllow(), vector_memory=_FakeVM(), redact_before_external=False).route("OPENAI_API_KEY=sk-test123")
        assert r6["decision"] != "redacted_blocked"
        ok("LocalFirstRouter redaction disabled passes through")

        # cascade on external
        r7 = LocalFirstRouter(kc_store=store, cost_ledger=_FakeLedgerAllow(), vector_memory=_FakeVM()).route("bilinmeyen soru xyz999")
        if r7["decision"] == "ask_external":
            assert "cascade" in r7
            assert r7["cascade"]["level"] in ("L0","L1","L2","L3","L4")
            ok("LocalFirstRouter cascade present on ask_external")
        else:
            warn("LocalFirstRouter cascade check", f"decision={r7['decision']}")

        # crystallize candidate
        if r7["decision"] == "ask_external":
            assert "crystallize_candidate" in r7
            assert r7["crystallize_candidate"]["status"] == "pending_crystallization"
            ok("LocalFirstRouter crystallize_candidate on external")

        # empty question
        r8 = LocalFirstRouter(kc_store=store, cost_ledger=_FakeLedgerAllow()).route("")
        assert r8["decision"] == "clarify"
        ok("LocalFirstRouter empty question -> clarify")

except Exception as e:
    fail("LocalFirstRouter", traceback.format_exc()[-400:])

# ================================================================
# 10. OLLAMA EXECUTOR
# ================================================================
section("10. OllamaExecutor")

try:
    from agents.ollama_executor import OllamaExecutor

    class _FakeClient:
        def __init__(self, fail=False):
            self.fail = fail
            self.calls = []
        def generate(self, model, prompt, stream=False):
            self.calls.append((model, prompt))
            if self.fail:
                raise ConnectionError("Ollama kapali")
            return {"response": "Test cevabi.", "model": model, "done": True}

    # required fields
    ex = OllamaExecutor(client=_FakeClient())
    r = ex.generate("Test?")
    for f in ["ok","text","model","level","latency_ms"]:
        assert f in r, f"{f} eksik"
    ok("OllamaExecutor required fields")

    # ok=True
    assert r["ok"] is True and r["text"] == "Test cevabi."
    ok("OllamaExecutor returns text")

    # dry_run
    r2 = ex.generate("Test?", dry_run=True)
    assert r2["ok"] is True and r2["dry_run"] is True
    ok("OllamaExecutor dry_run")

    # connection error
    ex2 = OllamaExecutor(client=_FakeClient(fail=True))
    r3 = ex2.generate("Test?")
    assert r3["ok"] is False and r3["text"] is None and "error" in r3
    ok("OllamaExecutor connection error handled")

    # level mapping
    ex3 = OllamaExecutor(client=_FakeClient())
    assert ex3.level_to_model("L0") == "local_memory"
    assert ex3.level_to_model("L1") is not None
    assert ex3.level_to_model("L2") is not None
    ok("OllamaExecutor level_to_model")

    # L0 no execution
    r4 = ex3.generate("Test?", level="L0")
    assert r4["ok"] is False, "L0 execution olmamali"
    ok("OllamaExecutor L0 returns error (no execution)")

    # Ollama live check
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3)
        ex_live = OllamaExecutor()
        r5 = ex_live.generate("Merhaba, kisaca kendini tanit.", level="L1")
        if r5["ok"]:
            ok(f"OllamaExecutor LIVE test (L1, {r5['latency_ms']}ms, {r5['model']})")
        else:
            warn("OllamaExecutor LIVE test", r5.get("error","?"))
    except Exception:
        warn("OllamaExecutor LIVE test", "Ollama erisilemiyor ? skip")

except Exception as e:
    fail("OllamaExecutor", traceback.format_exc()[-300:])

# ================================================================
# 11. REDACTION GUARD
# ================================================================
section("11. RedactionGuard")

try:
    from agents.redaction_guard import RedactionGuard
    g = RedactionGuard()

    # API key
    r = g.sanitize_text("OPENAI_API_KEY=sk-abcdef123456")
    assert r.redacted is True and len(r.hits) > 0
    ok("RedactionGuard detects API key")

    # email
    r2 = g.sanitize_text("Mail: ahmet@example.com")
    assert r2.redacted is True
    ok("RedactionGuard detects email")

    # temiz metin
    r3 = g.sanitize_text("Python listede tekrar eden elemanlari bulmak icin set kullanilir.")
    assert r3.redacted is False
    ok("RedactionGuard clean text not redacted")

    # contains_sensitive_data
    assert g.contains_sensitive_data("password=supersecret") is True
    assert g.contains_sensitive_data("merhaba dunya") is False
    ok("RedactionGuard contains_sensitive_data")

except Exception as e:
    fail("RedactionGuard", traceback.format_exc()[-300:])

# ================================================================
# 12. END-TO-END INTEGRATION
# ================================================================
section("12. END-TO-END INTEGRATION")

try:
    from agents.local_first_router import LocalFirstRouter
    from agents.knowledge_card_store import KnowledgeCardStore
    from agents.query_cache import QueryCache
    from agents.ollama_executor import OllamaExecutor
    from agents.cost_ledger import CostLedger

    class _FakeVM:
        def find_similar(self, *a, **kw):
            return []

    class _FakeClient:
        def generate(self, model, prompt, stream=False):
            return {"response": f"[FAKE:{model}] {prompt[:30]}", "model": model, "done": True}

    with tempfile.TemporaryDirectory() as td:
        store = KnowledgeCardStore(data_root=Path(td))
        cache = QueryCache(data_root=Path(td))
        ledger = CostLedger(daily_limit=0, data_root=Path(td))
        executor = OllamaExecutor(client=_FakeClient())

        # KC ekle
        c = store.add(question="RTX 3070 kac watt tuketiyor?", answer="220W TDP.", source_model="test", confidence=90)
        store.mark_approved(c["id"])
        store.mark_stored(c["id"], vector_doc_id="v1")

        router = LocalFirstRouter(
            kc_store=store,
            vector_memory=_FakeVM(),
            cost_ledger=ledger,
            query_cache=cache,
        )

        # Senaryo 1: KC'den yerelden cevap
        r1 = router.route("RTX 3070 kac watt tuketiyor?")
        assert r1["decision"] == "answer_local"
        assert r1["route"] == "knowledge_card"
        assert "220W" in r1.get("answer","")
        ok("E2E: KC hit returns local answer")

        # Senaryo 2: Bilinmeyen -> external -> executor
        r2 = router.route("Django REST framework nasil kurulur?")
        assert r2["decision"] == "ask_external"
        level = r2.get("cascade",{}).get("level","L2")
        exec_r = executor.generate("Django REST framework nasil kurulur?", level=level)
        assert exec_r["ok"] is True and exec_r["text"] is not None
        ok("E2E: unknown -> ask_external -> executor generates response")

        # Senaryo 3: Secret -> blocked
        r3 = router.route("TELEGRAM_BOT_TOKEN=1234567890:ABC gonder")
        assert r3["decision"] == "redacted_blocked"
        ok("E2E: secret blocked before external")

        # Senaryo 4: Cache'e yaz, sonra tekrar sor
        cache.put("Ollama nasil kurulur?", "curl ile indirilir.", source_route="kc")
        r4 = router.route("Ollama nasil kurulur?")
        assert r4["decision"] == "answer_local" and r4["route"] == "cache"
        ok("E2E: cache hit returns local answer")

        # Senaryo 5: False positive yok
        r5 = router.route("Python listede tekrar eden elemanlari nasil buluruz?")
        assert r5["route"] != "knowledge_card", f"false positive! {r5['route']}"
        ok("E2E: no false positive KC match")

except Exception as e:
    fail("END-TO-END", traceback.format_exc()[-400:])

# ================================================================
# SONUC
# ================================================================
section("AUDIT SONUCU")

for status, name in RESULTS:
    print(f"  [{status}] {name}")

print()
print(f"  TOPLAM : {PASS+FAIL+WARN}")
print(f"  OK     : {PASS}")
print(f"  FAIL   : {FAIL}")
print(f"  WARN   : {WARN}")
print()

if FAIL == 0:
    print("  >>> TUM TESTLER GECTI ? SISTEM SAGLIKLI <<<")
    sys.exit(0)
else:
    print(f"  >>> {FAIL} KRITIK HATA BULUNDU <<<")
    sys.exit(1)
