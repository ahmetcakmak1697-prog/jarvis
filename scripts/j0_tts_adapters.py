"""
scripts/j0_tts_adapters.py — TTS adapter layer for J0 voice pipeline.

Esik 1 (2026-08-31): PiperSubprocessAdapter and EdgeTTSAdapter are now LIVE.
Before this date both raised NotImplementedError unconditionally.

The safety properties were kept, not dropped -- they moved from "never runs"
to "runs only behind an explicit gate":

  * Piper is local (no network). It refuses to run unless the executable and
    the .onnx model are supplied as ABSOLUTE, EXISTING paths. PATH is never
    searched, nothing is downloaded, no path is guessed. Failures come back
    as TTSResult(ok=False), never as an exception.
  * Edge TTS is a CLOUD service -- the text leaves this machine. It stays
    default-off and refuses unless JARVIS_J0_EDGE_TTS_ENABLED=1 is set
    (CLAUDE.md 7: data class governs what may leave).

Imports stay light on purpose: subprocess, edge_tts and pygame are imported
lazily inside the default runners, so importing this module still pulls in no
network library, spawns no subprocess and touches no audio device. The
import-safety tests assert exactly that.

LOOP-0E Phase A remains: build_piper_dry_run_plan() and its validators
construct/validate a real Piper argv WITHOUT executing it, and plan objects
still expose no execution path of their own. See
automation/LOOP0D_J0B_SAFETY_CONTRACT.md.
"""
from __future__ import annotations

import math
import os
import time
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


PIPER_MAX_TIMEOUT_SECONDS = PIPER_DRY_RUN_MAX_TIMEOUT_SECONDS


class PiperSubprocessAdapter:
    """Local Piper TTS over a subprocess boundary.

    Gate change (2026-08-31, Esik 1): speak() used to raise NotImplementedError
    unconditionally. It now executes -- but the safety property is preserved,
    not removed: execution is refused unless prerequisites validate, and a
    failure is returned as a TTSResult rather than raised. Nothing is
    downloaded, no path is guessed, and PATH is never searched; the caller
    must supply absolute, existing paths (see validate_piper_paths).

    Piper runs entirely on this machine -- no network, no data egress.

    ``runner`` is injectable so the execution path is testable without a Piper
    binary present. It is called as ``runner(argv, text, timeout)`` and must
    return an object with ``returncode`` and ``stderr``.

    Piper subprocess boundary preferred to reduce coupling and
    licensing/linking ambiguity; license must be verified before
    distribution/commercial use; no legal conclusion is made in this sprint.
    """

    engine_name = "piper"

    def __init__(self, config: Optional[dict] = None, runner=None) -> None:
        self._config: dict = config or {}
        self._runner = runner

    def _fail(self, reason: str) -> TTSResult:
        return TTSResult(
            ok=False,
            engine=self.engine_name,
            first_audio_hint_ms=None,
            warning=f"piper_not_run: {reason}",
        )

    def speak(self, text: str) -> TTSResult:
        text_check = validate_piper_text(text)
        if not text_check.ok:
            return self._fail(text_check.reason or "text_invalid")

        executable = self._config.get("executable", "")
        model = self._config.get("model", "")
        prereq = validate_piper_paths(executable, model)
        if not prereq.ok:
            return self._fail(prereq.reason or "prerequisite_failed")

        timeout_check = validate_piper_timeout(
            self._config.get("timeout_seconds", PIPER_MAX_TIMEOUT_SECONDS)
        )
        if not timeout_check.ok:
            return self._fail(timeout_check.reason or "timeout_invalid")
        timeout = float(self._config.get("timeout_seconds",
                                         PIPER_MAX_TIMEOUT_SECONDS))

        output_file = self._config.get("output_file")
        if output_file is not None:
            out_check = validate_piper_output_path(output_file)
            if not out_check.ok:
                return self._fail(out_check.reason or "output_path_invalid")

        argv = build_piper_cmd(self._config)
        runner = self._runner or _default_piper_runner

        start = time.perf_counter()
        try:
            completed = runner(argv, text, timeout)
        except Exception as exc:  # noqa: BLE001 - surfaced, never swallowed
            return self._fail(f"subprocess_error: {exc}")

        returncode = getattr(completed, "returncode", 1)
        if returncode != 0:
            stderr = getattr(completed, "stderr", "") or ""
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", "replace")
            return self._fail(f"exit_{returncode}: {stderr.strip()[:200]}")

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return TTSResult(
            ok=True,
            engine=self.engine_name,
            # Piper writes the whole file before returning, so this is
            # synthesis wall-clock, not true first-audio onset. Named as a
            # hint precisely because it must not be read as onset latency.
            first_audio_hint_ms=elapsed_ms,
            warning=(
                "first_audio_hint_ms is synthesis wall-clock, not audio onset: "
                "piper writes the file before returning"
            ),
        )


def _default_piper_runner(argv: List[str], text: str, timeout: float):
    """Real subprocess runner. Imported lazily so importing this module
    never pulls in subprocess machinery (see import-safety tests)."""
    import subprocess

    return subprocess.run(
        argv,
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=timeout,
        check=False,
    )


# ---------------------------------------------------------------------------
# EdgeTTSAdapter (cloud fallback — DEFAULT OFF)
# ---------------------------------------------------------------------------

EDGE_TTS_ENABLE_FLAG = "JARVIS_J0_EDGE_TTS_ENABLED"
EDGE_TTS_DEFAULT_VOICE = "tr-TR-AhmetNeural"


class EdgeTTSAdapter:
    """Microsoft Edge TTS. Cloud service -- DEFAULT OFF.

    Gate change (2026-08-31, Esik 1): speak() used to raise
    NotImplementedError. It now works, but the data-egress gate is kept
    exactly as designed: **the text leaves this machine**, so synthesis is
    refused unless ``JARVIS_J0_EDGE_TTS_ENABLED=1`` is set (CLAUDE.md 7 --
    data class governs what may leave). Refusal is a TTSResult, never an
    exception, so a caller can fall back without try/except.

    ``synth`` and ``player`` are injectable so tests exercise the full path
    with no network and no audio device.
    """

    engine_name = "edge-tts"

    def __init__(
        self,
        voice: str = EDGE_TTS_DEFAULT_VOICE,
        synth=None,
        player=None,
        enabled: Optional[bool] = None,
    ) -> None:
        self._voice = voice
        self._synth = synth
        self._player = player
        self._enabled = enabled

    def is_enabled(self) -> bool:
        if self._enabled is not None:
            return bool(self._enabled)
        return os.getenv(EDGE_TTS_ENABLE_FLAG, "") == "1"

    def _fail(self, reason: str) -> TTSResult:
        return TTSResult(
            ok=False,
            engine=self.engine_name,
            first_audio_hint_ms=None,
            warning=f"edge_tts_not_run: {reason}",
        )

    def speak(self, text: str) -> TTSResult:
        if not isinstance(text, str) or not text.strip():
            return self._fail("text_empty")
        if not self.is_enabled():
            return self._fail(
                f"disabled: cloud TTS sends text off this machine; "
                f"set {EDGE_TTS_ENABLE_FLAG}=1 to allow"
            )

        synth = self._synth or _default_edge_synth
        player = self._player or _default_audio_player

        start = time.perf_counter()
        try:
            audio_path = synth(text, self._voice)
        except Exception as exc:  # noqa: BLE001 - surfaced, never swallowed
            return self._fail(f"synthesis_error: {exc}")
        # Measured BEFORE playback: the default player blocks for the whole
        # utterance, so including it would report speech duration as latency.
        synth_ms = (time.perf_counter() - start) * 1000.0

        try:
            player(audio_path)
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"playback_error: {exc}")

        return TTSResult(
            ok=True,
            engine=self.engine_name,
            first_audio_hint_ms=synth_ms,
            warning=(
                "first_audio_hint_ms is synthesis time only (network round-trip "
                "to the cloud TTS); playback start follows it and is not measured"
            ),
        )


def _default_edge_synth(text: str, voice: str) -> str:
    """Synthesize with edge-tts to a temp mp3 and return its path.

    Imported lazily: importing this module must not pull in a network
    library (import-safety tests assert exactly that).
    """
    import asyncio
    import tempfile

    import edge_tts

    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)

    async def _run() -> None:
        await edge_tts.Communicate(text, voice).save(path)

    asyncio.run(_run())
    return path


def _default_audio_player(path: str) -> None:
    """Play an audio file through the default output device (pygame)."""
    import pygame

    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(50)
    pygame.mixer.music.unload()
