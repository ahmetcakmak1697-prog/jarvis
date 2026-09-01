"""C1.2 Telegram memory candidate display tests."""

from __future__ import annotations

from tools.telegram_agent import _format_memory_candidate_item


def test_format_conversation_semantic_candidate():
    item = {
        "id": "mc_test123",
        "source_type": "conversation",
        "memory_type": "semantic",
        "storage_target": "vector",
        "sensitivity": "normal",
        "tier": "long_term_candidate",
        "confidence": 95,
        "expires_at": "2026-08-01T20:38:43",
        "tags": ["conversation", "c1_2_review", "explicit_save"],
        "summary": "USER: bunu hatırla: AC/DC ve rock müzik seviyorum",
        "route": {"action": "keep_long_term"},
    }

    lines = _format_memory_candidate_item(item)
    text = "\n".join(lines)

    assert "ID: mc_test123" in text
    assert "Source: conversation | Type: semantic -> vector" in text
    assert "Sensitivity: normal | Action: keep_long_term" in text
    assert "Tier: long_term_candidate | Confidence: 95" in text
    assert "Tags: conversation, c1_2_review, explicit_save" in text
    assert "Ozet: USER: bunu hatırla: AC/DC ve rock müzik seviyorum" in text


def test_format_sensitive_review_candidate():
    item = {
        "id": "mc_sensitive",
        "source_type": "conversation",
        "memory_type": "sensitive_review",
        "storage_target": "review_queue",
        "sensitivity": "sensitive",
        "tier": "project_or_session_candidate",
        "confidence": 70,
        "expires_at": "2026-06-16T20:38:43",
        "tags": ["conversation", "c1_2_review", "sensitive", "explicit_save"],
        "summary": "USER: telefon numaram 555 123 45 67 bunu kaydet",
        "route": {"action": "sensitive_review"},
    }

    lines = _format_memory_candidate_item(item)
    text = "\n".join(lines)

    assert "ID: mc_sensitive" in text
    assert "Source: conversation | Type: sensitive_review -> review_queue" in text
    assert "Sensitivity: sensitive | Action: sensitive_review" in text
    assert "Tags: conversation, c1_2_review, sensitive, explicit_save" in text


def test_format_candidate_truncates_long_summary():
    long_summary = "USER: " + ("çok uzun metin " * 80)
    item = {
        "id": "mc_long",
        "summary": long_summary,
        "route": {},
    }

    lines = _format_memory_candidate_item(item)
    summary_line = [line for line in lines if line.startswith("Ozet: ")][0]

    assert summary_line.endswith("...")
    assert len(summary_line) <= 290


def test_format_synthesis_candidate_shows_review_metadata():
    item = {
        "id": "mc_synthesis",
        "source_type": "synthesis",
        "mode": "memory_synthesis",
        "status": "approved",
        "memory_type": "semantic",
        "storage_target": "review_queue",
        "sensitivity": "normal",
        "proposal_type": "synthesized_memory",
        "theme": "jarvis",
        "source_count": 2,
        "source_ids": ["md_001", "md_002"],
        "tier": "project_or_session_candidate",
        "confidence": 70,
        "expires_at": "2026-08-01T20:38:43",
        "tags": ["synthesis", "c1_6", "theme:jarvis"],
        "summary": "Jarvis gelistirme calismalari aktif gorunuyor.",
        "route": {"action": "synthesis_review"},
        "user_decision": "approved",
        "decided_at": "2026-06-05T20:38:43",
    }

    lines = _format_memory_candidate_item(item)
    text = "\n".join(lines)

    assert "ID: mc_synthesis" in text
    assert "Source: synthesis | Type: semantic -> review_queue" in text
    assert "Status: approved | Decision: approved" in text
    assert "Proposal: synthesized_memory | Theme: jarvis | Sources: 2" in text
    assert "Source IDs: md_001, md_002" in text
    assert "Tags: synthesis, c1_6, theme:jarvis" in text
    assert "Ozet: Jarvis gelistirme calismalari aktif gorunuyor." in text

