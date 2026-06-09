"""C1.6F - Session/day closure summary.

Reads today's memory candidates and synthesis proposals,
produces a human-readable Telegram-safe summary string.

Scope (negative):
- No LLM calls
- No VectorMemory writes
- No queue mutations
- Zero side effects
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SessionClosure:
    """Produce a session closure summary from memory candidates."""

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

    def _count_by_status(self, candidates: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in candidates:
            s = str(c.get("status") or "unknown")
            counts[s] = counts.get(s, 0) + 1
        return counts

    def _synthesis_themes(self, candidates: list[dict]) -> list[str]:
        themes = []
        for c in candidates:
            if (
                str(c.get("source_type") or "") == "synthesis"
                and str(c.get("proposal_type") or "") == "synthesized_memory"
            ):
                theme = str(c.get("theme") or "").strip()
                if theme and theme not in themes:
                    themes.append(theme)
        return themes

    def summarize(self) -> str:
        """Return a Telegram-safe session closure summary string."""
        candidates = self._load_candidates()
        counts = self._count_by_status(candidates)
        themes = self._synthesis_themes(candidates)

        approved = counts.get("approved", 0)
        stored = counts.get("stored", 0)
        pending = counts.get("pending_review", 0)
        total = len(candidates)

        lines = ["Bugunki hafiza ozeti efendim."]

        if themes:
            theme_list = ", ".join(themes)
            lines.append(f"Sentez: {len(themes)} tema tespit edildi ({theme_list})")
        else:
            lines.append("Sentez: bu oturumda yeni tema olusturulmadi.")

        lines.append(f"Onaylanan: {approved} aday")
        lines.append(f"Yazilan: {stored} aday")
        lines.append(f"Bekleyen: {pending} aday")

        if total > 0:
            lines.append(f"Toplam kuyruk: {total} aday")

        if stored == 0 and approved == 0 and pending == 0:
            lines.append("Bugun hafizaya yeni icerik eklenmedi.")

        return "\n".join(lines)
