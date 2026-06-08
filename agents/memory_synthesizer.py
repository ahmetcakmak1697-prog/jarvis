"""Memory Synthesizer - C1.6A.

State management skeleton for episodic -> semantic synthesis pipeline.

Scope (C1.6A):
- SynthesisState dataclass with load/save/default
- processed delete_id tracking (duplicate guard)
- broken JSON safe fallback

Not in scope (C1.6B+):
- LLM synthesis
- VectorMemory write
- ApprovalQueue integration
- Automatic permanent memory
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "c1.6"


@dataclass
class SynthesisState:
    schema_version: str = SCHEMA_VERSION
    last_run: str = ""
    processed_delete_ids: list[str] = field(default_factory=list)
    generated_count: int = 0
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def mark_processed(self, delete_id: str) -> None:
        if delete_id and delete_id not in self.processed_delete_ids:
            self.processed_delete_ids.append(delete_id)

    def is_processed(self, delete_id: str) -> bool:
        return delete_id in self.processed_delete_ids


class MemorySynthesizerStore:
    """Load and persist SynthesisState."""

    DEFAULT_PATH = ROOT / "memory" / "synthesis_state.json"

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path is not None else self.DEFAULT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_or_default(self) -> SynthesisState:
        if not self.path.exists():
            return SynthesisState()

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return SynthesisState()

            return SynthesisState(
                schema_version=str(data.get("schema_version") or SCHEMA_VERSION),
                last_run=str(data.get("last_run") or ""),
                processed_delete_ids=list(data.get("processed_delete_ids") or []),
                generated_count=int(data.get("generated_count") or 0),
                updated_at=str(data.get("updated_at") or ""),
            )
        except Exception:
            return SynthesisState()

    def save(self, state: SynthesisState) -> None:
        state.updated_at = datetime.now().isoformat(timespec="seconds")
        self.path.write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def mark_processed(self, delete_id: str) -> SynthesisState:
        state = self.load_or_default()
        state.mark_processed(delete_id)
        self.save(state)
        return state

    def is_processed(self, delete_id: str) -> bool:
        return self.load_or_default().is_processed(delete_id)


class MemorySynthesizerCandidateCollector:
    ELIGIBLE_STATUSES = {"pending_review", "approved", "stored"}
    BLOCKED_MEMORY_TYPES = {"sensitive_review"}

    def __init__(self, queue_root=None, state_path=None):
        from agents.memory_candidate_queue import MemoryCandidateQueue
        self.queue = MemoryCandidateQueue(root=queue_root or ROOT)
        self.store = MemorySynthesizerStore(path=state_path)

    def _extract_text(self, item):
        return str(
            item.get("summary") or item.get("content")
            or item.get("user_msg") or item.get("text") or ""
        ).strip()

    def _is_expired(self, item):
        from datetime import datetime
        e = item.get("expires_at")
        if not e:
            return False
        try:
            return datetime.fromisoformat(str(e)) < datetime.now()
        except (ValueError, TypeError):
            return False

    def collect(self, limit=50):
        if limit <= 0:
            return []
        items = self.queue.list_candidates()
        eligible = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if str(item.get("source_type") or "") != "conversation":
                continue
            if str(item.get("status") or "") not in self.ELIGIBLE_STATUSES:
                continue
            if str(item.get("memory_type") or "") in self.BLOCKED_MEMORY_TYPES:
                continue
            if self._is_expired(item):
                continue
            text = self._extract_text(item)
            if not text:
                continue
            delete_id = str(item.get("delete_id") or item.get("id") or "")
            if delete_id and self.store.is_processed(delete_id):
                continue
            enriched = dict(item)
            enriched["_synthesis_text"] = text
            eligible.append(enriched)
            if len(eligible) >= limit:
                break
        return eligible

    def summary_texts(self, limit=50):
        return [
            i["_synthesis_text"]
            for i in self.collect(limit=limit)
            if i.get("_synthesis_text")
        ]



class MemorySynthesisReviewSubmitter:
    """Submit synthesized memory proposals to review queue.

    C1.6D transactional rule:
    - queue write first
    - mark source_ids processed only after successful queue write
    - no vector memory write
    """

    def __init__(self, queue=None, store=None, queue_root=None, state_path=None):
        if queue is None:
            from agents.memory_candidate_queue import MemoryCandidateQueue
            queue = MemoryCandidateQueue(root=queue_root or ROOT)

        self.queue = queue
        self.store = store if store is not None else MemorySynthesizerStore(path=state_path)

    def submit(self, proposals: list[dict]) -> dict:
        submitted = []
        errors = []
        processed_source_ids = []

        for proposal in proposals:
            if not isinstance(proposal, dict):
                errors.append({
                    "reason": "invalid_proposal",
                    "proposal": proposal,
                })
                continue

            result = self.queue.add_synthesis_candidate(proposal)
            if not result.get("ok") or not result.get("queued"):
                errors.append({
                    "reason": result.get("reason") or "queue_write_failed",
                    "proposal": proposal,
                    "result": result,
                })
                continue

            submitted.append(result.get("candidate"))

            source_ids = proposal.get("source_ids") or []
            if not isinstance(source_ids, list):
                source_ids = []

            for source_id in source_ids:
                source_id = str(source_id)
                if not source_id:
                    continue
                self.store.mark_processed(source_id)
                processed_source_ids.append(source_id)

        return {
            "ok": len(errors) == 0,
            "submitted_count": len(submitted),
            "error_count": len(errors),
            "processed_source_ids": processed_source_ids,
            "submitted": submitted,
            "errors": errors,
        }


# ---------------------------------------------------------------------------
# C1.6C -- Keyword Frequency Synthesizer
# ---------------------------------------------------------------------------

_DEFAULT_THEMES = [
    {
        "name": "jarvis",
        "keywords": ["jarvis", "roadmap", "commit", "patch", "test", "repo", "kod"],
        "summary": "Jarvis gelistirme calismalari aktif gorunuyor.",
    },
    {
        "name": "arduino",
        "keywords": ["arduino", "esp32", "elektronik", "breadboard", "jumper", "maker", "lehim"],
        "summary": "Elektronik ve Arduino ogrenme sureci aktif gorunuyor.",
    },
    {
        "name": "eshot",
        "keywords": ["eshot", "rapor", "telemetri", "rolanti", "yakit", "ihlal"],
        "summary": "ESHOT raporlama ve telemetri calismalari aktif gorunuyor.",
    },
    {
        "name": "health_rest",
        "keywords": ["yorgun", "uykusuz", "dinlen", "mola", "gece"],
        "summary": "Dinlenme ve enerji yonetimi dikkat gerektiriyor.",
    },
]


def _tr_fold(s: str) -> str:
    """ASCII-fold Turkish text for case-insensitive keyword matching.

    Python's .lower() mishandles Turkish: 'I'.lower() -> 'i' (should be 'i')
    and 'I' -> 'i' (should be 'i'). We fold everything to ASCII before matching
    so both keywords and candidate text compare on equal footing.
    Keywords are stored pre-folded (ASCII); input text is folded at match time.
    """
    s = s.replace("\u0130", "i")  # I (capital dotted) -> i
    s = s.replace("\u0049", "i")  # I -> i  (covers I->i same as ASCII)
    s = s.replace("\u0131", "i")  # i (dotless i) -> i
    s = s.replace("\u015f", "s")  # s -> s
    s = s.replace("\u015e", "s")  # S -> s
    s = s.replace("\u011f", "g")  # g -> g
    s = s.replace("\u011e", "g")  # G -> g
    s = s.replace("\u00fc", "u")  # u -> u
    s = s.replace("\u00dc", "u")  # U -> u
    s = s.replace("\u00f6", "o")  # o -> o
    s = s.replace("\u00d6", "o")  # O -> o
    s = s.replace("\u00e7", "c")  # c -> c
    s = s.replace("\u00c7", "c")  # C -> c
    return s.lower()


class KeywordFrequencySynthesizer:
    """C1.6C -- Rule-based keyword/theme frequency synthesizer.

    Reads _synthesis_text from collected candidates, counts how many
    DISTINCT candidates mention each theme (via substring/contains match,
    Turkish ASCII-folded), and produces proposals for themes that meet the
    threshold. Returns proposals only -- never writes to memory directly.

    Scope (negative):
      - No LLM calls
      - No VectorMemory writes
      - No ApprovalQueue writes
      - Zero side effects
    """

    def __init__(self, themes=None, min_mentions: int = 3):
        self.themes = themes if themes is not None else _DEFAULT_THEMES
        self.min_mentions = min_mentions

    def _candidate_blocked_for_synthesis(self, cand: dict) -> bool:
        """Return True when a candidate must not participate in synthesis.

        C1.6B already filters sensitive candidates before this point.
        This is a defensive guard so a future caller cannot accidentally
        synthesize private, sensitive, review-only, or blocked content.
        """
        boolean_flags = (
            "is_sensitive",
            "sensitive",
            "blocked",
            "synthesis_blocked",
            "_synthesis_blocked",
            "skip_synthesis",
            "requires_review",
            "sensitive_review_required",
            "approval_required",
        )
        if any(bool(cand.get(flag)) for flag in boolean_flags):
            return True

        data_class = str(cand.get("data_class") or cand.get("classification") or "").lower()
        route = str(cand.get("route") or cand.get("memory_route") or "").lower()
        decision = str(cand.get("decision") or "").lower()
        trust = str(cand.get("trust") or "").lower()
        memory_type = str(cand.get("memory_type") or "").lower()
        storage_target = str(cand.get("storage_target") or "").lower()

        # Do not treat normal queue status such as "pending_review" as blocked.
        # C1.6B intentionally allows pending_review/approved/stored candidates.
        # Blocking is based on data class, memory type, route, decision and trust.
        marker_text = " ".join((data_class, route, decision, trust, memory_type, storage_target))

        blocked_markers = (
            "personal-sensitive",
            "sensitive",
            "corporate",
            "eshot-sensitive",
            "blocked",
            "reject",
            "rejected",
            "redaction",
            "review",
            "approval",
            "untrusted",
        )
        return any(marker in marker_text for marker in blocked_markers)

    def _text_mentions_theme(self, folded_text: str, theme: dict) -> bool:
        """Return True if folded_text contains at least one keyword (substring match)."""
        return any(kw in folded_text for kw in theme["keywords"])

    def synthesize(self, candidates: list) -> list:
        """Analyse candidates and return theme proposals above threshold.

        Args:
            candidates: list of dicts with '_synthesis_text' field
                        (as produced by MemorySynthesizerCandidateCollector).

        Returns:
            list of proposal dicts:
            {
                'theme': str,
                'summary': str,
                'source_count': int,
                'confidence': int,          # min(95, 50 + source_count * 10)
                'source_ids': list[str],    # delete_id values of matching candidates
                'proposal_type': 'synthesized_memory',
            }
        """
        results = []

        for theme in self.themes:
            matching_source_ids = []

            for cand in candidates:
                if not isinstance(cand, dict):
                    continue

                if self._candidate_blocked_for_synthesis(cand):
                    continue

                text = str(cand.get("_synthesis_text") or "")
                if not text:
                    continue

                folded = _tr_fold(text)
                if self._text_mentions_theme(folded, theme):
                    source_id = str(
                        cand.get("delete_id") or cand.get("id") or ""
                    )
                    matching_source_ids.append(source_id)

            source_count = len(matching_source_ids)

            if source_count < self.min_mentions:
                continue  # below threshold -- no proposal

            confidence = min(95, 50 + source_count * 10)

            results.append(
                {
                    "theme": theme["name"],
                    "summary": theme["summary"],
                    "source_count": source_count,
                    "confidence": confidence,
                    "source_ids": matching_source_ids,
                    "proposal_type": "synthesized_memory",
                }
            )

        return results

