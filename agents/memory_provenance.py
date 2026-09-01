"""C1.6G-lite - Source-linked memory provenance resolver.

Resolves a synthesized memory's source_ids back to real candidate records,
so Jarvis can answer 'this memory came from which sources?'.

Scope (negative):
- No LLM calls
- No VectorMemory writes
- No queue mutations
- No deduplication / merging
- Missing sources are marked resolved=False, never block promotion
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_PREVIEW_LIMIT = 160


class MemoryProvenanceResolver:
    """Resolve source_ids to candidate provenance links."""

    def __init__(
        self,
        candidates: list[dict] | None = None,
        data_root: Path | str | None = None,
    ) -> None:
        self._candidates = candidates
        self._data_root = Path(data_root) if data_root is not None else ROOT

    def _load_candidates(self) -> list[dict]:
        if self._candidates is not None:
            return list(self._candidates)
        try:
            from agents.memory_candidate_queue import MemoryCandidateQueue
            q = MemoryCandidateQueue(root=self._data_root)
            return q.list_candidates()
        except Exception:
            return []

    def _index(self, candidates: list[dict]) -> dict[str, dict]:
        index: dict[str, dict] = {}
        for c in candidates:
            if not isinstance(c, dict):
                continue
            for key in (c.get("delete_id"), c.get("id")):
                key_str = str(key or "").strip()
                if key_str and key_str not in index:
                    index[key_str] = c
        return index

    def _preview(self, candidate: dict) -> str:
        text = str(
            candidate.get("summary")
            or candidate.get("content")
            or candidate.get("user_msg")
            or candidate.get("text")
            or ""
        ).strip()
        if len(text) > _PREVIEW_LIMIT:
            return text[:_PREVIEW_LIMIT - 3].rstrip() + "..."
        return text

    def resolve(self, source_ids: list) -> list[dict]:
        """Resolve each source_id to a provenance link dict.

        Returns a list; blank/None ids are skipped. Each link:
        {id, resolved, type, status, theme, summary_preview}
        """
        candidates = self._load_candidates()
        index = self._index(candidates)

        links: list[dict] = []
        for raw_id in source_ids or []:
            source_id = str(raw_id or "").strip()
            if not source_id:
                continue

            match = index.get(source_id)
            if match is None:
                links.append({
                    "id": source_id,
                    "resolved": False,
                    "type": None,
                    "status": None,
                    "theme": None,
                    "summary_preview": "",
                })
            else:
                links.append({
                    "id": source_id,
                    "resolved": True,
                    "type": str(match.get("source_type") or "") or None,
                    "status": str(match.get("status") or "") or None,
                    "theme": str(match.get("theme") or "") or None,
                    "summary_preview": self._preview(match),
                })

        return links

    def summarize(self, source_ids: list) -> dict[str, Any]:
        """Resolve and return aggregate counts + links."""
        links = self.resolve(source_ids)
        resolved = sum(1 for l in links if l["resolved"])
        return {
            "total": len(links),
            "resolved": resolved,
            "unresolved": len(links) - resolved,
            "links": links,
        }
