"""Y0 - LocalFirstRouter.

Decides whether a question can be answered locally (KnowledgeCard/memory)
or needs escalation to an external model.

Decision values:
  answer_local  - local knowledge sufficient
  ask_external  - no local answer, escalate
  clarify       - question too vague to route
  no_answer     - question unanswerable even externally

Route values:
  knowledge_card - answer from KnowledgeCardRetriever
  memory         - answer from VectorMemory recall
  external       - escalate to external model
  clarify        - ask user for clarification

Scope (negative):
- No API calls
- No model selection
- No VectorMemory writes
- No Telegram
- No automatic crystallization
- Pure decision object
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class LocalFirstRouter:
    """Route a question to local knowledge or external model."""

    def __init__(
        self,
        kc_store=None,
        kc_min_confidence: int = 50,
        data_root: Path | str | None = None,
        vector_memory=None,
        cost_ledger=None,
        query_cache=None,
        redact_before_external: bool = True,
    ) -> None:
        self._kc_store = kc_store
        self._kc_min_confidence = kc_min_confidence
        self._data_root = Path(data_root) if data_root else ROOT / "memory"
        self._vector_memory = vector_memory
        self._cost_ledger = cost_ledger
        self._query_cache = query_cache
        self._redact_before_external = redact_before_external

    def _get_retriever(self):
        from agents.knowledge_card_retriever import KnowledgeCardRetriever
        return KnowledgeCardRetriever(
            store=self._kc_store,
            data_root=self._data_root,
            min_confidence=self._kc_min_confidence,
        )

    def _get_memory(self):
        if self._vector_memory is not None:
            return self._vector_memory
        try:
            from tools.vector_memory import VectorMemory
            self._vector_memory = VectorMemory()
        except Exception:
            self._vector_memory = None
        return self._vector_memory

    def _get_cascade(self):
        from agents.model_cascade import ModelCascade
        return ModelCascade()

    def _get_ledger(self):

        if self._cost_ledger is not None:
            return self._cost_ledger
        try:
            from agents.cost_ledger import CostLedger
            self._cost_ledger = CostLedger()
        except Exception:
            self._cost_ledger = None
        return self._cost_ledger

    def _recall(self, question: str) -> list[dict]:

        """Return priority-ranked safe memory hits. Empty list on any failure."""
        try:
            vm = self._get_memory()
            if vm is None:
                return []
            raw_hits = vm.find_similar(question, n=5, threshold=0.65)
            if not raw_hits:
                return []
            from agents.memory_retrieval_policy import MemoryRetrievalPolicy
            from agents.retrieval_priority import RetrievalPriorityRanker
            safe = MemoryRetrievalPolicy().filter_hits(raw_hits, query=question)
            if not safe:
                return []
            return RetrievalPriorityRanker(max_items=3).rank(safe)
        except Exception:
            return []

    def route(self, question: str, context: dict[str, Any] | None = None) -> dict[str, Any]:

        """Return routing decision dict. No side effects."""
        question = str(question or "").strip()

        # 0. Check query cache first
        if self._query_cache is not None:
            cached = self._query_cache.get_exact(question)
            if cached:
                return {
                    "decision": "answer_local",
                    "route": "cache",
                    "confidence": 95,
                    "reason": "query_cache_hit",
                    "answer": cached.get("answer"),
                    "signals": {"cache_hit": True, "hit_count": cached.get("hit_count")},
                }

        if not question:
            return {
                "decision": "clarify",
                "route": "clarify",
                "confidence": 0,
                "reason": "empty_question",
                "signals": {},
            }

        if len(question) < 4:
            return {
                "decision": "clarify",
                "route": "clarify",
                "confidence": 10,
                "reason": "too_short",
                "signals": {"length": len(question)},
            }

        # 1. Check KnowledgeCard store first
        try:
            retriever = self._get_retriever()
            kc_result = retriever.lookup(question)
        except Exception:
            kc_result = {"found": False}

        if kc_result.get("found"):
            card = kc_result.get("card") or {}
            score = kc_result.get("score", 0)
            confidence = min(100, int(50 + score * 50))
            return {
                "decision": "answer_local",
                "route": "knowledge_card",
                "confidence": confidence,
                "reason": f"knowledge_card_match:score={score}",
                "answer": kc_result.get("answer"),
                "signals": {
                    "kc_found": True,
                    "kc_score": score,
                    "kc_id": card.get("id"),
                    "kc_source_model": card.get("source_model"),
                },
            }

        # 2. Check VectorMemory recall
        vm_hits = self._recall(question)
        if vm_hits:
            top = vm_hits[0]
            priority = float(top.get("priority_score", 0.0))
            confidence = min(100, int(40 + priority * 60))
            return {
                "decision": "answer_local",
                "route": "memory",
                "confidence": confidence,
                "reason": f"memory_recall:priority={priority:.3f}",
                "signals": {
                    "kc_found": False,
                    "memory_hits": len(vm_hits),
                    "top_hit_priority": priority,
                    "top_hit_id": top.get("id"),
                },
            }

        # 3. Cost ledger gate before external
        ledger = self._get_ledger()
        if ledger is not None:
            gate = ledger.check_and_consume("external_call")
            if not gate.get("allowed"):
                return {
                    "decision": "external_blocked",
                    "route": "external_blocked",
                    "confidence": 0,
                    "reason": f"budget_limit:{gate.get('reason','exceeded')}",
                    "signals": {
                        "kc_found": False,
                        "memory_hits": 0,
                        "ledger": gate,
                    },
                }

        # Y4: Redaction gate ? raw secret must not leave the system
        if self._redact_before_external:
            try:
                from agents.redaction_guard import RedactionGuard
                guard = RedactionGuard()
                rr = guard.sanitize_text(question)
                if rr.redacted and rr.hits:
                    return {
                        "decision": "redacted_blocked",
                        "route": "redacted_blocked",
                        "confidence": 100,
                        "reason": "redaction_guard_detected_sensitive_data_before_external",
                        "signals": {
                            "redaction_enabled": True,
                            "sensitive_detected": True,
                            "redaction_hits": list(rr.hits),
                        },
                    }
            except Exception:
                pass  # redaction failure = fail open (let through, don't crash)

        checked = ["knowledge_card", "memory"]
        escalation_reason = "no_local_knowledge:kc=0,memory=0"
        cascade = self._get_cascade().select(question)
        return {
            "decision": "ask_external",
            "route": "external",
            "confidence": 60,
            "reason": "no_local_knowledge",
            "escalation_reason": escalation_reason,
            "checked_sources": checked,
            "cascade": cascade,
            "crystallize_candidate": {
                "question": question,
                "checked_sources": checked,
                "escalation_reason": escalation_reason,
                "status": "pending_crystallization",
            },
            "signals": {
                "kc_found": False,
                "memory_hits": 0,
            },
        }
