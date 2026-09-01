"""C1.6H-2 - AnswerCrystallizer.

Takes a question + answer from an expensive model and crystallizes it
into a KnowledgeCard (pending/draft). Never writes to VectorMemory.

Scope (negative):
- No LLM calls
- No VectorMemory writes
- No queue mutations
- Vector indexing is a separate approve/promote step (C1.6H-3)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class AnswerCrystallizer:
    """Crystallize a question/answer pair into a pending KnowledgeCard."""

    def __init__(
        self,
        store=None,
        data_root: Path | str | None = None,
    ) -> None:
        self._store = store
        self._data_root = Path(data_root) if data_root is not None else ROOT / "memory"

    def _get_store(self):
        if self._store is not None:
            return self._store
        from agents.knowledge_card_store import KnowledgeCardStore
        self._store = KnowledgeCardStore(data_root=self._data_root)
        return self._store

    def crystallize(
        self,
        question: str,
        answer: str,
        source_model: str,
        domain: str = "",
        tags: list[str] | None = None,
        confidence: int = 80,
    ) -> dict[str, Any]:
        """Create and persist a pending/draft KnowledgeCard.

        Does NOT write to VectorMemory. Returns the card dict.
        Raises ValueError for invalid inputs (delegated to KnowledgeCardStore).
        """
        store = self._get_store()
        card = store.add(
            question=question,
            answer=answer,
            source_model=source_model,
            domain=domain,
            tags=tags,
            confidence=confidence,
        )
        return card
