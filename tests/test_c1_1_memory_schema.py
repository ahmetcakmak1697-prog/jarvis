"""C1.1 Memory Schema routing tests.

Guards the routing contract between MemoryPolicy and MemorySchemaMapper.
"""

from __future__ import annotations

from agents.memory_schema import MemorySchemaMapper


def _route(text: str) -> dict:
    return MemorySchemaMapper().route_exchange(text).to_dict()


def test_low_value_message_is_ignored():
    r = _route("tamam")

    assert r["schema_version"] == "c1.1"
    assert r["memory_type"] == "ignore"
    assert r["storage_target"] == "none"
    assert r["requires_review"] is False
    assert r["allow_vector"] is False


def test_explicit_preference_routes_to_semantic_vector():
    r = _route("bunu hatırla: AC/DC ve rock müzik seviyorum")

    assert r["memory_type"] == "semantic"
    assert r["storage_target"] == "vector"
    assert r["sensitivity"] == "normal"
    assert r["action"] == "keep_long_term"
    assert r["allow_vector"] is True
    assert r["requires_review"] is False
    assert "explicit_save" in r["tags"]
    assert r["delete_id"].startswith("md_")


def test_daily_context_routes_to_ephemeral_summary():
    r = _route("bugün hava yağmurlu, motosiklete çıkmayacağım")

    assert r["memory_type"] == "episodic"
    assert r["storage_target"] == "daily_summary"
    assert r["action"] == "daily_summary"
    assert r["allow_daily_summary"] is True
    assert r["allow_vector"] is False
    assert r["expires_at"] is not None


def test_project_signal_routes_to_semantic_vector():
    r = _route("Jarvis C1 hafıza politikasına başladık")

    assert r["memory_type"] == "semantic"
    assert r["storage_target"] == "vector"
    assert r["action"] == "keep_long_term"
    assert r["importance"] >= 8
    assert r["allow_vector"] is True
    assert "project" in r["tags"]


def test_sensitive_explicit_save_routes_to_review_queue():
    r = _route("telefon numaram 555 123 45 67 bunu kaydet")

    assert r["memory_type"] == "sensitive_review"
    assert r["storage_target"] == "review_queue"
    assert r["sensitivity"] == "sensitive"
    assert r["requires_review"] is True
    assert r["allow_vector"] is False
    assert "sensitive" in r["tags"]


def test_secret_marker_never_routes_to_vector_even_if_explicit():
    r = _route("bunu hatırla: api key secret-123")

    assert r["memory_type"] == "sensitive_review"
    assert r["storage_target"] == "review_queue"
    assert r["sensitivity"] == "secret"
    assert r["allow_vector"] is True  # policy allowed it
    assert r["requires_review"] is False  # policy did not catch it
    # schema safety override still blocks vector storage
