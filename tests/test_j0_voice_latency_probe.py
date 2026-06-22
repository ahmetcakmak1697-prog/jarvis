"""
Tests for j0_voice_latency_probe.py — skeleton/harness only.
"""
from __future__ import annotations

from j0_voice_latency_probe import (
    TR_STT_ENTITY_PHRASES,
    TR_STT_PROBE_PHRASES,
    TR_STT_PROJECT_CODE_PHRASES,
    VoiceLatencyProbe,
    spike_a_notice,
)


# ---- 1: test latency math ----


def test_trigger_to_first_response_ms():
    probe = VoiceLatencyProbe(
        trigger_detected_at=100.0,
        first_audio_or_text_at=102.5,
    )
    result = probe.trigger_to_first_response_ms()
    assert result is not None
    assert result == 2500.0  # 2.5 seconds * 1000


def test_trigger_to_first_response_cached():
    probe = VoiceLatencyProbe(
        trigger_detected_at=0.0,
        first_audio_or_text_at=1.0,
    )
    assert probe.trigger_to_first_response_ms() == 1000.0
    assert probe.trigger_to_first_response_ms() == 1000.0


# ---- 2: missing timestamps fail closed ----


def test_missing_trigger_returns_none():
    probe = VoiceLatencyProbe(
        trigger_detected_at=None,
        first_audio_or_text_at=102.5,
    )
    assert probe.trigger_to_first_response_ms() is None


def test_missing_first_audio_returns_none():
    probe = VoiceLatencyProbe(
        trigger_detected_at=100.0,
        first_audio_or_text_at=None,
    )
    assert probe.trigger_to_first_response_ms() is None


def test_all_missing_returns_none():
    probe = VoiceLatencyProbe()
    assert probe.trigger_to_first_response_ms() is None


# ---- 3: Spike-A notice says it cannot answer real latency/GPU sufficiency ----


def test_spike_a_notice_cannot_answer_gpu():
    notice = spike_a_notice()
    assert "GPU" in notice
    assert "yan\u0131tlayamaz" in notice


# ---- 4: Spike-A notice says it cannot answer real TR-STT accuracy ----


def test_spike_a_notice_cannot_answer_tr_stt():
    notice = spike_a_notice()
    assert "TR-STT" in notice
    assert "do\u011frulu\u011fu" in notice or "do\u011fruluk" in notice


# ---- 5: natural Turkish STT probe phrases exist ----


def test_tr_stt_probe_phrases_are_natural_turkish():
    for phrase in TR_STT_PROBE_PHRASES:
        assert isinstance(phrase, str)
        assert len(phrase) > 0
    assert "nerede kald\u0131k" in TR_STT_PROBE_PHRASES
    assert "son commit neydi" in TR_STT_PROBE_PHRASES
    assert "en son ne yapt\u0131k" in TR_STT_PROBE_PHRASES
    assert "bug\u00fcn ne yapaca\u011f\u0131z" in TR_STT_PROBE_PHRASES


# ---- 6: project-code phrases are not in the STT WER/pass-fail phrase list ----


def test_project_code_phrases_not_in_stt_probe():
    for phrase in TR_STT_PROJECT_CODE_PHRASES:
        assert phrase not in TR_STT_PROBE_PHRASES


# ---- 7: entity normalization is separated from STT gate ----


def test_entity_normalization_separate():
    assert len(TR_STT_ENTITY_PHRASES) > 0
    for entity_phrase in TR_STT_ENTITY_PHRASES:
        assert entity_phrase not in TR_STT_PROBE_PHRASES
    assert "faz \u00fc\u00e7 e bir" in TR_STT_ENTITY_PHRASES[0]
