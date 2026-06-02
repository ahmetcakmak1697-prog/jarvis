"""C1.3 Telegram memory expiry command tests."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta

from agents.memory_candidate_queue import MemoryCandidateQueue
from tools.telegram_agent import cmd_memory_expire


def test_cmd_memory_expire_output_shape():
    text = cmd_memory_expire()

    assert "Hafiza aday TTL temizligi tamamlandi." in text
    assert "Degisen:" in text
    assert "Once pending:" in text
    assert "Sonra pending:" in text
    assert "Kayitlar silinmedi" in text


def test_expire_old_runtime_logic_with_temp_queue():
    with TemporaryDirectory() as td:
        q = MemoryCandidateQueue(root=Path(td))

        now = datetime.now()
        old = (now - timedelta(days=1)).isoformat(timespec="seconds")
        future = (now + timedelta(days=1)).isoformat(timespec="seconds")

        q._save([
            {
                "id": "mc_old_pending",
                "created_at": old,
                "source_type": "conversation",
                "mode": "conversation",
                "status": "pending_review",
                "query": "old pending",
                "summary": "old pending",
                "confidence": 60,
                "tier": "temporary_candidate",
                "source_urls": [],
                "source_scores": [],
                "retrieved_at": old,
                "expires_at": old,
                "tags": ["test"],
            },
            {
                "id": "mc_future_pending",
                "created_at": old,
                "source_type": "conversation",
                "mode": "conversation",
                "status": "pending_review",
                "query": "future pending",
                "summary": "future pending",
                "confidence": 60,
                "tier": "temporary_candidate",
                "source_urls": [],
                "source_scores": [],
                "retrieved_at": old,
                "expires_at": future,
                "tags": ["test"],
            },
        ])

        result = q.expire_old(now=now)
        data = q._load()
        statuses = {item["id"]: item["status"] for item in data}

        assert result["changed"] == 1
        assert statuses["mc_old_pending"] == "expired"
        assert statuses["mc_future_pending"] == "pending_review"
