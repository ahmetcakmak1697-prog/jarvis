from agents.structured_output_guard import (
    StructuredOutputGuard,
    reporting_summary_schema,
)


def test_parse_valid_json_object():
    guard = StructuredOutputGuard()

    result = guard.parse_json('{"title": "Daily", "summary": "OK"}')

    assert result.ok is True
    assert result.data["title"] == "Daily"
    assert result.errors == []


def test_parse_invalid_json_returns_error():
    guard = StructuredOutputGuard()

    result = guard.parse_json("{invalid")

    assert result.ok is False
    assert result.data == {}
    assert result.errors


def test_parse_array_root_is_rejected():
    guard = StructuredOutputGuard()

    result = guard.parse_json("[1, 2, 3]")

    assert result.ok is False
    assert "json_root_not_object" in result.errors


def test_validate_required_fields():
    guard = StructuredOutputGuard()

    required, optional = reporting_summary_schema()

    result = guard.validate(
        {
            "title": "Report",
            "summary": "State is stable",
            "next_action": "Continue C3",
            "risks": [],
        },
        required,
        optional,
    )

    assert result.ok is True


def test_validate_missing_required_uses_error():
    guard = StructuredOutputGuard()

    required, optional = reporting_summary_schema()

    result = guard.validate(
        {
            "title": "Report",
            "summary": "State is stable",
            "risks": [],
        },
        required,
        optional,
    )

    assert result.ok is False
    assert "missing_required:next_action" in result.errors


def test_parse_and_validate_uses_fallback_on_bad_json():
    guard = StructuredOutputGuard()

    required, optional = reporting_summary_schema()
    fallback = {
        "title": "Fallback",
        "summary": "Structured output failed",
        "next_action": "Retry with safer prompt",
        "risks": ["structured_output_failed"],
    }

    result = guard.parse_and_validate(
        "{invalid",
        required,
        optional,
        fallback,
    )

    assert result.ok is False
    assert result.used_fallback is True
    assert result.data["title"] == "Fallback"


def test_parse_and_validate_uses_fallback_on_bad_schema():
    guard = StructuredOutputGuard()

    required, optional = reporting_summary_schema()
    fallback = {
        "title": "Fallback",
        "summary": "Structured output failed",
        "next_action": "Retry with safer prompt",
        "risks": ["structured_output_failed"],
    }

    result = guard.parse_and_validate(
        '{"title": "Bad", "summary": "Missing fields"}',
        required,
        optional,
        fallback,
    )

    assert result.ok is False
    assert result.used_fallback is True
    assert result.data["next_action"] == "Retry with safer prompt"
