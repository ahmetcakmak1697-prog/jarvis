"""C1.6G-lite source-linked provenance resolver tests."""

from __future__ import annotations


def _make_queue(tmp_path, candidates):
    import json
    root = tmp_path / "jarvis"
    (root / "memory").mkdir(parents=True, exist_ok=True)
    (root / "memory" / "memory_candidates.json").write_text(
        json.dumps(candidates), encoding="utf-8"
    )
    return root


def test_resolver_returns_list():
    from agents.memory_provenance import MemoryProvenanceResolver
    r = MemoryProvenanceResolver(candidates=[])
    links = r.resolve(["src_1"])
    assert isinstance(links, list)


def test_resolver_resolves_existing_source():
    from agents.memory_provenance import MemoryProvenanceResolver
    candidates = [
        {"id": "src_1", "delete_id": "src_1", "status": "stored",
         "source_type": "conversation", "theme": "jarvis",
         "summary": "Jarvis uzerinde calistik."},
    ]
    r = MemoryProvenanceResolver(candidates=candidates)
    links = r.resolve(["src_1"])
    assert len(links) == 1
    assert links[0]["id"] == "src_1"
    assert links[0]["resolved"] is True
    assert links[0]["status"] == "stored"


def test_resolver_marks_missing_source_unresolved():
    from agents.memory_provenance import MemoryProvenanceResolver
    r = MemoryProvenanceResolver(candidates=[])
    links = r.resolve(["ghost_id"])
    assert len(links) == 1
    assert links[0]["id"] == "ghost_id"
    assert links[0]["resolved"] is False


def test_resolver_mixed_sources():
    from agents.memory_provenance import MemoryProvenanceResolver
    candidates = [
        {"id": "real_1", "delete_id": "real_1", "status": "stored",
         "source_type": "conversation", "summary": "Gercek kaynak."},
    ]
    r = MemoryProvenanceResolver(candidates=candidates)
    links = r.resolve(["real_1", "ghost_1"])
    assert len(links) == 2
    by_id = {l["id"]: l for l in links}
    assert by_id["real_1"]["resolved"] is True
    assert by_id["ghost_1"]["resolved"] is False


def test_resolver_summary_preview_truncated():
    from agents.memory_provenance import MemoryProvenanceResolver
    long_summary = "x" * 500
    candidates = [
        {"id": "src_1", "delete_id": "src_1", "status": "stored",
         "source_type": "conversation", "summary": long_summary},
    ]
    r = MemoryProvenanceResolver(candidates=candidates)
    links = r.resolve(["src_1"])
    assert len(links[0]["summary_preview"]) <= 160


def test_resolver_handles_blank_ids():
    from agents.memory_provenance import MemoryProvenanceResolver
    r = MemoryProvenanceResolver(candidates=[])
    links = r.resolve(["", "   ", None])
    assert links == []


def test_resolver_summary_includes_resolved_count():
    from agents.memory_provenance import MemoryProvenanceResolver
    candidates = [
        {"id": "real_1", "delete_id": "real_1", "status": "stored",
         "source_type": "conversation", "summary": "Gercek."},
    ]
    r = MemoryProvenanceResolver(candidates=candidates)
    result = r.summarize(["real_1", "ghost_1"])
    assert result["total"] == 2
    assert result["resolved"] == 1
    assert result["unresolved"] == 1
    assert len(result["links"]) == 2
