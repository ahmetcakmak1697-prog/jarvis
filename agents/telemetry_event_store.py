"""Y5 - TelemetryEventStore.

Append-only JSONL telemetry for AssistantExecutor ask events.

Privacy rules:
- Raw question/answer text is NEVER stored.
- Only SHA-256 hash of normalized question (for dedup/pattern detection).
- Sensitive data detection: if question contains known secret patterns, hash is zeroed.

Fields per event:
  event_type, source, level, model, ok, blocked,
  latency_ms, answer_chars, question_hash, created_at
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILENAME = "telemetry_events.jsonl"

_SECRET_PATTERNS = ("api_key", "token", "password", "secret", "sk-", "bearer")


def _hash_question(question: str) -> str:
    q = str(question or "").strip().lower()
    for pat in _SECRET_PATTERNS:
        if pat in q:
            return "REDACTED"
    return hashlib.sha256(q.encode("utf-8")).hexdigest()[:16]


class TelemetryEventStore:
    """Append-only JSONL store for ask telemetry."""

    def __init__(self, data_root: Path | str | None = None) -> None:
        root = Path(data_root) if data_root is not None else ROOT / "memory"
        root.mkdir(parents=True, exist_ok=True)
        self._path = root / DEFAULT_FILENAME

    def log_ask(
        self,
        source: str,
        level: str | None,
        model: str | None,
        ok: bool,
        blocked: bool,
        latency_ms: int,
        answer_chars: int,
        question: str = "",
    ) -> None:
        """Append one ask event. Never stores raw question."""
        event: dict[str, Any] = {
            "event_type": "ask_completed",
            "source": str(source or ""),
            "level": level,
            "model": model,
            "ok": bool(ok),
            "blocked": bool(blocked),
            "latency_ms": int(latency_ms or 0),
            "answer_chars": int(answer_chars or 0),
            "question_hash": _hash_question(question),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def stats(self) -> dict[str, Any]:
        """Return summary stats from all logged events."""
        if not self._path.exists():
            return {"total": 0, "by_source": {}, "avg_latency_ms": {}}

        events: list[dict] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                pass

        by_source: dict[str, int] = {}
        latency_sum: dict[str, int] = {}
        latency_count: dict[str, int] = {}

        for ev in events:
            src = str(ev.get("source") or "unknown")
            by_source[src] = by_source.get(src, 0) + 1
            ms = ev.get("latency_ms") or 0
            latency_sum[src] = latency_sum.get(src, 0) + ms
            latency_count[src] = latency_count.get(src, 0) + 1

        avg_latency = {
            src: int(latency_sum[src] / latency_count[src])
            for src in latency_sum
        }

        return {
            "total": len(events),
            "by_source": by_source,
            "avg_latency_ms": avg_latency,
        }
