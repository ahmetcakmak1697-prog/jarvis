"""
tests/test_j0_spike_b_latency_probe.py — 24 required tests for J0 Spike-B.

Pure-function tests only — no microphone, no STT model, no hardware.
--real mode is exercised only via injected mocks (device_lister=lambda:[]).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

import pytest

import json as _json
import subprocess

from j0_spike_b_latency_probe import (
    STT_PHRASES,
    T0_DEFINITION,
    THRESHOLDS,
    _MOCK_RECORD_MS,
    _MOCK_STT_MS,
    _TURKISH_STATUS_SENTINEL,
    _VALID_T0_DEFINITIONS,
    _make_mock_run,
    _real_probe,
    aggregate_runs,
    classify_audio_latency,
    classify_wer,
    compute_wer,
    derive_gpu_verdict,
    emit_result,
    normalize_text,
    run_mock,
    validate_backend,
    validate_unicode,
)

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "j0_spike_b_latency_probe.py"

# ---------------------------------------------------------------------------
# Helper — build a minimal usable run dict
# ---------------------------------------------------------------------------

def _run(
    *,
    warmup: bool = False,
    ambient_ok: bool = True,
    t0: float = 1000.0,
    stt: float = 200.0,
    rec: float = 800.0,
    wer_r: float = 0.0,
    wer_n: float = 0.0,
) -> dict[str, Any]:
    return {
        "warmup": warmup,
        "ambient_ok": ambient_ok,
        "t0_to_first_text_ms": t0,
        "t0_to_first_audio_ms": None,
        "stt_ms": stt,
        "record_ms": rec,
        "wer_raw": wer_r,
        "wer_normalized": wer_n,
    }


# ---------------------------------------------------------------------------
# Test 1 — mock mode: measurement_valid is False
# ---------------------------------------------------------------------------

def test_mock_measurement_valid_false():
    result = run_mock()
    assert result["measurement_valid"] is False


# ---------------------------------------------------------------------------
# Test 2 — mock mode: summary starts with GEÇERSİZ ÖLÇÜM (MOCK)
# ---------------------------------------------------------------------------

def test_mock_summary_starts_gecersiz():
    result = run_mock()
    summary = result.get("summary", "")
    assert summary.startswith("GEÇERSİZ ÖLÇÜM (MOCK)"), (
        f"summary does not start with 'GEÇERSİZ ÖLÇÜM (MOCK)': {summary[:60]!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — mock mode: warning about 3070/GPU/latency decision
# ---------------------------------------------------------------------------

def test_mock_warning_mentions_3070_gpu():
    result = run_mock()
    warnings = result.get("warnings", [])
    combined = " ".join(warnings)
    assert "3070" in combined, "Missing '3070' in mock warnings"
    assert "GPU" in combined or "gpu" in combined.lower(), "Missing 'GPU' in mock warnings"
    assert "KULLANILAMAZ" in combined or "kullanilamaz" in combined.lower(), (
        "Missing 'KULLANILAMAZ' (cannot be used) in mock warnings"
    )


# ---------------------------------------------------------------------------
# Test 4 — metric names: t0_to_first_* present, no wake_to_*
# ---------------------------------------------------------------------------

def test_no_wake_metric_names():
    result = run_mock()
    assert "t0_to_first_audio_ms" in result, "t0_to_first_audio_ms key missing"
    assert "t0_to_first_text_ms" in result, "t0_to_first_text_ms key missing"
    for key in result:
        assert not key.startswith("wake_to_"), (
            f"Forbidden metric name '{key}' — no real wake-word detector is measured"
        )
    # Also check metric_stats
    for key in result.get("metric_stats", {}):
        assert not key.startswith("wake_to_"), (
            f"Forbidden metric stat key '{key}'"
        )


# ---------------------------------------------------------------------------
# Test 5 — t0_definition: mandatory and non-empty
# ---------------------------------------------------------------------------

def test_t0_definition_mandatory_nonempty():
    result = run_mock()
    assert "t0_definition" in result, "t0_definition key missing from output"
    td = result["t0_definition"]
    assert isinstance(td, str) and len(td) > 0, (
        f"t0_definition must be a non-empty string, got {td!r}"
    )


# ---------------------------------------------------------------------------
# Test 6 — t0_definition: must be one of the valid sentinel values
# ---------------------------------------------------------------------------

def test_t0_definition_valid_value():
    valid = ("recording_start", "keypress", "speech_onset")
    result = run_mock()
    td = result["t0_definition"]
    assert td in valid, f"t0_definition={td!r} not in valid set {valid}"
    # Also test the module-level constant
    assert T0_DEFINITION in valid


# ---------------------------------------------------------------------------
# Test 7 — metric math: t0_to_first_text_ms == record_ms + after_record_to_text_ms
# ---------------------------------------------------------------------------

def test_metric_math_record_plus_after_eq_t0():
    # Use _make_mock_run directly; run_idx_0=1 (non-warmup)
    phrase = "nerede kaldık"
    run = _make_mock_run(phrase, run_idx_0=1)
    rec = run["record_ms"]
    after = run["after_record_to_text_ms"]
    t0 = run["t0_to_first_text_ms"]
    assert t0 == pytest.approx(rec + after), (
        f"Math broken: t0={t0} != record_ms={rec} + after={after}"
    )
    # Verify concrete values from _MOCK_STT_MS[1] = 400
    expected_stt = _MOCK_STT_MS[1]  # 400.0
    expected_after = expected_stt + 20.0  # 420.0
    expected_t0 = _MOCK_RECORD_MS + expected_after  # 1420.0
    assert run["stt_ms"] == pytest.approx(expected_stt)
    assert t0 == pytest.approx(expected_t0)


# ---------------------------------------------------------------------------
# Test 8 — five runs: aggregate median / min / max correct
# ---------------------------------------------------------------------------

def test_five_runs_aggregate_median_min_max():
    # run_mock default is 5 runs:
    # run(0)=warmup excl, run(1)..run(4) usable
    # t0 values: 1420, 1320, 1520, 1620  (from _MOCK_STT_MS[1..4]+overhead)
    result = run_mock(n_runs=5)
    stats = result["metric_stats"]
    assert "t0_to_first_text_ms" in stats, "metric_stats missing t0_to_first_text_ms"
    t0s = stats["t0_to_first_text_ms"]
    assert t0s["median"] == pytest.approx(1470.0), f"Expected median 1470.0, got {t0s['median']}"
    assert t0s["min"] == pytest.approx(1320.0), f"Expected min 1320.0, got {t0s['min']}"
    assert t0s["max"] == pytest.approx(1620.0), f"Expected max 1620.0, got {t0s['max']}"
    assert t0s["n"] == 4, f"Expected n=4, got {t0s['n']}"


# ---------------------------------------------------------------------------
# Test 9 — warmup: first run excluded from statistics
# ---------------------------------------------------------------------------

def test_warmup_excluded_from_stats():
    result = run_mock(n_runs=5)
    assert result["warmup_excluded"] is True, "warmup_excluded should be True"
    assert result["n_usable"] == 4, "n_usable should be 4 (5 runs minus 1 warmup)"
    # warmup run should carry excluded_reason='warmup' in annotated runs list
    warmup_annotated = [r for r in result["runs"] if r.get("excluded_reason") == "warmup"]
    assert len(warmup_annotated) == 1, f"Expected 1 warmup run, got {len(warmup_annotated)}"
    assert warmup_annotated[0]["warmup"] is True


# ---------------------------------------------------------------------------
# Test 10 — n < 3 usable runs → verdict='yetersiz_veri', gpu_verdict='ölçülemedi'
# ---------------------------------------------------------------------------

def test_n_lt_3_usable_gives_yetersiz_veri():
    # 1 warmup + 2 usable = n=2 < 3
    runs = [
        _run(warmup=True, t0=1000.0),
        _run(warmup=False, t0=1100.0),
        _run(warmup=False, t0=1200.0),
    ]
    agg = aggregate_runs(runs)
    assert agg["verdict"] == "yetersiz_veri", (
        f"Expected 'yetersiz_veri' for n=2, got {agg['verdict']!r}"
    )
    # gpu_verdict is derived separately via derive_gpu_verdict, not returned by aggregate_runs
    assert "gpu_verdict" not in agg, "aggregate_runs must not return gpu_verdict"
    # derive_gpu_verdict with yetersiz_veri verdict → ölçülemedi (even with proven GPU)
    assert derive_gpu_verdict("yetersiz_veri", True, True) == "ölçülemedi"
    assert derive_gpu_verdict("yetersiz_veri", None, True) == "ölçülemedi"
    assert agg["n"] == 2


# ---------------------------------------------------------------------------
# Test 11 — missing TTS: t0_to_first_audio_ms is None (not 0.0) + warning emitted
# ---------------------------------------------------------------------------

def test_missing_tts_null_not_zero():
    result = run_mock()
    v = result["t0_to_first_audio_ms"]
    assert v is None, f"t0_to_first_audio_ms should be None (not 0), got {v!r}"
    # Warning about TTS must be present
    warnings = " ".join(result.get("warnings", []))
    assert "TTS" in warnings or "tts" in warnings.lower() or "metriği" in warnings, (
        "No TTS-missing warning found in output"
    )


# ---------------------------------------------------------------------------
# Test 12 — threshold boundaries: audio latency + WER
# ---------------------------------------------------------------------------

def test_threshold_audio_latency_boundaries():
    # Boundary at 1500 ms (pass) and 3000 ms (warn)
    assert classify_audio_latency(0.0) == "pass"
    assert classify_audio_latency(1500.0) == "pass"
    assert classify_audio_latency(1500.1) == "warn"
    assert classify_audio_latency(3000.0) == "warn"
    assert classify_audio_latency(3000.1) == "fail"
    assert classify_audio_latency(99999.0) == "fail"
    assert classify_audio_latency(None) == "not_measured"


def test_threshold_wer_boundaries():
    # Boundary at 10% (pass) and 25% (warn)
    assert classify_wer(0.0) == "pass"
    assert classify_wer(10.0) == "pass"
    assert classify_wer(10.1) == "warn"
    assert classify_wer(25.0) == "warn"
    assert classify_wer(25.1) == "fail"
    assert classify_wer(100.0) == "fail"


# ---------------------------------------------------------------------------
# Test 13 — WER rises on wrong recognition
# ---------------------------------------------------------------------------

def test_wer_rises_on_wrong_recognition():
    wer_raw, wer_norm = compute_wer("nerede kaldık", "başka bir şey söylendi")
    assert wer_raw > 0.0, "wer_raw should be > 0 for wrong recognition"
    assert wer_norm > 0.0, "wer_normalized should be > 0 for wrong recognition"


# ---------------------------------------------------------------------------
# Test 14 — WER normalization: "Nerede kaldık?" vs "nerede kaldık"
#           → wer_normalized == 0, wer_raw > 0
# ---------------------------------------------------------------------------

def test_wer_normalization_nerede_kaldik():
    expected = "Nerede kaldık?"
    recognized = "nerede kaldık"
    wer_raw, wer_normalized = compute_wer(expected, recognized)
    assert wer_normalized == pytest.approx(0.0), (
        f"wer_normalized should be 0 after normalization, got {wer_normalized}"
    )
    assert wer_raw > 0.0, (
        f"wer_raw should be > 0 (case/punctuation differ at word level), got {wer_raw}"
    )


# ---------------------------------------------------------------------------
# Test 15 — ambient_ok=False: excluded with excluded_reason='ambient'
# ---------------------------------------------------------------------------

def test_ambient_excluded_with_reason():
    runs = [
        _run(warmup=True, t0=1000.0),
        _run(warmup=False, ambient_ok=False, t0=1100.0),
        _run(warmup=False, t0=1200.0),
        _run(warmup=False, t0=1300.0),
        _run(warmup=False, t0=1400.0),
    ]
    agg = aggregate_runs(runs)
    assert agg["ambient_excluded"] == 1, (
        f"Expected 1 ambient-excluded run, got {agg['ambient_excluded']}"
    )
    ambient_runs = [r for r in agg["annotated_runs"] if r.get("excluded_reason") == "ambient"]
    assert len(ambient_runs) == 1, f"Expected 1 run with excluded_reason='ambient', got {len(ambient_runs)}"
    assert ambient_runs[0]["ambient_ok"] is False
    # Usable count = 5 - 1 warmup - 1 ambient = 3
    assert agg["n"] == 3


# ---------------------------------------------------------------------------
# Test 16 — CPU backend + gpu_used=True fails validation
# ---------------------------------------------------------------------------

def test_cpu_backend_gpu_used_true_fails_validation():
    errors = validate_backend("cpu", "int8", True)
    assert len(errors) > 0, (
        "validate_backend should return errors for cpu backend with gpu_used=True"
    )
    combined = " ".join(errors).lower()
    assert "contradiction" in combined or "cpu" in combined, (
        f"Error message does not mention contradiction/cpu: {errors}"
    )


def test_consistent_backends_pass_validation():
    # CUDA with gpu_used=True → valid
    assert validate_backend("cuda", "float16", True) == []
    # CPU with gpu_used=None → no contradiction
    assert validate_backend("cpu", "int8", None) == []
    # No backend → no errors
    assert validate_backend(None, None, None) == []


# ---------------------------------------------------------------------------
# Test 17 — no input device: _real_probe returns ok=False, error='no_input_device'
# ---------------------------------------------------------------------------

def test_no_input_device_returns_ok_false():
    result = _real_probe(
        phrases=["nerede kaldık"],
        n_runs=1,
        device_lister=lambda: [],  # empty → no microphone
    )
    assert result["ok"] is False, f"Expected ok=False, got {result['ok']}"
    assert result["error"] == "no_input_device", (
        f"Expected error='no_input_device', got {result.get('error')!r}"
    )
    assert result.get("t0_to_first_text_ms") is None, (
        "t0_to_first_text_ms should be None when no device"
    )
    assert result.get("t0_to_first_audio_ms") is None, (
        "t0_to_first_audio_ms should be None when no device"
    )
    # BLOCKER 6: t0_definition must be present on all output paths
    assert result.get("t0_definition") in _VALID_T0_DEFINITIONS, (
        f"t0_definition missing or invalid on no_input_device path: {result.get('t0_definition')!r}"
    )


# ---------------------------------------------------------------------------
# Test 18 — Unicode valid Turkish chars pass validate_unicode
# ---------------------------------------------------------------------------

def test_unicode_valid_turkish_passes():
    # All Turkish special chars, both cases
    ok, issues = validate_unicode("çğışüöÇĞİŞÜÖ nerede kaldık")
    assert ok is True, f"Valid Turkish text should pass, got issues: {issues}"
    assert issues == []


# ---------------------------------------------------------------------------
# Test 19 — Mojibake strings fail validate_unicode
# ---------------------------------------------------------------------------

def test_unicode_mojibake_fails():
    # Ã§ is UTF-8 'ç' (0xC3 0xA7) decoded as cp1252
    ok, issues = validate_unicode("Ã§alışma")
    assert ok is False, "Mojibake text should fail validate_unicode"
    assert len(issues) > 0, "Should have at least one issue reported"


def test_unicode_replacement_char_fails():
    ok, issues = validate_unicode("nerede �kaldık")
    assert ok is False, "U+FFFD replacement char should fail validate_unicode"


# ---------------------------------------------------------------------------
# Test 20 — gpu_used: mock output reflects backend, not hardcoded True
# ---------------------------------------------------------------------------

def test_gpu_used_not_hardcoded_true():
    result = run_mock()
    # Mock uses CPU backend; gpu_used should NOT be True
    gpu_used = result["gpu_used"]
    assert gpu_used is not True, (
        f"gpu_used should not be hardcoded True for mock CPU backend; got {gpu_used!r}"
    )
    assert result["backend"] in ("cpu", "mock-cpu", "injected", "cpu"), (
        f"Unexpected backend for mock: {result['backend']!r}"
    )


# ---------------------------------------------------------------------------
# Test 21 — output schema: all required fields present
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = [
    "ok", "mode", "measurement_valid", "ts", "t0_definition",
    "device_info", "backend", "model", "compute_type", "gpu_used",
    "ambient_rms", "ambient_peak", "ambient_ok",
    "record_ms", "stt_ms", "after_record_to_text_ms",
    "t0_to_first_text_ms", "t0_to_first_audio_ms",
    "j0_status_ms", "total_command_to_response_ms",
    "recognized_text", "expected_text",
    "wer_raw", "wer_normalized",
    "status_route_matched", "status_summary_sample",
    "thresholds", "metric_stats", "verdict", "gpu_verdict",
    "warnings", "runs",
]


def test_output_has_all_required_fields():
    result = run_mock()
    missing = [f for f in _REQUIRED_FIELDS if f not in result]
    assert missing == [], f"Required fields missing from output: {missing}"


# ---------------------------------------------------------------------------
# Test 22 — AST: no forbidden imports (telegram / scheduler / requests / http libs)
# ---------------------------------------------------------------------------

_FORBIDDEN_TOP_LEVEL = {"telegram", "requests", "httpx", "aiohttp", "schedule", "threading"}


def test_no_forbidden_imports_in_script():
    assert _SCRIPT_PATH.is_file(), f"Script not found: {_SCRIPT_PATH}"
    tree = ast.parse(_SCRIPT_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                assert top not in _FORBIDDEN_TOP_LEVEL, (
                    f"Forbidden import '{alias.name}' at line {node.lineno}"
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                assert top not in _FORBIDDEN_TOP_LEVEL, (
                    f"Forbidden 'from {node.module} import ...' at line {node.lineno}"
                )


# ---------------------------------------------------------------------------
# Test 23 — mock mode does not require sounddevice to be installed
# ---------------------------------------------------------------------------

def test_mock_mode_does_not_import_sounddevice():
    """run_mock must work even when sounddevice is not installed."""
    saved = sys.modules.pop("sounddevice", None)
    try:
        result = run_mock()
        assert result["mode"] == "mock", "Expected mode='mock'"
        assert result["measurement_valid"] is False
    finally:
        if saved is not None:
            sys.modules["sounddevice"] = saved


# ---------------------------------------------------------------------------
# Test 24 — existing J0 live-status module is still importable and intact
# ---------------------------------------------------------------------------

def test_existing_j0_module_still_importable():
    from j0_live_status import collect_status, LiveStatus, _default_git_runner
    assert callable(collect_status), "collect_status must be callable"
    assert LiveStatus is not None
    assert callable(_default_git_runner), "_default_git_runner must be callable"


# ===========================================================================
# BLOCKER 1 — Mock must never look like a real pass
# ===========================================================================

def test_mock_verdict_is_gecersiz_olcum():
    """Mock verdict must not be 'yeterli' — it is explicitly invalid."""
    result = run_mock()
    assert result["verdict"] == "geçersiz_ölçüm", (
        f"mock verdict should be 'geçersiz_ölçüm', got {result['verdict']!r}"
    )


def test_mock_gpu_verdict_is_olculemedi():
    """Mock gpu_verdict must be 'ölçülemedi' — no GPU evidence in mock."""
    result = run_mock()
    assert result["gpu_verdict"] == "ölçülemedi", (
        f"mock gpu_verdict should be 'ölçülemedi', got {result['gpu_verdict']!r}"
    )


def test_measurement_valid_false_never_produces_yeterli():
    """derive_gpu_verdict must return 'ölçülemedi' when measurement_valid=False."""
    # Even with gpu_used=True, measurement_valid=False → ölçülemedi
    assert derive_gpu_verdict("yeterli", True, measurement_valid=False) == "ölçülemedi"
    assert derive_gpu_verdict("sınırda", True, measurement_valid=False) == "ölçülemedi"
    # And mock output must have measurement_valid=False
    result = run_mock()
    assert result["measurement_valid"] is False
    # Cross-check: verdict and gpu_verdict are both invalid
    assert result["verdict"] != "yeterli"
    assert result["gpu_verdict"] != "yeterli"


# ===========================================================================
# BLOCKER 2 — gpu_verdict requires proven GPU runtime evidence
# ===========================================================================

def test_gpu_used_null_gives_olculemedi():
    """gpu_used=None (unproven) must produce gpu_verdict='ölçülemedi'."""
    # Regardless of latency verdict
    assert derive_gpu_verdict("yeterli", None, True) == "ölçülemedi"
    assert derive_gpu_verdict("sınırda", None, True) == "ölçülemedi"
    assert derive_gpu_verdict("yetersiz", None, True) == "ölçülemedi"


def test_cuda_unproven_cannot_give_yeterli_gpu():
    """Without proven CUDA/GPU evidence gpu_verdict cannot be 'yeterli'."""
    # gpu_used=None even if verdict is good
    gv = derive_gpu_verdict("yeterli", None, measurement_valid=True)
    assert gv != "yeterli", (
        f"gpu_verdict='yeterli' without proven GPU: got {gv!r}"
    )
    # gpu_used=False also cannot give yeterli
    gv2 = derive_gpu_verdict("yeterli", False, measurement_valid=True)
    assert gv2 != "yeterli", (
        f"gpu_verdict='yeterli' with gpu_used=False: got {gv2!r}"
    )


def test_gpu_used_false_gives_yetersiz_gpu():
    """gpu_used=False means no GPU → gpu_verdict='yetersiz'."""
    assert derive_gpu_verdict("yeterli", False, True) == "yetersiz"
    assert derive_gpu_verdict("sınırda", False, True) == "yetersiz"


def test_proven_gpu_maps_verdict():
    """Only gpu_used=True maps latency verdict to gpu_verdict."""
    assert derive_gpu_verdict("yeterli", True, True) == "yeterli"
    assert derive_gpu_verdict("sınırda", True, True) == "sınırda"
    assert derive_gpu_verdict("yetersiz", True, True) == "yetersiz"
    assert derive_gpu_verdict("yetersiz_veri", True, True) == "ölçülemedi"


# ===========================================================================
# BLOCKER 3 — STT exceptions must not create fake zeros
# ===========================================================================

def _mock_device():
    return [{"name": "mock_mic", "max_input_channels": 1}]


def _mock_audio(seconds: float):
    return [0.0] * max(1, int(seconds * 16000))


def test_stt_exception_no_fake_zeros():
    """STT failure must not produce recognized='' and stt_ms=0.0."""
    def failing_stt(_audio):
        raise RuntimeError("model_load_failed")

    result = _real_probe(
        phrases=["nerede kaldık"],
        n_runs=2,
        device_lister=_mock_device,
        audio_recorder=_mock_audio,
        ambient_sampler=lambda: [0.0] * 8000,
        stt_runner=failing_stt,
    )
    runs = result.get("runs", [])
    stt_error_runs = [r for r in runs if r.get("excluded_reason") == "stt_error"]
    assert len(stt_error_runs) > 0, "Expected at least one stt_error excluded run"
    for r in stt_error_runs:
        # Must NOT have fake zero stt_ms
        assert r.get("stt_ms") is None, (
            f"stt_ms should be None on STT error, got {r.get('stt_ms')!r}"
        )
        # Must NOT have fake empty recognized_text
        assert "recognized_text" not in r or r.get("recognized_text") is None, (
            f"recognized_text should be absent/None on STT error"
        )
        # Must NOT have fake t0_to_first_text_ms
        assert r.get("t0_to_first_text_ms") is None, (
            "t0_to_first_text_ms should be None on STT error"
        )


def test_stt_exception_excluded_with_stt_error_reason():
    """STT failure run must carry excluded_reason='stt_error' and be excluded from stats."""
    call_n = [0]

    def sometimes_failing_stt(_audio):
        call_n[0] += 1
        if call_n[0] == 1:  # warmup pass
            return ("ok", 100.0)
        raise RuntimeError("transcription_error")

    result = _real_probe(
        phrases=["nerede kaldık"],
        n_runs=3,
        device_lister=_mock_device,
        audio_recorder=_mock_audio,
        ambient_sampler=lambda: [0.0] * 8000,
        stt_runner=sometimes_failing_stt,
    )
    runs = result.get("runs", [])
    stt_error_runs = [r for r in runs if r.get("excluded_reason") == "stt_error"]
    assert len(stt_error_runs) >= 1, "Expected stt_error excluded runs"

    # Verdict must not be 'yeterli' when most/all non-warmup runs failed STT
    assert result.get("verdict") != "yeterli", (
        "verdict should not be 'yeterli' when STT errors dominate"
    )


# ===========================================================================
# BLOCKER 4 — Ambient exceptions must not create fake zeros
# ===========================================================================

def test_ambient_exception_no_fake_zeros():
    """Ambient sampler failure must not produce ambient_rms=0, ambient_peak=0, ambient_ok=True."""
    def failing_ambient():
        raise RuntimeError("device_error")

    result = _real_probe(
        phrases=["nerede kaldık"],
        n_runs=2,
        device_lister=_mock_device,
        audio_recorder=_mock_audio,
        ambient_sampler=failing_ambient,
        stt_runner=lambda a: ("nerede kaldık", 100.0),
    )
    runs = result.get("runs", [])
    ambient_error_runs = [r for r in runs if r.get("excluded_reason") == "ambient_error"]
    assert len(ambient_error_runs) > 0, "Expected ambient_error excluded runs"
    for r in ambient_error_runs:
        assert r.get("ambient_rms") is None, (
            f"ambient_rms must be None on ambient error, got {r.get('ambient_rms')!r}"
        )
        assert r.get("ambient_peak") is None, (
            f"ambient_peak must be None on ambient error, got {r.get('ambient_peak')!r}"
        )
        # ambient_ok must NOT be True (fake clean room)
        assert r.get("ambient_ok") is not True, (
            "ambient_ok must not be True when ambient sampling failed"
        )


def test_ambient_exception_excluded_from_stats():
    """Ambient error runs must be excluded from statistical aggregation."""
    def failing_ambient():
        raise RuntimeError("device_error")

    result = _real_probe(
        phrases=["nerede kaldık"],
        n_runs=2,
        device_lister=_mock_device,
        audio_recorder=_mock_audio,
        ambient_sampler=failing_ambient,
        stt_runner=lambda a: ("nerede kaldık", 100.0),
    )
    # n_usable must exclude ambient_error runs
    error_excluded = result.get("error_excluded", 0)
    ambient_excluded = result.get("ambient_excluded", 0)
    total_excluded = error_excluded + ambient_excluded + (1 if result.get("warmup_excluded") else 0)
    n_usable = result.get("n_usable", 0)
    # With 2 runs and ambient failing on both: n_usable < 3 → verdict='yetersiz_veri'
    assert result.get("verdict") in ("yetersiz_veri", "ölçülemedi"), (
        f"Expected low-data verdict when ambient fails, got {result.get('verdict')!r}"
    )


# ===========================================================================
# BLOCKER 5 — status_summary_sample populated; sentinel has all Turkish chars
# ===========================================================================

def test_sentinel_has_all_required_turkish_chars():
    """_TURKISH_STATUS_SENTINEL must contain all 7 required Turkish chars."""
    required = [
        ("ç", "ç c-cedilla"),
        ("ğ", "ğ g-breve"),
        ("ı", "ı dotless-i"),
        ("İ", "İ I-with-dot"),
        ("ö", "ö o-umlaut"),
        ("ş", "ş s-cedilla"),
        ("ü", "ü u-umlaut"),
    ]
    for char, name in required:
        assert char in _TURKISH_STATUS_SENTINEL, (
            f"Required Turkish char {name} ({char!r}) missing from sentinel"
        )


def test_mock_status_summary_sample_populated():
    """Mock output must have a non-null status_summary_sample."""
    result = run_mock()
    sample = result.get("status_summary_sample")
    assert sample is not None, "status_summary_sample must not be None in mock output"
    assert isinstance(sample, str) and len(sample) > 0, (
        "status_summary_sample must be a non-empty string"
    )


def test_mock_status_summary_sample_has_turkish_chars():
    """status_summary_sample in mock output must contain all required Turkish chars."""
    result = run_mock()
    sample = result["status_summary_sample"]
    required = ["ç", "ğ", "ı", "İ", "ö", "ş", "ü"]
    for char in required:
        assert char in sample, (
            f"Required Turkish char {char!r} missing from status_summary_sample"
        )


def test_real_status_summary_sample_populated_or_warned():
    """Real probe with injected STT must set status_summary_sample (real or sentinel + warning)."""
    result = _real_probe(
        phrases=["nerede kaldık"],
        n_runs=2,
        device_lister=_mock_device,
        audio_recorder=_mock_audio,
        ambient_sampler=lambda: [0.0] * 8000,
        stt_runner=lambda a: ("nerede kaldık", 100.0),
    )
    sample = result.get("status_summary_sample")
    # Either populated (real or sentinel) — never silently null
    if sample is None:
        warnings_text = " ".join(result.get("warnings", []))
        assert "status" in warnings_text.lower() or "j0_status" in warnings_text.lower(), (
            "status_summary_sample is None without an explicit status warning"
        )
    else:
        assert isinstance(sample, str) and len(sample) > 0


def test_unicode_null_sample_without_warning_would_fail():
    """validate_unicode must reject mojibake; null sample cannot silently pass."""
    # Null is not a string — validate_unicode requires text; callers must not pass null
    # Check that a mojibake string fails
    ok, issues = validate_unicode("Ã§alışma ağacı")
    assert ok is False, "Mojibake string must fail validate_unicode"
    # And that the sentinel passes (no mojibake)
    ok2, issues2 = validate_unicode(_TURKISH_STATUS_SENTINEL)
    assert ok2 is True, f"Sentinel must pass validate_unicode, got issues: {issues2}"


# ===========================================================================
# BLOCKER 6 — t0_definition on ALL early-return paths
# ===========================================================================

def test_missing_sounddevice_early_return_has_t0_definition():
    """sounddevice_not_installed early return must include t0_definition."""
    # Temporarily hide sounddevice to trigger the ImportError path
    saved = sys.modules.pop("sounddevice", None)
    try:
        result = _real_probe(phrases=["nerede kaldık"], n_runs=1)
        # Either sounddevice was already loaded (not None), or early-exit was triggered
        if result.get("ok") is False and result.get("error") == "sounddevice_not_installed":
            assert result.get("t0_definition") in _VALID_T0_DEFINITIONS, (
                f"t0_definition missing on sounddevice_not_installed path: "
                f"{result.get('t0_definition')!r}"
            )
    finally:
        if saved is not None:
            sys.modules["sounddevice"] = saved


def test_all_injected_early_failures_have_t0_definition():
    """All _real_probe early-failure paths via device_lister must include t0_definition."""
    # no_input_device path (already strengthened in test 17, verify once more)
    result = _real_probe(phrases=["nerede kaldık"], n_runs=1, device_lister=lambda: [])
    assert result.get("t0_definition") in _VALID_T0_DEFINITIONS, (
        f"t0_definition missing on no_input_device path: {result.get('t0_definition')!r}"
    )


# ===========================================================================
# UTF-8 stdout encoding — subprocess byte tests (no PYTHONIOENCODING)
# ===========================================================================

def test_mock_cli_stdout_is_strict_utf8_bytes():
    """Spike-B --mock must emit raw UTF-8 bytes without PYTHONIOENCODING override.

    Forbidden: text=True, PYTHONIOENCODING in env, errors='ignore'/'replace',
    CP1254 decode. Fail if strict UTF-8 decode raises UnicodeDecodeError.
    """
    script = Path(__file__).resolve().parents[1] / "scripts" / "j0_spike_b_latency_probe.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--mock"],
        capture_output=True,
        text=False,  # raw bytes — never text=True
        # No PYTHONIOENCODING in env (inherit parent, which may be CP1254)
    )
    assert proc.returncode == 0, (
        f"Spike-B --mock exited {proc.returncode}\nstderr={proc.stderr[:200]!r}"
    )

    # Must decode strictly as UTF-8 — UnicodeDecodeError = CP1254 leaked through
    text = proc.stdout.decode("utf-8", errors="strict")
    parsed = _json.loads(text)

    assert parsed["measurement_valid"] is False
    assert parsed["verdict"] == "geçersiz_ölçüm", (
        f"verdict={parsed['verdict']!r} — expected 'geçersiz_ölçüm'"
    )
    assert parsed["gpu_verdict"] == "ölçülemedi", (
        f"gpu_verdict={parsed['gpu_verdict']!r} — expected 'ölçülemedi'"
    )
    summary = parsed.get("summary", "")
    assert summary.startswith("GEÇERSİZ ÖLÇÜM (MOCK)"), (
        f"summary does not start with 'GEÇERSİZ ÖLÇÜM (MOCK)': {summary[:60]!r}"
    )
    sample = parsed.get("status_summary_sample", "")
    for char in ["ç", "ğ", "ı", "İ", "ö", "ş", "ü"]:
        assert char in sample, (
            f"Turkish char {char!r} missing from status_summary_sample in raw UTF-8 output"
        )


def test_real_mode_serialization_path_is_utf8():
    """Real-mode emit_result() must produce UTF-8 JSON identical to mock path (no hardware).

    Uses BytesIO+TextIOWrapper to capture bytes from the shared emit_result()
    function, proving real-mode serialization uses the same UTF-8 writer as mock.
    """
    import io

    payload = {
        "ok": True,
        "mode": "real",
        "measurement_valid": False,
        "ts": "2026-01-01T00:00:00+00:00",
        "verdict": "yetersiz_veri",
        "gpu_verdict": "ölçülemedi",
        "recognized_text": "nerede kaldık, şğışçöü",
        "status_summary_sample": (
            "Çalışma ağacı: TEMİZ\n"
            "henüz devrede değil\n"
            "Telegram gönderme\n"
            "nerede kaldık araçtır\n"
            "Şu an devam eden: İ"
        ),
    }

    buf = io.BytesIO()
    wrapper = io.TextIOWrapper(buf, encoding="utf-8", errors="strict")
    emit_result(payload, stream=wrapper)
    wrapper.flush()

    raw = buf.getvalue()
    # Strict decode — proves the bytes written are valid UTF-8
    decoded = raw.decode("utf-8", errors="strict")
    parsed = _json.loads(decoded)

    assert parsed["mode"] == "real"
    assert parsed["recognized_text"] == "nerede kaldık, şğışçöü"
    for char in ["ç", "ğ", "ı", "İ", "ö", "ş", "ü"]:
        assert char in parsed["status_summary_sample"], (
            f"Turkish char {char!r} missing from real-mode serialized status_summary_sample"
        )
