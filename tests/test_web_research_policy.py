"""Tests for WebResearchPolicy Turkish character normalization."""

from __future__ import annotations

from agents.web_research_policy import WebResearchPolicy


def test_normalize_turkish_ascii_fold():
    policy = WebResearchPolicy()
    result = policy._normalize("\u0130ZM\u0130R I\u011eDIR \u015eOF\u00d6R \u00c7\u00d6Z\u00dcM \u00dcCRET")
    assert "izmir" in result
    assert "igdir" in result
    assert "sofor" in result
    assert "cozum" in result
    assert "ucret" in result


def test_normalize_preserves_ascii():
    policy = WebResearchPolicy()
    result = policy._normalize("Hello World 123")
    assert result == "hello world 123"


def test_turkish_current_info_detected():
    policy = WebResearchPolicy()
    decision = policy.decide("bug\u00fcn \u0130zmir hava durumu nedir")
    assert decision.allow is True
    assert decision.mode == policy.MODE_CURRENT_INFO
