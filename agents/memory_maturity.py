"""C1.7-3A - Memory Maturity Scorer.

Calculates how mature/stable a memory record is based on:
- age (days since created_at)
- access_count
- tier (core/recall/archival/episodic)
- confidence

Output levels:
  fresh    - brand new, not yet proven
  warming  - used a few times, gaining trust
  stable   - well-established, reliable
  archival - old and rarely accessed, candidate for archival

Scope (negative):
- No file writes
- No VectorMemory updates
- No tier mutation
- No Telegram commands
- Pure calculation only
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

_TIER_BONUS = {
    "core": 20,
    "recall": 10,
    "archival": 0,
    "episodic": -10,
}

_LEVEL_THRESHOLDS = [
    (75, "stable"),
    (45, "warming"),
    (20, "fresh"),
    (0,  "archival"),
]


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s))
    except Exception:
        return None


def _age_days(created_at: str | None) -> float:
    dt = _parse_dt(created_at)
    if dt is None:
        return 0.0
    return max(0.0, (datetime.now() - dt).total_seconds() / 86400)


class MemoryMaturityScorer:
    """Score memory record maturity. Pure calculation, zero side effects."""

    def score(self, record: dict[str, Any]) -> dict[str, Any]:
        """Return maturity assessment dict."""
        age = _age_days(record.get("created_at"))
        access_count = int(record.get("access_count") or 0)
        tier = str(record.get("tier") or "recall").lower()
        confidence = int(record.get("confidence") or 50)

        # age score: 0-30 points (cap at 90 days)
        age_score = min(30, age / 3)

        # access score: 0-30 points (cap at 10 accesses)
        access_score = min(30, access_count * 3)

        # confidence score: 0-20 points
        confidence_score = confidence * 0.20

        # tier bonus: -10 to +20
        tier_bonus = _TIER_BONUS.get(tier, 0)

        raw = age_score + access_score + confidence_score + tier_bonus
        maturity_score = max(0, min(100, int(raw)))

        # archival override: old + low access + archival tier
        if age > 90 and access_count == 0 and tier == "archival":
            maturity_score = max(maturity_score, 0)
            level = "archival"
        else:
            level = "archival"
            for threshold, name in _LEVEL_THRESHOLDS:
                if maturity_score >= threshold:
                    level = name
                    break

        return {
            "maturity_score": maturity_score,
            "maturity_level": level,
            "reason": f"age={age:.1f}d access={access_count} tier={tier} confidence={confidence}",
            "signals": {
                "age_days": round(age, 1),
                "access_count": access_count,
                "tier": tier,
                "confidence": confidence,
                "age_score": round(age_score, 1),
                "access_score": round(access_score, 1),
                "confidence_score": round(confidence_score, 1),
                "tier_bonus": tier_bonus,
            },
        }
