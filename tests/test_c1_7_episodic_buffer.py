"""C1.7 EpisodicBuffer tests."""
from __future__ import annotations


def test_append_event_creates_jsonl_record(tmp_path):
    from agents.episodic_buffer import EpisodicBuffer
    b = EpisodicBuffer(root=tmp_path)
    result = b.append_event("coding", "C1.7 episodic buffer test event", tags=["c1.7"])
    assert result["ok"] is True
    assert result["event"]["event_type"] == "coding"
    assert result["event"]["summary"] == "C1.7 episodic buffer test event"
    path = tmp_path / "memory" / "episodic_buffer.jsonl"
    assert path.exists()
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_list_recent_returns_newest_first(tmp_path):
    from agents.episodic_buffer import EpisodicBuffer
    b = EpisodicBuffer(root=tmp_path)
    b.append_event("first", "ilk olay")
    b.append_event("second", "ikinci olay")
    recent = b.list_recent(limit=2)
    assert len(recent) == 2
    assert recent[0]["event_type"] == "second"
    assert recent[1]["event_type"] == "first"


def test_list_recent_respects_limit(tmp_path):
    from agents.episodic_buffer import EpisodicBuffer
    b = EpisodicBuffer(root=tmp_path)
    for i in range(5):
        b.append_event("note", f"olay {i}")
    assert len(b.list_recent(limit=3)) == 3


def test_append_event_rejects_blank_summary(tmp_path):
    from agents.episodic_buffer import EpisodicBuffer
    b = EpisodicBuffer(root=tmp_path)
    result = b.append_event("note", "   ")
    assert result["ok"] is False
    assert result["reason"] == "blank_summary"


def test_stats_counts_events(tmp_path):
    from agents.episodic_buffer import EpisodicBuffer
    b = EpisodicBuffer(root=tmp_path)
    b.append_event("coding", "bir")
    b.append_event("coding", "iki")
    b.append_event("note", "uc")
    stats = b.stats()
    assert stats["total"] == 3
    assert stats["by_type"]["coding"] == 2
    assert stats["by_type"]["note"] == 1


def test_prune_keeps_max_items(tmp_path):
    from agents.episodic_buffer import EpisodicBuffer
    b = EpisodicBuffer(root=tmp_path)
    for i in range(6):
        b.append_event("note", f"olay {i}")
    result = b.prune(max_items=3)
    recent = b.list_recent(limit=10)
    assert result["ok"] is True
    assert result["kept"] == 3
    assert len(recent) == 3
    assert recent[0]["summary"] == "olay 5"
    assert recent[-1]["summary"] == "olay 3"


def test_prune_rewrites_jsonl_file(tmp_path):
    """Prune sonrasi JSONL dosyasinda gercekten max_items satir olmali."""
    from agents.episodic_buffer import EpisodicBuffer
    b = EpisodicBuffer(root=tmp_path)
    for i in range(6):
        b.append_event("note", f"olay {i}")
    b.prune(max_items=3)
    path = tmp_path / "memory" / "episodic_buffer.jsonl"
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 3


def test_event_has_created_at(tmp_path):
    """Her event'in created_at alani olmali."""
    from agents.episodic_buffer import EpisodicBuffer
    b = EpisodicBuffer(root=tmp_path)
    result = b.append_event("coding", "test")
    assert "created_at" in result["event"]
    assert result["event"]["created_at"]
