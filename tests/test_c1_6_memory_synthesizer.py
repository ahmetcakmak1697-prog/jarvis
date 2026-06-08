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

# C1.6D synthesis proposal queue tests

def test_queue_add_synthesis_candidate_creates_pending_review_item(tmp_path):
    from agents.memory_candidate_queue import MemoryCandidateQueue

    q = MemoryCandidateQueue(root=tmp_path)

    proposal = {
        "theme": "jarvis",
        "summary": "Jarvis gelistirme calismalari aktif gorunuyor.",
        "source_count": 3,
        "confidence": 80,
        "source_ids": ["md_001", "md_002", "md_003"],
        "proposal_type": "synthesized_memory",
    }

    result = q.add_synthesis_candidate(proposal)

    assert result["ok"] is True
    assert result["queued"] is True

    candidate = result["candidate"]
    assert candidate["source_type"] == "synthesis"
    assert candidate["mode"] == "memory_synthesis"
    assert candidate["status"] == "pending_review"
    assert candidate["query"] == "synthesis:jarvis"
    assert candidate["summary"] == "Jarvis gelistirme calismalari aktif gorunuyor."
    assert candidate["confidence"] == 80
    assert candidate["memory_type"] == "semantic"
    assert candidate["storage_target"] == "review_queue"
    assert candidate["sensitivity"] == "normal"
    assert candidate["proposal_type"] == "synthesized_memory"
    assert candidate["theme"] == "jarvis"
    assert candidate["source_count"] == 3
    assert candidate["source_ids"] == ["md_001", "md_002", "md_003"]
    assert "synthesis" in candidate["tags"]
    assert "c1_6" in candidate["tags"]
    assert "theme:jarvis" in candidate["tags"]

    pending = q.list_pending(limit=10)
    assert len(pending) == 1
    assert pending[0]["id"] == candidate["id"]


def test_queue_add_synthesis_candidate_is_idempotent(tmp_path):
    from agents.memory_candidate_queue import MemoryCandidateQueue

    q = MemoryCandidateQueue(root=tmp_path)

    proposal = {
        "theme": "eshot",
        "summary": "ESHOT raporlama ve telemetri calismalari aktif gorunuyor.",
        "source_count": 3,
        "confidence": 80,
        "source_ids": ["a", "b", "c"],
        "proposal_type": "synthesized_memory",
    }

    first = q.add_synthesis_candidate(proposal)
    second = q.add_synthesis_candidate(proposal)

    assert first["ok"] is True
    assert second["ok"] is True
    assert first["candidate"]["id"] == second["candidate"]["id"]

    all_items = q.list_candidates()
    assert len(all_items) == 1
    assert all_items[0]["source_type"] == "synthesis"


def test_queue_add_synthesis_candidate_rejects_non_synthesis_proposal(tmp_path):
    from agents.memory_candidate_queue import MemoryCandidateQueue

    q = MemoryCandidateQueue(root=tmp_path)

    result = q.add_synthesis_candidate(
        {
            "theme": "jarvis",
            "summary": "bad proposal",
            "source_count": 3,
            "confidence": 80,
            "source_ids": ["x", "y", "z"],
            "proposal_type": "not_synthesis",
        }
    )

    assert result["ok"] is False
    assert result["queued"] is False
    assert result["reason"] == "invalid_proposal_type"
    assert q.list_candidates() == []

# C1.6D transactional submitter tests

def test_synthesis_submitter_marks_sources_processed_after_successful_queue_write(tmp_path):
    from agents.memory_candidate_queue import MemoryCandidateQueue
    from agents.memory_synthesizer import (
        MemorySynthesisReviewSubmitter,
        MemorySynthesizerStore,
    )

    queue_root = tmp_path / "queue"
    state_path = tmp_path / "synthesis_state.json"

    submitter = MemorySynthesisReviewSubmitter(
        queue=MemoryCandidateQueue(root=queue_root),
        store=MemorySynthesizerStore(path=state_path),
    )

    proposal = {
        "theme": "jarvis",
        "summary": "Jarvis gelistirme calismalari aktif gorunuyor.",
        "source_count": 2,
        "confidence": 70,
        "source_ids": ["md_001", "md_002"],
        "proposal_type": "synthesized_memory",
    }

    result = submitter.submit([proposal])

    assert result["ok"] is True
    assert result["submitted_count"] == 1
    assert result["processed_source_ids"] == ["md_001", "md_002"]

    queued = MemoryCandidateQueue(root=queue_root).list_candidates()
    assert len(queued) == 1
    assert queued[0]["source_type"] == "synthesis"
    assert queued[0]["status"] == "pending_review"

    state = MemorySynthesizerStore(path=state_path).load_or_default()
    assert state.is_processed("md_001") is True
    assert state.is_processed("md_002") is True


def test_synthesis_submitter_does_not_mark_processed_when_queue_write_fails(tmp_path):
    from agents.memory_synthesizer import (
        MemorySynthesisReviewSubmitter,
        MemorySynthesizerStore,
    )

    class FailingQueue:
        def add_synthesis_candidate(self, proposal):
            return {
                "ok": False,
                "queued": False,
                "reason": "simulated_queue_failure",
            }

    state_path = tmp_path / "synthesis_state.json"
    submitter = MemorySynthesisReviewSubmitter(
        queue=FailingQueue(),
        store=MemorySynthesizerStore(path=state_path),
    )

    proposal = {
        "theme": "jarvis",
        "summary": "Jarvis gelistirme calismalari aktif gorunuyor.",
        "source_count": 2,
        "confidence": 70,
        "source_ids": ["md_001", "md_002"],
        "proposal_type": "synthesized_memory",
    }

    result = submitter.submit([proposal])

    assert result["ok"] is False
    assert result["submitted_count"] == 0
    assert result["processed_source_ids"] == []
    assert result["errors"][0]["reason"] == "simulated_queue_failure"

    state = MemorySynthesizerStore(path=state_path).load_or_default()
    assert state.is_processed("md_001") is False
    assert state.is_processed("md_002") is False

# C1.6D end-to-end integration tests

def test_c1_6d_collector_synthesizer_submitter_end_to_end(tmp_path):
    import json
    from agents.memory_candidate_queue import MemoryCandidateQueue
    from agents.memory_synthesizer import (
        KeywordFrequencySynthesizer,
        MemorySynthesisReviewSubmitter,
        MemorySynthesizerCandidateCollector,
        MemorySynthesizerStore,
    )

    queue_root = tmp_path / "queue"
    queue_path = queue_root / "memory" / "memory_candidates.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    queue_path.write_text(
        json.dumps(
            [
                {
                    "id": "c1",
                    "source_type": "conversation",
                    "status": "pending_review",
                    "memory_type": "semantic",
                    "storage_target": "vector",
                    "summary": "jarvis roadmap commit notu hazirlandi",
                    "delete_id": "md_001",
                },
                {
                    "id": "c2",
                    "source_type": "conversation",
                    "status": "approved",
                    "memory_type": "semantic",
                    "storage_target": "vector",
                    "summary": "jarvis patch test ve repo calismasi yapildi",
                    "delete_id": "md_002",
                },
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    state_path = tmp_path / "synthesis_state.json"

    collector = MemorySynthesizerCandidateCollector(
        queue_root=queue_root,
        state_path=state_path,
    )
    candidates = collector.collect()
    assert len(candidates) == 2

    synthesizer = KeywordFrequencySynthesizer(min_mentions=2)
    proposals = synthesizer.synthesize(candidates)
    assert len(proposals) == 1
    assert proposals[0]["theme"] == "jarvis"
    assert proposals[0]["source_ids"] == ["md_001", "md_002"]

    submitter = MemorySynthesisReviewSubmitter(
        queue=MemoryCandidateQueue(root=queue_root),
        store=MemorySynthesizerStore(path=state_path),
    )
    result = submitter.submit(proposals)

    assert result["ok"] is True
    assert result["submitted_count"] == 1
    assert result["processed_source_ids"] == ["md_001", "md_002"]

    items = MemoryCandidateQueue(root=queue_root).list_candidates()
    synthesis_items = [item for item in items if item.get("source_type") == "synthesis"]
    assert len(synthesis_items) == 1

    synthesis_item = synthesis_items[0]
    assert synthesis_item["status"] == "pending_review"
    assert synthesis_item["storage_target"] == "review_queue"
    assert synthesis_item["memory_type"] == "semantic"
    assert synthesis_item["proposal_type"] == "synthesized_memory"
    assert synthesis_item["source_ids"] == ["md_001", "md_002"]

    state = MemorySynthesizerStore(path=state_path).load_or_default()
    assert state.is_processed("md_001") is True
    assert state.is_processed("md_002") is True

    # Processed source ids must not be collected again on the next run.
    second_collect = MemorySynthesizerCandidateCollector(
        queue_root=queue_root,
        state_path=state_path,
    ).collect()
    assert second_collect == []

# C1.6E synthesized memory review/status tests

def test_c1_6e_synthesis_candidate_decide_approved_updates_review_status(tmp_path):
    from agents.memory_candidate_queue import MemoryCandidateQueue

    q = MemoryCandidateQueue(root=tmp_path)

    proposal = {
        "theme": "jarvis",
        "summary": "Jarvis gelistirme calismalari aktif gorunuyor.",
        "source_count": 2,
        "confidence": 70,
        "source_ids": ["md_001", "md_002"],
        "proposal_type": "synthesized_memory",
    }

    candidate = q.add_synthesis_candidate(proposal)["candidate"]
    result = q.decide(candidate["id"], "approved")

    assert result["ok"] is True
    assert result["candidate_id"] == candidate["id"]

    updated = q.get(candidate["id"])
    assert updated["source_type"] == "synthesis"
    assert updated["proposal_type"] == "synthesized_memory"
    assert updated["status"] == "approved"
    assert updated["user_decision"] == "approved"
    assert updated["decided_at"]
    assert updated["storage_target"] == "review_queue"
    assert updated["memory_type"] == "semantic"


def test_c1_6e_synthesis_candidate_decide_rejected_and_deferred(tmp_path):
    from agents.memory_candidate_queue import MemoryCandidateQueue

    q = MemoryCandidateQueue(root=tmp_path)

    reject_candidate = q.add_synthesis_candidate(
        {
            "theme": "jarvis",
            "summary": "Jarvis gelistirme calismalari aktif gorunuyor.",
            "source_count": 2,
            "confidence": 70,
            "source_ids": ["a", "b"],
            "proposal_type": "synthesized_memory",
        }
    )["candidate"]

    defer_candidate = q.add_synthesis_candidate(
        {
            "theme": "eshot",
            "summary": "ESHOT raporlama ve telemetri calismalari aktif gorunuyor.",
            "source_count": 2,
            "confidence": 70,
            "source_ids": ["c", "d"],
            "proposal_type": "synthesized_memory",
        }
    )["candidate"]

    rejected = q.decide(reject_candidate["id"], "rejected")
    deferred = q.decide(defer_candidate["id"], "deferred")

    assert rejected["ok"] is True
    assert deferred["ok"] is True

    updated_reject = q.get(reject_candidate["id"])
    updated_defer = q.get(defer_candidate["id"])

    assert updated_reject["status"] == "rejected"
    assert updated_reject["user_decision"] == "rejected"
    assert updated_reject["decided_at"]

    assert updated_defer["status"] == "deferred"
    assert updated_defer["user_decision"] == "deferred"
    assert updated_defer["decided_at"]


def test_c1_6e_synthesis_candidate_rejects_invalid_decision(tmp_path):
    from agents.memory_candidate_queue import MemoryCandidateQueue

    q = MemoryCandidateQueue(root=tmp_path)

    candidate = q.add_synthesis_candidate(
        {
            "theme": "jarvis",
            "summary": "Jarvis gelistirme calismalari aktif gorunuyor.",
            "source_count": 2,
            "confidence": 70,
            "source_ids": ["md_001", "md_002"],
            "proposal_type": "synthesized_memory",
        }
    )["candidate"]

    result = q.decide(candidate["id"], "store_now")

    assert result["ok"] is False
    assert "approved/rejected/deferred" in result["error"]

    unchanged = q.get(candidate["id"])
    assert unchanged["status"] == "pending_review"
    assert unchanged.get("user_decision") is None
