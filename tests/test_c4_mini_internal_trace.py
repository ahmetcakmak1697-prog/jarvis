import json

from agents.internal_trace import InternalTraceLogger


def test_internal_trace_writes_jsonl(tmp_path):
    path = tmp_path / "trace.jsonl"
    logger = InternalTraceLogger(path=path)

    record = logger.log(
        event="report_started",
        layer="C3",
        status="ok",
        message="Report started",
        payload={"report_type": "daily_project_summary"},
    )

    assert path.exists()
    assert record["event"] == "report_started"

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    loaded = json.loads(lines[0])
    assert loaded["layer"] == "C3"
    assert loaded["payload"]["report_type"] == "daily_project_summary"


def test_internal_trace_redacts_message_and_payload(tmp_path):
    path = tmp_path / "trace.jsonl"
    logger = InternalTraceLogger(path=path)

    record = logger.log(
        event="secret_test",
        layer="security",
        status="warn",
        message="OPENAI_API_KEY=sk-secret",
        payload={
            "token": "abc123",
            "email": "user@example.com",
            "path": r"C:\Users\Ahmedov\Desktop\Jarvis",
        },
    )

    text = json.dumps(record, ensure_ascii=False)

    assert "sk-secret" not in text
    assert "abc123" not in text
    assert "user@example.com" not in text
    assert "Ahmedov" not in text
    assert "[REDACTED]" in text or "[REDACTED_EMAIL]" in text


def test_internal_trace_tail_skips_broken_lines(tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text('{"event":"ok","layer":"test","status":"ok"}\n{broken\n', encoding="utf-8")

    logger = InternalTraceLogger(path=path)

    items = logger.tail(10)

    assert len(items) == 1
    assert items[0]["event"] == "ok"


def test_internal_trace_stats_counts_events_layers_statuses(tmp_path):
    path = tmp_path / "trace.jsonl"
    logger = InternalTraceLogger(path=path)

    logger.log("event_a", layer="C3", status="ok")
    logger.log("event_a", layer="C3", status="ok")
    logger.log("event_b", layer="A6", status="warn")

    stats = logger.stats()

    assert stats["total"] == 3
    assert stats["events"]["event_a"] == 2
    assert stats["layers"]["C3"] == 2
    assert stats["statuses"]["warn"] == 1
