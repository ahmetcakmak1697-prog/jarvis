"""C1.5 MemoryCandidateWriter route-aware store guard tests."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from agents.memory_candidate_queue import MemoryCandidateQueue
from agents.memory_candidate_writer import MemoryCandidateWriter


class FakeMemory:
    def __init__(self):
        self.calls = []

    def remember(self, user_msg, jarvis_msg, meta=None):
        self.calls.append((user_msg, jarvis_msg, meta or {}))
        return "fake_memory_id"


def _writer_with_fake_memory(root: Path):
    writer = MemoryCandidateWriter(root=root)
    fake = FakeMemory()
    writer.memory = fake
    return writer, fake


def test_semantic_conversation_candidate_is_stored_with_c1_metadata():
    with TemporaryDirectory() as td:
        root = Path(td)
        q = MemoryCandidateQueue(root=root)

        candidate = q.add_conversation_candidate(
            "bunu hatırla: AC/DC ve rock müzik seviyorum",
            tags=["test_semantic"],
        )["candidate"]

        writer, fake = _writer_with_fake_memory(root)
        result = writer.approve_and_store(candidate["id"])

        assert result["ok"] is True
        assert result["stored"] is True
        assert len(fake.calls) == 1

        user_msg, jarvis_msg, meta = fake.calls[0]

        assert "AC/DC" in user_msg
        assert "AC/DC" in jarvis_msg

        assert meta["source_type"] == "conversation"
        assert meta["schema_version"] == "c1.1"
        assert meta["memory_type"] == "semantic"
        assert meta["storage_target"] == "vector"
        assert meta["sensitivity"] == "normal"
        assert meta["memory_action"] == "keep_long_term"
        assert meta["allow_vector"] is True
        assert meta["requires_review"] is False
        assert meta["delete_id"].startswith("md_")
        assert "conversation" in meta["memory_tags"]
        assert "c1_2_review" in meta["memory_tags"]
        assert "explicit_save" in meta["memory_tags"]
        assert "test_semantic" in meta["memory_tags"]


def test_sensitive_conversation_candidate_is_not_stored_even_when_approved():
    with TemporaryDirectory() as td:
        root = Path(td)
        q = MemoryCandidateQueue(root=root)

        candidate = q.add_conversation_candidate(
            "telefon numaram 555 123 45 67 bunu kaydet",
            tags=["test_sensitive"],
        )["candidate"]

        writer, fake = _writer_with_fake_memory(root)
        result = writer.approve_and_store(candidate["id"])

        assert result["ok"] is False
        assert result["stored"] is False
        assert "C1 route" in result["error"]
        assert len(fake.calls) == 0

        stored_candidate = writer.queue.get(candidate["id"])
        assert stored_candidate["status"] == "approved"
        assert stored_candidate["user_decision"] == "approved"


def test_review_queue_route_is_blocked_before_policy_write():
    with TemporaryDirectory() as td:
        root = Path(td)
        q = MemoryCandidateQueue(root=root)

        candidate = q.add_conversation_candidate(
            "bunu hatırla: api key secret-123",
            tags=["test_secret"],
        )["candidate"]

        writer, fake = _writer_with_fake_memory(root)
        result = writer.approve_and_store(candidate["id"])

        assert result["stored"] is False
        assert "C1 route" in result["error"]
        assert len(fake.calls) == 0

        policy = result["policy"]
        assert policy["storage_target"] == "review_queue"
        assert policy["sensitivity"] == "secret"
