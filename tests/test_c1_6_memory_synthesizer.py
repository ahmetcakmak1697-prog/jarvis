"""C1.6A Memory Synthesizer state tests."""

from __future__ import annotations

from pathlib import Path

from agents.memory_synthesizer import MemorySynthesizerStore, SynthesisState, SCHEMA_VERSION


def test_synthesizer_returns_default_when_no_file(tmp_path):
    store = MemorySynthesizerStore(path=tmp_path / "synthesis_state.json")
    state = store.load_or_default()

    assert isinstance(state, SynthesisState)
    assert state.schema_version == SCHEMA_VERSION
    assert state.processed_delete_ids == []
    assert state.generated_count == 0
    assert state.last_run == ""


def test_synthesizer_save_and_load_roundtrip(tmp_path):
    store = MemorySynthesizerStore(path=tmp_path / "synthesis_state.json")
    state = store.load_or_default()
    state.last_run = "2026-06-04T12:00:00"
    state.generated_count = 3
    store.save(state)

    loaded = store.load_or_default()
    assert loaded.last_run == "2026-06-04T12:00:00"
    assert loaded.generated_count == 3
    assert loaded.updated_at != ""


def test_synthesizer_broken_json_falls_back_to_default(tmp_path):
    path = tmp_path / "synthesis_state.json"
    path.write_text("{ not valid json }", encoding="utf-8")

    store = MemorySynthesizerStore(path=path)
    state = store.load_or_default()

    assert isinstance(state, SynthesisState)
    assert state.processed_delete_ids == []


def test_synthesizer_duplicate_guard(tmp_path):
    store = MemorySynthesizerStore(path=tmp_path / "synthesis_state.json")

    store.mark_processed("md_abc123")
    store.mark_processed("md_abc123")
    store.mark_processed("md_def456")

    state = store.load_or_default()
    assert state.processed_delete_ids.count("md_abc123") == 1
    assert "md_def456" in state.processed_delete_ids
    assert len(state.processed_delete_ids) == 2


def test_synthesizer_is_processed_returns_correct(tmp_path):
    store = MemorySynthesizerStore(path=tmp_path / "synthesis_state.json")

    assert store.is_processed("md_xyz") is False
    store.mark_processed("md_xyz")
    assert store.is_processed("md_xyz") is True


def test_synthesizer_default_path_is_memory_dir():
    store = MemorySynthesizerStore()
    assert "memory" in str(store.path)
    assert "synthesis_state.json" in str(store.path)


# C1.6B tests

def _make_queue(tmp_path, candidates):
    import json
    queue_root = tmp_path / "jarvis"
    (queue_root / "memory").mkdir(parents=True, exist_ok=True)
    (queue_root / "memory" / "memory_candidates.json").write_text(
        json.dumps(candidates), encoding="utf-8"
    )
    return queue_root


def test_collector_returns_empty_when_no_candidates(tmp_path):
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector
    queue_root = _make_queue(tmp_path, [])
    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root,
        state_path=tmp_path / "synthesis_state.json",
    )
    assert collector.collect() == []


def test_collector_zero_limit_returns_empty(tmp_path):
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector
    candidates = [{"id": "1", "source_type": "conversation", "status": "stored",
                   "summary": "icerik", "delete_id": "md_001"}]
    queue_root = _make_queue(tmp_path, candidates)
    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root, state_path=tmp_path / "synthesis_state.json")
    assert collector.collect(limit=0) == []
    assert collector.collect(limit=-1) == []


def test_collector_filters_web_research(tmp_path):
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector
    candidates = [
        {"id": "1", "source_type": "web_research", "status": "stored",
         "summary": "web result", "delete_id": "md_001"},
        {"id": "2", "source_type": "conversation", "status": "stored",
         "summary": "konusma ozeti", "delete_id": "md_002"},
    ]
    queue_root = _make_queue(tmp_path, candidates)
    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root, state_path=tmp_path / "synthesis_state.json")
    result = collector.collect()
    assert len(result) == 1
    assert result[0]["source_type"] == "conversation"


def test_collector_filters_rejected_and_deferred_status(tmp_path):
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector
    candidates = [
        {"id": "1", "source_type": "conversation", "status": "rejected",
         "summary": "reddedilen", "delete_id": "md_001"},
        {"id": "2", "source_type": "conversation", "status": "deferred",
         "summary": "ertelenen", "delete_id": "md_002"},
        {"id": "3", "source_type": "conversation", "status": "pending_review",
         "summary": "bekleyen", "delete_id": "md_003"},
    ]
    queue_root = _make_queue(tmp_path, candidates)
    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root, state_path=tmp_path / "synthesis_state.json")
    result = collector.collect()
    assert len(result) == 1
    assert result[0]["status"] == "pending_review"


def test_collector_skips_sensitive_review_candidates(tmp_path):
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector
    candidates = [
        {"id": "1", "source_type": "conversation", "status": "pending_review",
         "memory_type": "sensitive_review", "summary": "hassas bilgi", "delete_id": "md_001"},
        {"id": "2", "source_type": "conversation", "status": "stored",
         "memory_type": "semantic", "summary": "normal bilgi", "delete_id": "md_002"},
    ]
    queue_root = _make_queue(tmp_path, candidates)
    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root, state_path=tmp_path / "synthesis_state.json")
    result = collector.collect()
    assert len(result) == 1
    assert result[0]["delete_id"] == "md_002"


def test_collector_skips_expired_candidates(tmp_path):
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector
    candidates = [
        {"id": "1", "source_type": "conversation", "status": "stored",
         "summary": "suresi dolmus", "delete_id": "md_001", "expires_at": "2020-01-01T00:00:00"},
        {"id": "2", "source_type": "conversation", "status": "stored",
         "summary": "gecerli", "delete_id": "md_002", "expires_at": "2099-01-01T00:00:00"},
        {"id": "3", "source_type": "conversation", "status": "stored",
         "summary": "expires_at yok", "delete_id": "md_003"},
    ]
    queue_root = _make_queue(tmp_path, candidates)
    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root, state_path=tmp_path / "synthesis_state.json")
    result = collector.collect()
    assert len(result) == 2
    ids = {r["delete_id"] for r in result}
    assert "md_001" not in ids
    assert "md_002" in ids
    assert "md_003" in ids


def test_collector_skips_already_processed(tmp_path):
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector, MemorySynthesizerStore
    candidates = [
        {"id": "1", "source_type": "conversation", "status": "stored",
         "summary": "islenmis", "delete_id": "md_already"},
        {"id": "2", "source_type": "conversation", "status": "stored",
         "summary": "yeni", "delete_id": "md_new"},
    ]
    queue_root = _make_queue(tmp_path, candidates)
    state_path = tmp_path / "synthesis_state.json"
    MemorySynthesizerStore(path=state_path).mark_processed("md_already")
    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root, state_path=state_path)
    result = collector.collect()
    assert len(result) == 1
    assert result[0]["delete_id"] == "md_new"


def test_collector_enriches_with_synthesis_text(tmp_path):
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector
    candidates = [
        {"id": "1", "source_type": "conversation", "status": "stored",
         "summary": "Arduino ogreniyorum", "delete_id": "md_001"},
        {"id": "2", "source_type": "conversation", "status": "stored",
         "user_msg": "summary yok user_msg var", "delete_id": "md_002"},
    ]
    queue_root = _make_queue(tmp_path, candidates)
    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root, state_path=tmp_path / "synthesis_state.json")
    result = collector.collect()
    assert len(result) == 2
    assert result[0]["_synthesis_text"] == "Arduino ogreniyorum"
    assert result[1]["_synthesis_text"] == "summary yok user_msg var"


def test_collector_skips_empty_text(tmp_path):
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector
    candidates = [
        {"id": "1", "source_type": "conversation", "status": "stored",
         "summary": "", "delete_id": "md_001"},
        {"id": "2", "source_type": "conversation", "status": "stored",
         "summary": "gercek icerik", "delete_id": "md_002"},
    ]
    queue_root = _make_queue(tmp_path, candidates)
    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root, state_path=tmp_path / "synthesis_state.json")
    result = collector.collect()
    assert len(result) == 1
    assert result[0]["_synthesis_text"] == "gercek icerik"


def test_collector_summary_texts(tmp_path):
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector
    candidates = [
        {"id": "1", "source_type": "conversation", "status": "stored",
         "summary": "Arduino ogreniyorum", "delete_id": "md_001"},
        {"id": "2", "source_type": "conversation", "status": "stored",
         "summary": "Jarvis projesi devam ediyor", "delete_id": "md_002"},
    ]
    queue_root = _make_queue(tmp_path, candidates)
    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root, state_path=tmp_path / "synthesis_state.json")
    texts = collector.summary_texts()
    assert len(texts) == 2
    assert any("Arduino" in t for t in texts)
    assert any("Jarvis" in t for t in texts)


# C1.6C tests

def test_synthesizer_below_threshold_no_proposal(tmp_path):
    from agents.memory_synthesizer import KeywordFrequencySynthesizer
    # Her tema en fazla 1 adayda geciyor; min_mentions=2 ile hicbir proposal cikmamali.
    candidates = [
        {"_synthesis_text": "bugun arduino ile biraz ugrastim"},
        {"_synthesis_text": "jarvis projesinde commit attim"},
        {"_synthesis_text": "eshot raporu uzerinde calistim"},
    ]
    synth = KeywordFrequencySynthesizer(min_mentions=2)
    proposals = synth.synthesize(candidates)
    assert proposals == []

# C1.6C safety and quality tests

def test_c1_6c_above_threshold_and_source_ids():
    from agents.memory_synthesizer import KeywordFrequencySynthesizer

    candidates = [
        {"delete_id": "c1", "_synthesis_text": "bugun eshot telemetri raporu hazirladim"},
        {"delete_id": "c2", "_synthesis_text": "jarvis icin roadmap guncellendi"},
        {"delete_id": "c3", "_synthesis_text": "eshot ihlal karnesi olusturuldu"},
        {"delete_id": "c4", "_synthesis_text": "eshot rolanti sureleri hesaplandi"},
    ]

    synth = KeywordFrequencySynthesizer(min_mentions=3)
    proposals = synth.synthesize(candidates)

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["theme"] == "eshot"
    assert proposal["source_count"] == 3
    assert proposal["confidence"] == 80
    assert set(proposal["source_ids"]) == {"c1", "c3", "c4"}
    assert proposal["proposal_type"] == "synthesized_memory"


def test_c1_6c_turkish_fold_and_suffix_matching():
    from agents.memory_synthesizer import KeywordFrequencySynthesizer

    candidates = [
        {"id": "t1", "_synthesis_text": "ESHOT \u0130HLAL tespiti yapildi"},
        {"id": "t2", "_synthesis_text": "\u015eofor rApOrU incelendi"},
        {"id": "t3", "_synthesis_text": "R\u00d6LANT\u0130 suresi cok yuksek"},
    ]

    synth = KeywordFrequencySynthesizer(min_mentions=3)
    proposals = synth.synthesize(candidates)

    assert len(proposals) == 1
    assert proposals[0]["theme"] == "eshot"
    assert proposals[0]["source_count"] == 3
    assert set(proposals[0]["source_ids"]) == {"t1", "t2", "t3"}


def test_c1_6c_sensitive_candidates_do_not_contribute_to_threshold():
    from agents.memory_synthesizer import KeywordFrequencySynthesizer

    candidates = [
        {"id": "s1", "_synthesis_text": "jarvis repoya pushladim"},
        {
            "id": "s2",
            "_synthesis_text": "jarvis projesi hakkinda ozel not",
            "data_class": "personal-sensitive",
        },
        {
            "id": "s3",
            "_synthesis_text": "jarvis gizli kod",
            "sensitive_review_required": True,
        },
    ]

    synth = KeywordFrequencySynthesizer(min_mentions=3)
    proposals = synth.synthesize(candidates)

    assert proposals == []


def test_c1_6c_returns_proposals_only_without_side_effect_fields():
    from agents.memory_synthesizer import KeywordFrequencySynthesizer

    candidates = [
        {"delete_id": "a1", "_synthesis_text": "arduino esp32 maker calismasi yapildi"},
        {"delete_id": "a2", "_synthesis_text": "elektronik breadboard jumper notlari alindi"},
    ]

    synth = KeywordFrequencySynthesizer(min_mentions=2)
    proposals = synth.synthesize(candidates)

    assert len(proposals) == 1
    proposal = proposals[0]
    assert set(proposal.keys()) == {
        "theme",
        "summary",
        "source_count",
        "confidence",
        "source_ids",
        "proposal_type",
    }
    assert "memory" not in proposal
    assert "vector" not in proposal
    assert "approval" not in proposal

# C1.6D-debt public queue API tests

def test_memory_candidate_queue_list_candidates_public_api(tmp_path):
    import json
    from agents.memory_candidate_queue import MemoryCandidateQueue

    q = MemoryCandidateQueue(root=tmp_path)
    q.path.write_text(
        json.dumps(
            [
                {"id": "c1", "status": "pending_review", "summary": "one"},
                {"id": "c2", "status": "approved", "summary": "two"},
                {"id": "c3", "status": "stored", "summary": "three"},
                {"id": "c4", "status": "rejected", "summary": "four"},
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    all_items = q.list_candidates()
    assert [item["id"] for item in all_items] == ["c1", "c2", "c3", "c4"]

    active_items = q.list_candidates(statuses={"pending_review", "approved", "stored"})
    assert [item["id"] for item in active_items] == ["c1", "c2", "c3"]

    limited = q.list_candidates(limit=2)
    assert [item["id"] for item in limited] == ["c3", "c4"]

    assert q.list_all() == all_items


def test_collector_uses_public_list_candidates_api(tmp_path):
    import json
    from agents.memory_synthesizer import MemorySynthesizerCandidateCollector

    queue_root = tmp_path / "queue"
    queue_path = queue_root / "memory" / "memory_candidates.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            [
                {
                    "id": "1",
                    "source_type": "conversation",
                    "status": "pending_review",
                    "memory_type": "semantic",
                    "summary": "jarvis roadmap notu",
                    "delete_id": "md_001",
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root,
        state_path=tmp_path / "synthesis_state.json",
    )

    calls = {"list_candidates": 0}
    original_list_candidates = collector.queue.list_candidates

    def spy_list_candidates(*args, **kwargs):
        calls["list_candidates"] += 1
        return original_list_candidates(*args, **kwargs)

    collector.queue.list_candidates = spy_list_candidates

    result = collector.collect()
    assert calls["list_candidates"] == 1
    assert len(result) == 1
    assert result[0]["delete_id"] == "md_001"
    assert result[0]["_synthesis_text"] == "jarvis roadmap notu"
