"""Y5 TelemetryEventStore tests."""
from __future__ import annotations
import json


def _store(tmp_path):
    from agents.telemetry_event_store import TelemetryEventStore
    return TelemetryEventStore(data_root=tmp_path)


def test_log_ask_creates_jsonl(tmp_path):
    s = _store(tmp_path)
    s.log_ask(source="ollama", level="L2", model="mistral-nemo",
              ok=True, blocked=False, latency_ms=13750,
              answer_chars=800, question="Python tekrar eden elemanlar")
    lines = (tmp_path / "telemetry_events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["source"] == "ollama"
    assert event["level"] == "L2"
    assert event["latency_ms"] == 13750
    assert "question_hash" in event
    assert "raw_question" not in event  # privacy: raw soru yazilmaz
    assert "created_at" in event


def test_question_hash_consistent(tmp_path):
    s = _store(tmp_path)
    s.log_ask(source="kc", level=None, model=None, ok=True,
              blocked=False, latency_ms=0, answer_chars=50,
              question="Qwen3 nasil kurulur?")
    s.log_ask(source="kc", level=None, model=None, ok=True,
              blocked=False, latency_ms=0, answer_chars=50,
              question="Qwen3 nasil kurulur?")
    lines = (tmp_path / "telemetry_events.jsonl").read_text(encoding="utf-8").splitlines()
    h1 = json.loads(lines[0])["question_hash"]
    h2 = json.loads(lines[1])["question_hash"]
    assert h1 == h2


def test_stats_returns_counts(tmp_path):
    s = _store(tmp_path)
    s.log_ask(source="ollama", level="L2", model="m", ok=True,
              blocked=False, latency_ms=10000, answer_chars=500, question="q1")
    s.log_ask(source="knowledge_card", level=None, model=None, ok=True,
              blocked=False, latency_ms=0, answer_chars=100, question="q2")
    s.log_ask(source="quick_reply", level=None, model=None, ok=True,
              blocked=False, latency_ms=1, answer_chars=20, question="merhaba")
    stats = s.stats()
    assert stats["total"] == 3
    assert stats["by_source"]["ollama"] == 1
    assert stats["by_source"]["knowledge_card"] == 1
    assert stats["avg_latency_ms"]["ollama"] == 10000


def test_no_side_effects_on_import(tmp_path):
    from agents.telemetry_event_store import TelemetryEventStore
    s = TelemetryEventStore(data_root=tmp_path)
    assert not (tmp_path / "telemetry_events.jsonl").exists()


def test_blocked_event_logged(tmp_path):
    s = _store(tmp_path)
    s.log_ask(source="redacted_blocked", level=None, model=None,
              ok=False, blocked=True, latency_ms=50, answer_chars=0,
              question="OPENAI_API_KEY=sk-test")
    lines = (tmp_path / "telemetry_events.jsonl").read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[0])
    assert event["blocked"] is True
    assert event["ok"] is False
    # Guvenlik: raw secret loglanmamali
    assert "sk-test" not in json.dumps(event)
