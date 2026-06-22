"""
j0_voice_latency_probe.py — Voice latency harness skeleton (Spike-A).

SPIKE_A_ONLY: This is a skeleton/harness only.
- No real microphone, wake-word, STT, or TTS.
- No package installs.

Real wake -> ilk-hece measurement belongs to Spike-B.
Spike-B must run locally with microphone, model setup,
and STT/TTS packages allowed.
Spike-A cannot answer GPU sufficiency.
Spike-A cannot answer real TR-STT accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Probe data model
# ---------------------------------------------------------------------------


@dataclass
class VoiceLatencyProbe:
    trigger_detected_at: Optional[float] = None
    stt_start_at: Optional[float] = None
    stt_end_at: Optional[float] = None
    llm_start_at: Optional[float] = None
    first_token_at: Optional[float] = None
    tts_start_at: Optional[float] = None
    first_audio_or_text_at: Optional[float] = None

    _cached_trigger_to_first: Optional[float] = field(default=None, init=False, repr=False)

    def trigger_to_first_response_ms(self) -> Optional[float]:
        if self._cached_trigger_to_first is not None:
            return self._cached_trigger_to_first
        if self.trigger_detected_at is None or self.first_audio_or_text_at is None:
            return None
        result = (self.first_audio_or_text_at - self.trigger_detected_at) * 1000.0
        self._cached_trigger_to_first = result
        return result


# ---------------------------------------------------------------------------
# TR-STT probe phrases
# ---------------------------------------------------------------------------

TR_STT_PROBE_PHRASES: list[str] = [
    "nerede kald\u0131k",
    "son commit neydi",
    "en son ne yapt\u0131k",
    "bug\u00fcn ne yapaca\u011f\u0131z",
]

TR_STT_ENTITY_PHRASES: list[str] = [
    "faz \u00fc\u00e7 e bir durumunu \u00f6zetle",
]

TR_STT_PROJECT_CODE_PHRASES: list[str] = [
    "FAZ \u00fc\u00e7 E bir durumunu \u00f6zetle",
]


# ---------------------------------------------------------------------------
# Spike-A notice
# ---------------------------------------------------------------------------


def spike_a_notice() -> str:
    return (
        "SPIKE_A_ONLY: Bu ara\u00e7 bir iskelet / ko\u015fum tak\u0131m\u0131d\u0131r.\n"
        "Ger\u00e7ek wake -> ilk-hece \u00f6l\u00e7\u00fcm\u00fc i\u00e7in Spike-B gerekir.\n"
        "Spike-B, mikrofon, model kurulumu ve STT/TTS paketleri ile\n"
        "yerel olarak \u00e7al\u0131\u015ft\u0131r\u0131lmal\u0131d\u0131r.\n"
        "Spike-A GPU yeterlili\u011fini yan\u0131tlayamaz.\n"
        "Spike-A ger\u00e7ek TR-STT do\u011frulu\u011funu yan\u0131tlayamaz.\n"
    )
