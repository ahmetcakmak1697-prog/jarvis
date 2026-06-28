"""
scripts/j0_spike_b_latency_probe.py — J0 Spike-B latency probe.

Measures t0->first-text and (optionally) t0->first-audio latency for
the J0 voice loop using real microphone capture and faster-whisper STT.

t0 is always "recording_start" in this spike (keypress triggers recording).
There is no real wake-word detector — do NOT use "wake_to_*" metric names.
Metric names: t0_to_first_text_ms, t0_to_first_audio_ms.

Two modes
---------
  --mock   No microphone, no model. Validates metric math + output schema.
           measurement_valid=false, mode="mock"
           Summary: "GEÇERSİZ ÖLÇÜM (MOCK)"
           WARNING: MOCK numbers cannot be used for 3070/GPU/latency decisions.

  --real   Real mic + faster-whisper STT + real backend detection.
           measurement_valid=true, mode="real"
           Run at least --runs 5 (default). First run is warmup.

Optional flag: --runs N  (default 5)

Packages required for --real mode (Ahmet installs manually):
    pip install faster-whisper sounddevice numpy
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

T0_DEFINITION = "recording_start"
_VALID_T0_DEFINITIONS = ("recording_start", "keypress", "speech_onset")

STT_PHRASES = [
    "nerede kaldık",
    "son commit neydi",
    "en son ne yaptık",
    "bugün ne yapacağız",
]

THRESHOLDS: dict[str, dict[str, float]] = {
    "t0_to_first_audio_ms": {"pass": 1500.0, "warn": 3000.0},
    "wer_normalized_pct": {"pass": 10.0, "warn": 25.0},
}

# Mock timing constants — deterministic so tests can verify math
_MOCK_RECORD_MS = 1000.0
_MOCK_J0_STATUS_MS = 50.0
_MOCK_AMBIENT_RMS = 0.001
_MOCK_AMBIENT_PEAK = 0.005
# stt_ms by 0-based run index (5 runs total; index 0 = warmup)
_MOCK_STT_MS = [500.0, 400.0, 300.0, 500.0, 600.0]

_MOJIBAKE_MARKERS = ["Ã", "Ä", "Å", "�", "â€", "Ã§", "Ä±"]

# Turkish character sentinel — used for status_summary_sample Unicode validation
# when real status collection is unavailable (mock mode or collection failure).
# Must contain: ç ğ ı İ ö ş ü
_TURKISH_STATUS_SENTINEL = (
    "Çalışma ağacı: TEMİZ\n"
    "henüz devrede değil\n"
    "Telegram gönderme\n"
    "nerede kaldık araçtır\n"
    "Şu an devam eden: İ"
)

# ---------------------------------------------------------------------------
# Pure functions — testable without microphone
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _lev_words(ref: list[str], hyp: list[str]) -> int:
    """Word-level Levenshtein edit distance."""
    m, n = len(ref), len(hyp)
    if m == 0:
        return n
    if n == 0:
        return m
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            prev, dp[j] = dp[j], (prev if ref[i - 1] == hyp[j - 1] else 1 + min(prev, dp[j], dp[j - 1]))
    return dp[n]


def compute_wer(expected: str, recognized: str) -> tuple[float, float]:
    """Return (wer_raw, wer_normalized).

    wer_raw    — word WER on unmodified strings
    wer_normalized — word WER after normalize_text() on both sides
    """
    ref_raw = expected.split()
    hyp_raw = recognized.split()
    n_ref = max(len(ref_raw), 1)
    wer_raw = _lev_words(ref_raw, hyp_raw) / n_ref

    ref_norm = normalize_text(expected).split()
    hyp_norm = normalize_text(recognized).split()
    n_ref_norm = max(len(ref_norm), 1)
    wer_normalized = _lev_words(ref_norm, hyp_norm) / n_ref_norm

    return wer_raw, wer_normalized


def classify_audio_latency(ms: float | None) -> str:
    """Classify t0_to_first_audio_ms against thresholds."""
    if ms is None:
        return "not_measured"
    thr = THRESHOLDS["t0_to_first_audio_ms"]
    if ms <= thr["pass"]:
        return "pass"
    if ms <= thr["warn"]:
        return "warn"
    return "fail"


def classify_wer(wer_pct: float) -> str:
    """Classify WER percentage against thresholds."""
    thr = THRESHOLDS["wer_normalized_pct"]
    if wer_pct <= thr["pass"]:
        return "pass"
    if wer_pct <= thr["warn"]:
        return "warn"
    return "fail"


def _stat(values: list[float]) -> dict[str, Any]:
    if not values:
        return {}
    return {
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "n": len(values),
    }


def derive_gpu_verdict(
    verdict: str,
    gpu_used: bool | None,
    measurement_valid: bool = True,
) -> str:
    """Compute gpu_verdict from latency verdict + GPU runtime evidence.

    Only proven CUDA/GPU runtime (gpu_used=True) may yield 'yeterli' or 'sınırda'.
    gpu_used=None (unproven) → 'ölçülemedi'.
    gpu_used=False (no GPU) → 'yetersiz'.
    measurement_valid=False → 'ölçülemedi' always.
    """
    if not measurement_valid:
        return "ölçülemedi"
    if gpu_used is None:
        return "ölçülemedi"
    if gpu_used is False:
        return "yetersiz"
    # gpu_used is True: map from latency/WER verdict
    _map: dict[str, str] = {
        "yeterli": "yeterli",
        "sınırda": "sınırda",
        "yetersiz": "yetersiz",
        "yetersiz_veri": "ölçülemedi",
        "geçersiz_ölçüm": "ölçülemedi",
    }
    return _map.get(verdict, "ölçülemedi")


def aggregate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Exclude warmup, pre-excluded (stt_error/ambient_error), and loud-ambient runs.

    Pre-set excluded_reason (stt_error, ambient_error, etc.) takes priority over
    the ambient_ok check so that error runs are never silently included in stats.
    gpu_verdict is NOT computed here — callers use derive_gpu_verdict().
    """
    annotated: list[dict[str, Any]] = []
    usable: list[dict[str, Any]] = []
    warmup_excluded = False
    ambient_excluded = 0
    error_excluded = 0

    for r in runs:
        r_out = dict(r)
        if r.get("warmup"):
            r_out["excluded_reason"] = "warmup"
            warmup_excluded = True
            annotated.append(r_out)
            continue
        # Pre-set exclusion (stt_error, ambient_error, …) takes priority
        if r.get("excluded_reason"):
            error_excluded += 1
            annotated.append(r_out)
            continue
        if not r.get("ambient_ok", True):
            r_out["excluded_reason"] = "ambient"
            ambient_excluded += 1
            annotated.append(r_out)
            continue
        annotated.append(r_out)
        usable.append(r_out)

    n = len(usable)
    stats: dict[str, Any] = {}
    for metric in ("t0_to_first_text_ms", "stt_ms", "record_ms", "wer_raw", "wer_normalized"):
        vals = [r[metric] for r in usable if r.get(metric) is not None]
        if vals:
            stats[metric] = _stat(vals)

    audio_vals = [r["t0_to_first_audio_ms"] for r in usable if r.get("t0_to_first_audio_ms") is not None]
    if audio_vals:
        stats["t0_to_first_audio_ms"] = _stat(audio_vals)

    if n < 3:
        return {
            "n": n,
            "warmup_excluded": warmup_excluded,
            "ambient_excluded": ambient_excluded,
            "error_excluded": error_excluded,
            "verdict": "yetersiz_veri",
            "metric_stats": stats,
            "annotated_runs": annotated,
        }

    audio_med = stats.get("t0_to_first_audio_ms", {}).get("median")
    wer_med_pct = stats.get("wer_normalized", {}).get("median", 0.0) * 100
    audio_cls = classify_audio_latency(audio_med)
    wer_cls = classify_wer(wer_med_pct)

    classes = [c for c in (audio_cls, wer_cls) if c != "not_measured"]
    if "fail" in classes:
        verdict = "yetersiz"
    elif "warn" in classes:
        verdict = "sınırda"
    else:
        verdict = "yeterli"

    return {
        "n": n,
        "warmup_excluded": warmup_excluded,
        "ambient_excluded": ambient_excluded,
        "error_excluded": error_excluded,
        "verdict": verdict,
        "metric_stats": stats,
        "annotated_runs": annotated,
    }


def validate_backend(
    backend: str | None,
    compute_type: str | None,
    gpu_used: bool | None,
) -> list[str]:
    """Return list of consistency errors. Empty list = consistent."""
    errors: list[str] = []
    if backend is None:
        return errors
    bl = backend.lower()
    if "cpu" in bl and gpu_used is True:
        errors.append(f"contradiction: backend={backend!r} implies no GPU but gpu_used=True")
    if "cuda" in bl and gpu_used is False:
        errors.append(f"contradiction: backend={backend!r} implies GPU but gpu_used=False")
    return errors


def validate_unicode(text: str) -> tuple[bool, list[str]]:
    """Return (ok, issues). Checks for mojibake markers."""
    issues: list[str] = []
    for bad in _MOJIBAKE_MARKERS:
        if bad in text:
            issues.append(f"mojibake {bad!r} found in text")
    return len(issues) == 0, issues


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------


def _make_mock_run(phrase: str, run_idx_0: int) -> dict[str, Any]:
    """Build one mock run. run_idx_0 is 0-based. Run 0 is warmup."""
    stt_ms = _MOCK_STT_MS[run_idx_0 % len(_MOCK_STT_MS)]
    after_ms = stt_ms + 20.0
    t0_text = _MOCK_RECORD_MS + after_ms
    wer_raw, wer_normalized = compute_wer(phrase, phrase)  # perfect recognition in mock
    return {
        "warmup": run_idx_0 == 0,
        "phrase_idx": run_idx_0,
        "ambient_rms": _MOCK_AMBIENT_RMS,
        "ambient_peak": _MOCK_AMBIENT_PEAK,
        "ambient_ok": True,
        "record_ms": _MOCK_RECORD_MS,
        "stt_ms": stt_ms,
        "after_record_to_text_ms": after_ms,
        "t0_to_first_text_ms": t0_text,
        "t0_to_first_audio_ms": None,  # TTS not measured in this spike
        "j0_status_ms": _MOCK_J0_STATUS_MS,
        "total_command_to_response_ms": t0_text + _MOCK_J0_STATUS_MS,
        "recognized_text": phrase,
        "expected_text": phrase,
        "wer_raw": wer_raw,
        "wer_normalized": wer_normalized,
        "status_route_matched": "nerede" in phrase,
        "status_summary_sample": _TURKISH_STATUS_SENTINEL,
    }


def run_mock(phrases: list[str] | None = None, n_runs: int = 5) -> dict[str, Any]:
    """Run mock mode. Returns measurement_valid=False. No hardware touched."""
    if phrases is None:
        phrases = STT_PHRASES
    phrase = phrases[0]  # use first phrase for multi-run
    runs = [_make_mock_run(phrase, i) for i in range(n_runs)]
    agg = aggregate_runs(runs)

    # BLOCKER 1: mock output must never look like a real pass.
    # Override verdict and gpu_verdict unconditionally for measurement_valid=False.
    verdict = "geçersiz_ölçüm"
    gpu_verdict = derive_gpu_verdict(verdict, None, measurement_valid=False)  # → "ölçülemedi"

    warnings = [
        "MOCK — bu sayılar gerçek değildir, "
        "3070/GPU/latency kararı için KULLANILAMAZ"
    ]
    if any(r.get("t0_to_first_audio_ms") is None for r in runs if not r.get("warmup")):
        warnings.append("TTS ölçülemedi, his metriği eksik")

    summary = (
        "GEÇERSİZ ÖLÇÜM (MOCK) — bu çıktı yalnızca şema/matematik doğrulama içindir. "
        "Gerçek 3070/GPU/latency kararı için --real ile çalıştırın."
    )

    return {
        "ok": True,
        "mode": "mock",
        "measurement_valid": False,
        "ts": _ts(),
        "t0_definition": T0_DEFINITION,
        "device_info": "mock",
        "backend": "cpu",
        "model": "mock-whisper",
        "compute_type": "int8",
        "gpu_used": None,  # mock: no GPU evidence
        "ambient_rms": _MOCK_AMBIENT_RMS,
        "ambient_peak": _MOCK_AMBIENT_PEAK,
        "ambient_ok": True,
        # Representative values from last non-warmup run
        "record_ms": _MOCK_RECORD_MS,
        "stt_ms": _MOCK_STT_MS[-1],
        "after_record_to_text_ms": _MOCK_STT_MS[-1] + 20.0,
        "t0_to_first_text_ms": _MOCK_RECORD_MS + _MOCK_STT_MS[-1] + 20.0,
        "t0_to_first_audio_ms": None,
        "j0_status_ms": _MOCK_J0_STATUS_MS,
        "total_command_to_response_ms": _MOCK_RECORD_MS + _MOCK_STT_MS[-1] + 20.0 + _MOCK_J0_STATUS_MS,
        "recognized_text": phrase,
        "expected_text": phrase,
        "wer_raw": 0.0,
        "wer_normalized": 0.0,
        "status_route_matched": "nerede" in phrase,
        # Always populated: sentinel guarantees Turkish char coverage for Unicode validation
        "status_summary_sample": _TURKISH_STATUS_SENTINEL,
        "thresholds": THRESHOLDS,
        "metric_stats": agg["metric_stats"],
        "verdict": verdict,
        "gpu_verdict": gpu_verdict,
        "warnings": warnings,
        "summary": summary,
        "runs": agg["annotated_runs"],
        "n_usable": agg["n"],
        "warmup_excluded": agg["warmup_excluded"],
        "ambient_excluded": agg["ambient_excluded"],
        "error_excluded": agg["error_excluded"],
    }


# ---------------------------------------------------------------------------
# Real mode — injectable for testing, lazy hardware imports
# ---------------------------------------------------------------------------


def _real_probe(
    phrases: list[str] | None = None,
    n_runs: int = 5,
    *,
    device_lister=None,
    audio_recorder=None,
    ambient_sampler=None,
    stt_runner=None,
) -> dict[str, Any]:
    """Injectable real probe core. Hardware dependencies injected for testability.

    device_lister:   () -> list[dict]                       list available input devices
    audio_recorder:  (seconds: float) -> ndarray            capture main audio
    ambient_sampler: () -> ndarray                          capture 0.5s ambient; defaults
                                                            to audio_recorder(0.5) if None
    stt_runner:      (audio: ndarray) -> tuple[str, float]  (text, stt_ms)
    """
    if phrases is None:
        phrases = STT_PHRASES

    ts = _ts()

    # BLOCKER 6: t0_definition must appear on every output path, including early failures.
    _early: dict[str, Any] = {
        "mode": "real",
        "measurement_valid": False,
        "ts": ts,
        "t0_definition": T0_DEFINITION,
        "t0_to_first_text_ms": None,
        "t0_to_first_audio_ms": None,
    }

    # Resolve device_lister
    if device_lister is None:
        try:
            import sounddevice as sd

            device_lister = lambda: [d for d in sd.query_devices() if d["max_input_channels"] > 0]
        except ImportError:
            return {
                **_early,
                "ok": False,
                "error": "sounddevice_not_installed",
                "warnings": ["Install: pip install sounddevice numpy faster-whisper"],
            }

    devices = device_lister()
    if not devices:
        return {
            **_early,
            "ok": False,
            "error": "no_input_device",
            "warnings": ["No input audio device found. Connect a microphone."],
        }

    # Resolve STT runner
    if stt_runner is None:
        try:
            from faster_whisper import WhisperModel

            _model = WhisperModel("small", device="auto", compute_type="int8")
            backend_info = {
                "backend": "faster-whisper",
                "model": "small",
                "compute_type": "int8",
            }

            def stt_runner(audio_np):
                import time
                t_start = time.perf_counter()
                segments, info = _model.transcribe(audio_np, language="tr")
                text = " ".join(s.text.strip() for s in segments)
                stt_ms = (time.perf_counter() - t_start) * 1000
                return text, stt_ms

        except ImportError:
            return {
                **_early,
                "ok": False,
                "error": "faster_whisper_not_installed",
                "warnings": ["Install: pip install faster-whisper"],
            }
    else:
        backend_info = {
            "backend": "injected",
            "model": "injected",
            "compute_type": "injected",
        }

    # Resolve audio recorder
    if audio_recorder is None:
        try:
            import sounddevice as sd
            import numpy as np

            def audio_recorder(seconds: float = 4.0):
                sample_rate = 16000
                frames = int(seconds * sample_rate)
                audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")
                sd.wait()
                return audio.flatten()

        except ImportError:
            return {
                **_early,
                "ok": False,
                "error": "sounddevice_not_installed",
                "warnings": ["Install: pip install sounddevice numpy"],
            }

    # Default ambient_sampler: uses audio_recorder with short window
    if ambient_sampler is None:
        _ar = audio_recorder
        ambient_sampler = lambda: _ar(0.5)

    # Collect J0 status once before the loop — for Unicode validation + j0_status_ms
    import time

    _repo_root = Path(__file__).resolve().parents[1]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

    status_sample: str = _TURKISH_STATUS_SENTINEL  # guaranteed non-null fallback
    j0_status_ms_global: float | None = None
    warnings: list[str] = ["TTS ölçülmedi, his metriği eksik"]
    status_warning: str | None = None

    try:
        from j0_live_status import (
            collect_status as _cs,
            _default_git_runner as _gr,
            _default_roadmap_loader as _rl,
        )
        _t_j0 = time.perf_counter()
        j0_status_obj = _cs(_gr, _rl)
        j0_status_ms_global = (time.perf_counter() - _t_j0) * 1000
        status_sample = j0_status_obj.text_summary()[:500]
    except Exception as exc:
        status_warning = (
            f"j0_status_collection_failed: {type(exc).__name__} — "
            f"Unicode validation using Turkish sentinel"
        )
        warnings.append(status_warning)
        # status_sample stays as _TURKISH_STATUS_SENTINEL (set above)

    # BLOCKER 2: gpu_used is not determined from backend string alone.
    # Only runtime evidence (model.device inspection) may set it to True.
    # For now, all real-probe paths leave gpu_used=None until proven.
    gpu_used: bool | None = None
    warnings.append(
        "gpu_used=null — CUDA/GPU usage not yet proven; "
        "check model.device after --real run to confirm"
    )

    # Run probes
    runs: list[dict[str, Any]] = []

    for i in range(n_runs):
        is_warmup = i == 0
        phrase = phrases[i % len(phrases)]

        # --- Ambient measurement ---
        ambient_rms: float | None = None
        ambient_peak: float | None = None
        ambient_ok = False
        ambient_exc: str | None = None

        try:
            ambient_arr = ambient_sampler()
            import numpy as np

            arr = np.array(ambient_arr, dtype=float)
            ambient_rms = float(np.sqrt(np.mean(arr ** 2)))
            ambient_peak = float(np.max(np.abs(arr)))
            ambient_ok = ambient_rms < 0.05
        except Exception as exc:
            ambient_exc = type(exc).__name__

        # BLOCKER 4: ambient exception must not create fake zeros + ambient_ok=True
        if ambient_exc is not None:
            runs.append({
                "warmup": is_warmup,
                "phrase_idx": i,
                "ambient_rms": None,
                "ambient_peak": None,
                "ambient_ok": False,
                "excluded_reason": "ambient_error",
                "ambient_error_type": ambient_exc,
                "t0_to_first_text_ms": None,
                "t0_to_first_audio_ms": None,
                "record_ms": None,
                "stt_ms": None,
            })
            continue

        # --- Main recording ---
        t0 = time.perf_counter()
        try:
            audio = audio_recorder(4.0)
        except Exception as exc:
            return {
                **_early,
                "ok": False,
                "error": f"recording_failed: {type(exc).__name__}",
            }

        record_ms = (time.perf_counter() - t0) * 1000
        t_after_record = time.perf_counter()

        # BLOCKER 3: STT exception must not produce fake recognized="" + stt_ms=0.0
        recognized: str | None = None
        stt_ms: float | None = None
        stt_exc: str | None = None

        try:
            recognized, stt_ms = stt_runner(audio)
        except Exception as exc:
            stt_exc = type(exc).__name__

        if stt_exc is not None:
            runs.append({
                "warmup": is_warmup,
                "phrase_idx": i,
                "ambient_rms": ambient_rms,
                "ambient_peak": ambient_peak,
                "ambient_ok": ambient_ok,
                "record_ms": record_ms,
                "excluded_reason": "stt_error",
                "stt_error_type": stt_exc,
                "t0_to_first_text_ms": None,
                "t0_to_first_audio_ms": None,
            })
            continue

        # Metrics — only reachable when STT succeeded
        t_text_ready = time.perf_counter()
        after_record_to_text_ms = (t_text_ready - t_after_record) * 1000
        t0_to_first_text_ms = record_ms + after_record_to_text_ms

        wer_raw, wer_normalized = compute_wer(phrase, recognized or "")

        runs.append({
            "warmup": is_warmup,
            "phrase_idx": i,
            "ambient_rms": ambient_rms,
            "ambient_peak": ambient_peak,
            "ambient_ok": ambient_ok,
            "record_ms": record_ms,
            "stt_ms": stt_ms,
            "after_record_to_text_ms": after_record_to_text_ms,
            "t0_to_first_text_ms": t0_to_first_text_ms,
            "t0_to_first_audio_ms": None,  # TTS not implemented yet
            "j0_status_ms": j0_status_ms_global,
            "total_command_to_response_ms": t0_to_first_text_ms + (j0_status_ms_global or 0.0),
            "recognized_text": recognized,
            "expected_text": phrase,
            "wer_raw": wer_raw,
            "wer_normalized": wer_normalized,
            "status_route_matched": "nerede" in (recognized or "").lower(),
            "status_summary_sample": status_sample,
        })

    agg = aggregate_runs(runs)

    # BLOCKER 2: gpu_verdict derived from latency verdict + proven GPU evidence.
    # gpu_used=None → "ölçülemedi" regardless of latency result.
    gpu_verdict = derive_gpu_verdict(agg["verdict"], gpu_used, measurement_valid=True)

    # Pick last successful (non-excluded) run for representative scalars
    _last = next(
        (r for r in reversed(runs) if not r.get("excluded_reason")),
        runs[-1] if runs else None,
    )

    def _last_field(key: str) -> Any:
        return _last.get(key) if _last else None

    return {
        "ok": True,
        "mode": "real",
        "measurement_valid": True,
        "ts": ts,
        "t0_definition": T0_DEFINITION,
        "device_info": str(devices[0].get("name", "unknown")) if devices else "unknown",
        "backend": backend_info["backend"],
        "model": backend_info["model"],
        "compute_type": backend_info["compute_type"],
        "gpu_used": gpu_used,
        "ambient_rms": _last_field("ambient_rms"),
        "ambient_peak": _last_field("ambient_peak"),
        "ambient_ok": _last_field("ambient_ok"),
        "record_ms": _last_field("record_ms"),
        "stt_ms": _last_field("stt_ms"),
        "after_record_to_text_ms": _last_field("after_record_to_text_ms"),
        "t0_to_first_text_ms": _last_field("t0_to_first_text_ms"),
        "t0_to_first_audio_ms": None,
        "j0_status_ms": j0_status_ms_global,
        "total_command_to_response_ms": _last_field("total_command_to_response_ms"),
        "recognized_text": _last_field("recognized_text"),
        "expected_text": _last_field("expected_text"),
        "wer_raw": _last_field("wer_raw"),
        "wer_normalized": _last_field("wer_normalized"),
        "status_route_matched": _last_field("status_route_matched"),
        # BLOCKER 5: always populated (real text or sentinel); null only with explicit warning
        "status_summary_sample": status_sample,
        "thresholds": THRESHOLDS,
        "metric_stats": agg["metric_stats"],
        "verdict": agg["verdict"],
        "gpu_verdict": gpu_verdict,
        "warnings": warnings,
        "runs": agg["annotated_runs"],
        "n_usable": agg["n"],
        "warmup_excluded": agg["warmup_excluded"],
        "ambient_excluded": agg["ambient_excluded"],
        "error_excluded": agg["error_excluded"],
    }


def run_real(phrases: list[str] | None = None, n_runs: int = 5) -> dict[str, Any]:
    """Run real mode. Requires sounddevice + faster-whisper installed."""
    return _real_probe(phrases=phrases, n_runs=n_runs)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="py -3.11 scripts/j0_spike_b_latency_probe.py",
        description="J0 Spike-B latency probe. --mock for schema check; --real for real measurement.",
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--mock", action="store_true", help="Mock mode — no hardware.")
    group.add_argument("--real", action="store_true", help="Real mode — microphone + STT.")
    p.add_argument("--runs", type=int, default=5, metavar="N", help="Number of runs (default 5).")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 1

    if args.mock:
        result = run_mock(n_runs=args.runs)
    else:
        result = run_real(n_runs=args.runs)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
