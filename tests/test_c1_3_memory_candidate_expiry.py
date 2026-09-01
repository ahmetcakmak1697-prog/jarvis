"""C1.3 Memory candidate TTL expiry tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from agents.memory_candidate_queue import MemoryCandidateQueue


def _item(candidate_id: str, status: str, expires_at: str) -> dict:
    return {
        "id": candidate_id,
        "created_at": expires_at,
        "source_type": "conversation",
        "mode": "conversation",
        "status": status,
        "query": candidate_id,
        "summary": candidate_id,
        "confidence": 60,
        "tier": "temporary_candidate",
        "source_urls": [],
        "source_scores": [],
        "retrieved_at": expires_at,
        "expires_at": expires_at,
        "tags": ["test"],
    }


def test_expire_old_marks_pending_and_deferred_only():
    with TemporaryDirectory() as td:
        q = MemoryCandidateQueue(root=Path(td))

        now = datetime.now()
        old = (now - timedelta(days=1)).isoformat(timespec="seconds")
        future = (now + timedelta(days=1)).isoformat(timespec="seconds")

        q._save([
            _item("mc_old_pending", "pending_review", old),
            _item("mc_old_deferred", "deferred", old),
            _item("mc_future_pending", "pending_review", future),
            _item("mc_old_rejected", "rejected", old),
            _item("mc_old_stored", "stored", old),
        ])

        result = q.expire_old(now=now)
        data = q._load()
        statuses = {item["id"]: item["status"] for item in data}

        assert result["ok"] is True
        assert result["changed"] == 2
        assert set(result["expired_ids"]) == {"mc_old_pending", "mc_old_deferred"}

        assert statuses["mc_old_pending"] == "expired"
        assert statuses["mc_old_deferred"] == "expired"
        assert statuses["mc_future_pending"] == "pending_review"
        assert statuses["mc_old_rejected"] == "rejected"
        assert statuses["mc_old_stored"] == "stored"

        expired_items = [item for item in data if item["status"] == "expired"]
        assert all(item["user_decision"] == "expired" for item in expired_items)
        assert all(item.get("decided_at") for item in expired_items)


def test_expire_old_writes_audit_events():
    with TemporaryDirectory() as td:
        q = MemoryCandidateQueue(root=Path(td))

        now = datetime.now()
        old = (now - timedelta(days=1)).isoformat(timespec="seconds")

        q._save([
            _item("mc_old_pending", "pending_review", old),
            _item("mc_old_deferred", "deferred", old),
        ])

        result = q.expire_old(now=now)
        audit = q.audit.tail(10)
        events = [item.get("event") for item in audit]

        assert result["changed"] == 2
        assert events.count("memory_candidate_expired") == 2

        candidate_ids = {item.get("candidate_id") for item in audit}
        assert "mc_old_pending" in candidate_ids
        assert "mc_old_deferred" in candidate_ids


def test_expire_old_is_idempotent():
    with TemporaryDirectory() as td:
        q = MemoryCandidateQueue(root=Path(td))

        now = datetime.now()
        old = (now - timedelta(days=1)).isoformat(timespec="seconds")

        q._save([
            _item("mc_old_pending", "pending_review", old),
        ])

        first = q.expire_old(now=now)
        second = q.expire_old(now=now)

        assert first["changed"] == 1
        assert second["changed"] == 0

        data = q._load()
        assert data[0]["status"] == "expired"
