"""C1.2 Conversation memory candidate queue tests.

Guards conversation-derived memory candidate routing:
- low-value messages are not queued
- semantic/vector routes become pending review candidates
- daily/episodic routes are not queued here
- sensitive routes become review candidates
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from agents.memory_candidate_queue import MemoryCandidateQueue


def _queue():
    td = TemporaryDirectory()
    q = MemoryCandidateQueue(root=Path(td.name))
    return td, q


def test_low_value_message_is_not_queued():
    td, q = _queue()
    try:
        result = q.add_conversation_candidate("tamam")

        assert result["ok"] is True
        assert result["queued"] is False
        assert result["reason"] == "route_not_review_candidate"
        assert q.list_pending(limit=10) == []
    finally:
        td.cleanup()


def test_explicit_preference_is_queued_as_semantic_vector_candidate():
    td, q = _queue()
    try:
        result = q.add_conversation_candidate("bunu hatırla: AC/DC ve rock müzik seviyorum")

        assert result["ok"] is True
        assert result["queued"] is True

        candidate = result["candidate"]
        assert candidate["source_type"] == "conversation"
        assert candidate["status"] == "pending_review"
        assert candidate["memory_type"] == "semantic"
        assert candidate["storage_target"] == "vector"
        assert candidate["sensitivity"] == "normal"
        assert "conversation" in candidate["tags"]
        assert "c1_2_review" in candidate["tags"]
        assert "explicit_save" in candidate["tags"]
        assert candidate["delete_id"].startswith("md_")

        pending = q.list_pending(limit=10)
        assert len(pending) == 1
        assert pending[0]["id"] == candidate["id"]
    finally:
        td.cleanup()


def test_daily_context_is_not_queued_as_review_candidate():
    td, q = _queue()
    try:
        result = q.add_conversation_candidate("bugün hava yağmurlu, motosiklete çıkmayacağım")

        assert result["ok"] is True
        assert result["queued"] is False
        assert result["route"]["memory_type"] == "episodic"
        assert result["route"]["storage_target"] == "daily_summary"
        assert q.list_pending(limit=10) == []
    finally:
        td.cleanup()


def test_sensitive_explicit_save_is_queued_for_review():
    td, q = _queue()
    try:
        result = q.add_conversation_candidate("telefon numaram 555 123 45 67 bunu kaydet")

        assert result["ok"] is True
        assert result["queued"] is True

        candidate = result["candidate"]
        assert candidate["source_type"] == "conversation"
        assert candidate["status"] == "pending_review"
        assert candidate["memory_type"] == "sensitive_review"
        assert candidate["storage_target"] == "review_queue"
        assert candidate["sensitivity"] == "sensitive"
        assert "sensitive" in candidate["tags"]
        assert "explicit_save" in candidate["tags"]

        pending = q.list_pending(limit=10)
        assert len(pending) == 1
        assert pending[0]["id"] == candidate["id"]
    finally:
        td.cleanup()


def test_duplicate_conversation_candidate_is_not_duplicated():
    td, q = _queue()
    try:
        first = q.add_conversation_candidate("bunu hatırla: AC/DC ve rock müzik seviyorum")
        second = q.add_conversation_candidate("bunu hatırla: AC/DC ve rock müzik seviyorum")

        assert first["queued"] is True
        assert second["queued"] is True

        pending = q.list_pending(limit=10)
        assert len(pending) == 1
        assert pending[0]["id"] == first["candidate"]["id"]
    finally:
        td.cleanup()
