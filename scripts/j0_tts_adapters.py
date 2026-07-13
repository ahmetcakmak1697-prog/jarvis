"""
scripts/j0_tts_adapters.py — TTS adapter layer for J0 voice pipeline.

INTERFACE + FAKE ONLY THIS SPRINT (J0A).
Real Piper subprocess integration = J0B.
Real Edge TTS integration = J0B.

No subprocess is spawned in this file. No network calls. No audio devices.

LOOP-0E Phase A addition: build_piper_dry_run_plan() and its validators
construct/validate a real Piper argv WITHOUT ever executing it (no
subprocess.run/Popen, no os.system, no playback). Real execution stays
behind PiperSubprocessAdapter.speak()'s NotImplementedError pending a
separately approved, manually-run Phase B step. See
automation/LOOP0D_J0B_SAFETY_CONTRACT.md.
"""
from __future__ import annotations

import math
import os
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


# ---------------------------------------------------------------------------
# Phase A dry-run command planning (LOOP-0E) — no subprocess, no execution
# ---------------------------------------------------------------------------
#
# Proves a real Piper command CAN be constructed and validated safely
# without ever invoking subprocess. Real execution remains behind
# PiperSubprocessAdapter.speak()'s NotImplementedError below, gated by a
# separate, manually-run Phase B step (Ahmet only).

PIPER_DRY_RUN_ALLOWED_OUTPUT_ROOT = "artifacts/manual_piper_smoke"
PIPER_DRY_RUN_MAX_TEXT_LENGTH = 200
PIPER_DRY_RUN_MAX_TIMEOUT_SECONDS = 60.0


@dataclass
class PiperPrerequisiteResult:
    """Structured prerequisite check result. Never raised as an exception."""

    ok: bool
    reason: Optional[str] = None


@dataclass
class PiperCommandPlan:
    """Dry-run-only Piper command plan. Never executed by this module.

    argv is populated only when ok is True; reason is populated only when
    ok is False, using one of the structured prerequisite-failure codes
    returned by validate_piper_paths / validate_piper_output_path /
    validate_piper_timeout / validate_piper_text.
    """

    ok: bool
    argv: Optional[List[str]] = None
    executable: Optional[str] = None
    model: Optional[str] = None
    output_path: Optional[str] = None
    timeout_seconds: Optional[float] = None
    reason: Optional[str] = None


def validate_piper_paths(executable: str, model: str) -> PiperPrerequisiteResult:
    """Validate executable/model paths are absolute and exist on disk.

    No download, no PATH lookup, no guessed path — caller must supply an
    already-verified absolute path for both.
    """
    if not executable or not os.path.isabs(executable):
        return PiperPrerequisiteResult(ok=False, reason="executable_not_absolute")
    if not os.path.isfile(executable):
        return PiperPrerequisiteResult(ok=False, reason="executable_missing")
    if not model or not os.path.isabs(model):
        return PiperPrerequisiteResult(ok=False, reason="model_not_absolute")
    if not os.path.isfile(model):
        return PiperPrerequisiteResult(ok=False, reason="model_missing")
    return PiperPrerequisiteResult(ok=True)


def validate_piper_output_path(
    output_path: str, allowed_root: str = PIPER_DRY_RUN_ALLOWED_OUTPUT_ROOT
) -> PiperPrerequisiteResult:
    """Validate output_path ends with .wav and stays inside allowed_root.

    Path traversal outside allowed_root (e.g. via "..") is rejected.
    """
    if not output_path.lower().endswith(".wav"):
        return PiperPrerequisiteResult(ok=False, reason="output_not_wav")
    root_abs = os.path.abspath(allowed_root)
    out_abs = os.path.abspath(output_path)
    try:
        common = os.path.commonpath([root_abs, out_abs])
    except ValueError:
        return PiperPrerequisiteResult(ok=False, reason="output_outside_allowed_root")
    if common != root_abs:
        return PiperPrerequisiteResult(ok=False, reason="output_outside_allowed_root")
    return PiperPrerequisiteResult(ok=True)


def validate_piper_timeout(
    timeout_seconds, max_timeout: float = PIPER_DRY_RUN_MAX_TIMEOUT_SECONDS
) -> PiperPrerequisiteResult:
    """Validate timeout_seconds is a finite, positive, bounded, non-boolean number.

    bool is a subclass of int in Python, so it is rejected explicitly before
    the numeric check. math.isfinite() rejects NaN and +/-inf explicitly
    rather than relying on NaN's incidental (and unreliable) comparison
    behavior — NaN <= 0 and NaN > max_timeout are both False, which would
    otherwise let NaN slip through as "valid".
    """
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        return PiperPrerequisiteResult(ok=False, reason="invalid_timeout")
    if not math.isfinite(timeout_seconds):
        return PiperPrerequisiteResult(ok=False, reason="invalid_timeout")
    if timeout_seconds <= 0 or timeout_seconds > max_timeout:
        return PiperPrerequisiteResult(ok=False, reason="invalid_timeout")
    return PiperPrerequisiteResult(ok=True)


def validate_piper_text(
    text: str, max_length: int = PIPER_DRY_RUN_MAX_TEXT_LENGTH
) -> PiperPrerequisiteResult:
    """Validate text length only. Content is never interpolated into argv/shell."""
    if len(text) > max_length:
        return PiperPrerequisiteResult(ok=False, reason="text_too_long")
    return PiperPrerequisiteResult(ok=True)


def build_piper_dry_run_plan(
    *,
    executable: str,
    model: str,
    output_path: str,
    text: str,
    timeout_seconds,
    allowed_output_root: str = PIPER_DRY_RUN_ALLOWED_OUTPUT_ROOT,
) -> PiperCommandPlan:
    """Construct a validated Piper command plan WITHOUT executing anything.

    Never calls subprocess.run/Popen, os.system, or any playback function.
    text is validated for length only and is never placed into argv — the
    returned argv's executable/--model/model/--output_file/output_path
    positions are fixed regardless of text content (text is intended to be
    sent via stdin by a future, separately-approved real runtime, mirroring
    build_piper_cmd's existing stdin-based design above).
    """
    text_check = validate_piper_text(text)
    if not text_check.ok:
        return PiperCommandPlan(ok=False, reason=text_check.reason)

    path_check = validate_piper_paths(executable, model)
    if not path_check.ok:
        return PiperCommandPlan(ok=False, reason=path_check.reason)

    output_check = validate_piper_output_path(output_path, allowed_output_root)
    if not output_check.ok:
        return PiperCommandPlan(ok=False, reason=output_check.reason)

    timeout_check = validate_piper_timeout(timeout_seconds)
    if not timeout_check.ok:
        return PiperCommandPlan(ok=False, reason=timeout_check.reason)

    argv = [executable, "--model", model, "--output_file", output_path]

    return PiperCommandPlan(
        ok=True,
        argv=argv,
        executable=executable,
        model=model,
        output_path=output_path,
        timeout_seconds=float(timeout_seconds),
    )


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
