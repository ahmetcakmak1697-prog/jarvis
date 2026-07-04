"""
scripts/j0_tts_adapters.py — TTS adapter layer for J0 voice pipeline.

INTERFACE + FAKE ONLY THIS SPRINT (J0A).
Real Piper subprocess integration = J0B.
Real Edge TTS integration = J0B.

No subprocess is spawned in this file. No network calls. No audio devices.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import List, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TTSResult:
    """Result from a TTS speak() call.

    first_audio_hint_ms: wall-clock milliseconds from speak() call to first
        audio onset. None if not measured. NEVER 0 for an unmeasured value —
        0 would be a false claim. See warning field.
    warning: populated whenever first_audio_hint_ms is None; callers should
        log or surface this string rather than silently discarding it.
    """

    ok: bool
    engine: str
    first_audio_hint_ms: Optional[float]
    warning: Optional[str] = field(default=None)

    def __post_init__(self) -> None:
        if self.first_audio_hint_ms is None and self.warning is None:
            self.warning = (
                "first_audio_hint_ms is None: latency not measured; "
                "do not infer or fabricate a timing value"
            )
        if self.first_audio_hint_ms == 0:
            raise ValueError(
                "first_audio_hint_ms must not be 0 for an unmeasured value; use None"
            )


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class TTSAdapter(Protocol):
    """Text-to-speech adapter interface."""

    def speak(self, text: str) -> TTSResult:
        """Synthesize and output text. Returns a TTSResult."""
        ...


# ---------------------------------------------------------------------------
# FakeTTSAdapter (tests only)
# ---------------------------------------------------------------------------


class FakeTTSAdapter:
    """Records all spoken texts. Never measures timing. For tests only."""

    def __init__(self) -> None:
        self.spoken: List[str] = []

    def speak(self, text: str) -> TTSResult:
        self.spoken.append(text)
        return TTSResult(
            ok=True,
            engine="fake",
            first_audio_hint_ms=None,
        )


# ---------------------------------------------------------------------------
# PiperSubprocessAdapter (stub — J0B)
# ---------------------------------------------------------------------------


def build_piper_cmd(config: dict) -> list:
    """Build Piper TTS CLI command argv. Pure function — no subprocess, no I/O.

    config keys:
        executable (str, optional): path to piper binary; defaults to "piper"
        model      (str, required): path to Piper .onnx voice model file
        output_file (str, optional): write output WAV here instead of stdout

    Returns a list[str] suitable for subprocess.run(cmd, input=text, ...).

    Piper subprocess boundary preferred to reduce coupling and
    licensing/linking ambiguity; license must be verified before
    distribution/commercial use; no legal conclusion is made in this sprint.
    """
    executable = config.get("executable", "piper")
    model = config["model"]
    cmd: list = [executable, "--model", model, "--output-raw"]
    if "output_file" in config:
        cmd += ["--output_file", config["output_file"]]
    return cmd


class PiperSubprocessAdapter:
    """Stub. Real Piper subprocess integration = J0B.

    Piper subprocess boundary preferred to reduce coupling and
    licensing/linking ambiguity; license must be verified before
    distribution/commercial use; no legal conclusion is made in this sprint.
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        self._config: dict = config or {}

    def speak(self, text: str) -> TTSResult:
        raise NotImplementedError(
            "J0B: PiperSubprocessAdapter is not implemented in J0A. "
            "Real Piper subprocess integration is scheduled for sprint J0B."
        )


# ---------------------------------------------------------------------------
# EdgeTTSAdapter (stub — J0B, default-off cloud fallback)
# ---------------------------------------------------------------------------


class EdgeTTSAdapter:
    """Default-off cloud fallback adapter. Stub. No network in J0A.

    Edge TTS is a cloud service. This adapter is labeled cloud-fallback.
    Activating it requires JARVIS_J0_EDGE_TTS_ENABLED=1 (not wired yet).
    Real implementation = J0B. No network calls anywhere in this sprint.
    """

    def speak(self, text: str) -> TTSResult:
        raise NotImplementedError(
            "J0B-edge: EdgeTTSAdapter is not implemented in J0A. "
            "Edge TTS is a cloud-only fallback scheduled for sprint J0B."
        )
