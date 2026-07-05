"""
tests/test_blackbox_log.py — BLACKBOX-0 audit log tests.

Coverage:
  1.  append first event → sequence=1, previous_event_hash=null
  2.  append second event → links to first event_hash
  3.  validate clean log → ok=True
  4.  tampering with first event → validation failure
  5.  deleting a middle event → validation failure
  6.  duplicate sequence → validation failure
  7.  invalid JSON line → validation failure
  8.  missing required field → validation failure
  9.  append succeeds despite corrupt prior log → integrity_warnings
  10. append succeeds despite broken hash chain → integrity_warnings
  11. clean log matches its anchor
  12. tampered log fails against old anchor
  13. recomputing event hashes after tampering still fails old anchor digest
  14. concurrency: two threads → no duplicate sequence
  15. redaction removes obvious secrets
  16. redaction does not destroy normal text
  17. raw diff/log evidence is not stored verbatim
  18. event_hash is deterministic
  19. UTF-8 Turkish text survives round-trip
  20. raw bytes decode strictly as UTF-8
  21. no mojibake markers in output
  22. commit_hash=null is valid (no self-referential requirement)
  23. Codex verdict event records PASS/CONCERN/BLOCKER
  24. safety_flags records sprint constraints
  25. validate_log returns structured errors, not only bool
"""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Optional

import pytest

# Ensure agents/ is on sys.path
import sys
_AGENTS_DIR = Path(__file__).resolve().parents[1] / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

from blackbox_log import (
    AppendResult,
    AnchorVerifyResult,
    ValidationResult,
    append_event,
    compute_log_digest,
    create_anchor_record,
    validate_log,
    verify_anchor,
    _canonical_json,
    _compute_event_hash,
    _redact_dict,
    _sanitize_evidence,
    _sanitize_forbidden_keys,
    _sanitize_value,
    REQUIRED_FIELDS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOJIBAKE_MARKERS = ["Ã", "Ä", "Å", "â€", "Ã§", "Ä±", "�"]

_MINIMAL_EVENT = {
    "event_type": "sprint_started",
    "sprint_id": "BB0-test",
    "actor": "ClaudeCode",
    "summary": "Test sprint started",
}


def _minimal(overrides: dict | None = None) -> dict:
    e = dict(_MINIMAL_EVENT)
    if overrides:
        e.update(overrides)
    return e


# ---------------------------------------------------------------------------
# 1. First event: sequence=1, previous_event_hash=null
# ---------------------------------------------------------------------------


def test_first_event_sequence_and_prev_hash(tmp_path):
    log = tmp_path / "bb.jsonl"
    result = append_event(log, _minimal())

    assert result.ok, f"Expected ok; got error={result.error}"
    assert result.appended
    assert result.sequence == 1
    assert result.previous_event_hash is None

    line = log.read_text(encoding="utf-8").strip()
    event = json.loads(line)
    assert event["sequence"] == 1
    assert event["previous_event_hash"] is None


# ---------------------------------------------------------------------------
# 2. Second event links to first event_hash
# ---------------------------------------------------------------------------


def test_second_event_links_to_first(tmp_path):
    log = tmp_path / "bb.jsonl"
    r1 = append_event(log, _minimal({"summary": "event 1"}))
    r2 = append_event(log, _minimal({"summary": "event 2"}))

    assert r1.ok and r2.ok
    assert r2.sequence == 2
    assert r2.previous_event_hash == r1.event_hash

    lines = log.read_text(encoding="utf-8").strip().splitlines()
    e2 = json.loads(lines[1])
    assert e2["previous_event_hash"] == r1.event_hash


# ---------------------------------------------------------------------------
# 3. Validate clean log passes
# ---------------------------------------------------------------------------


def test_validate_clean_log_ok(tmp_path):
    log = tmp_path / "bb.jsonl"
    for i in range(3):
        append_event(log, _minimal({"summary": f"event {i}"}))

    result = validate_log(log)
    assert result.ok, f"Expected ok=True; errors={result.errors}"
    assert result.event_count == 3
    assert result.last_sequence == 3
    assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# 4. Tampering with first event causes validation failure
# ---------------------------------------------------------------------------


def test_tampered_first_event_fails_validation(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({"summary": "original summary"}))
    append_event(log, _minimal({"summary": "second event"}))

    # Rewrite first line with modified summary
    lines = log.read_text(encoding="utf-8").splitlines()
    e1 = json.loads(lines[0])
    e1["summary"] = "TAMPERED summary"
    lines[0] = _canonical_json(e1)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = validate_log(log)
    assert not result.ok
    assert any("event_hash" in err or "mismatch" in err.lower() for err in result.errors), (
        f"Expected hash mismatch error; got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# 5. Deleting a middle event causes validation failure
# ---------------------------------------------------------------------------


def test_deleted_middle_event_fails_validation(tmp_path):
    log = tmp_path / "bb.jsonl"
    for i in range(3):
        append_event(log, _minimal({"summary": f"event {i}"}))

    lines = log.read_text(encoding="utf-8").splitlines()
    # Remove the middle event (index 1 = sequence 2)
    lines.pop(1)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = validate_log(log)
    assert not result.ok
    assert any("sequence" in err.lower() or "out-of-order" in err.lower()
               or "previous_event_hash" in err for err in result.errors), (
        f"Expected sequence/chain error; got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# 6. Duplicate sequence causes validation failure
# ---------------------------------------------------------------------------


def test_duplicate_sequence_fails_validation(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({"summary": "event 1"}))
    append_event(log, _minimal({"summary": "event 2"}))

    # Manually craft a third line with duplicate sequence=2
    lines = log.read_text(encoding="utf-8").splitlines()
    e1 = json.loads(lines[0])
    # Build a fake event with sequence=2 (duplicate)
    fake = dict(e1)
    fake["sequence"] = 2
    fake["summary"] = "duplicate"
    fake["event_hash"] = _compute_event_hash(fake)
    lines.append(_canonical_json(fake))
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = validate_log(log)
    assert not result.ok
    assert any("duplicate" in err.lower() for err in result.errors), (
        f"Expected duplicate sequence error; got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# 7. Invalid JSON line causes validation failure
# ---------------------------------------------------------------------------


def test_invalid_json_line_fails_validation(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal())

    with log.open("ab") as f:
        f.write(b"NOT_VALID_JSON\n")

    result = validate_log(log)
    assert not result.ok
    assert any("invalid json" in err.lower() for err in result.errors), (
        f"Expected invalid JSON error; got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# 8. Missing required field causes validation failure
# ---------------------------------------------------------------------------


def test_missing_required_field_fails_validation(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal())

    lines = log.read_text(encoding="utf-8").splitlines()
    e1 = json.loads(lines[0])
    del e1["actor"]  # remove required field
    # Don't recompute hash (also tests hash mismatch)
    lines[0] = _canonical_json(e1)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = validate_log(log)
    assert not result.ok
    found_field_error = any(
        "actor" in err or "missing required" in err.lower()
        for err in result.errors
    )
    assert found_field_error, f"Expected missing-field error; got: {result.errors}"


# ---------------------------------------------------------------------------
# 9. Append succeeds despite corrupt prior log (integrity_warnings)
# ---------------------------------------------------------------------------


def test_append_succeeds_despite_corrupt_log(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal())

    # Corrupt the existing line
    log.write_bytes(b"CORRUPT_LINE\n")

    result = append_event(log, _minimal({"summary": "new event after corruption"}))

    assert result.ok, f"append_event must succeed despite corrupt log; error={result.error}"
    assert result.appended
    assert len(result.integrity_warnings) > 0, (
        "Expected integrity_warnings about the corrupt prior log"
    )


# ---------------------------------------------------------------------------
# 10. Append succeeds despite broken hash chain (integrity_warnings)
# ---------------------------------------------------------------------------


def test_append_succeeds_despite_broken_chain(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({"summary": "event 1"}))
    append_event(log, _minimal({"summary": "event 2"}))

    # Tamper with first event hash field
    lines = log.read_text(encoding="utf-8").splitlines()
    e1 = json.loads(lines[0])
    e1["event_hash"] = "a" * 64  # valid hex length but wrong value
    lines[0] = _canonical_json(e1)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = append_event(log, _minimal({"summary": "event 3 after chain break"}))

    assert result.ok, f"append_event must succeed; error={result.error}"
    assert result.appended
    assert len(result.integrity_warnings) > 0, (
        "Expected integrity_warnings about the broken chain"
    )


# ---------------------------------------------------------------------------
# 11. Clean log matches its anchor
# ---------------------------------------------------------------------------


def test_clean_log_matches_anchor(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({"summary": "anchor test"}))

    anchor = create_anchor_record(log, git_head="abc123", sprint_id="BB0-test")
    result = verify_anchor(log, anchor)

    assert result.ok
    assert result.match, "Clean log must match its own anchor"
    assert result.anchor_digest == result.current_digest


# ---------------------------------------------------------------------------
# 12. Tampered log fails against old anchor
# ---------------------------------------------------------------------------


def test_tampered_log_fails_anchor(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({"summary": "pre-anchor event"}))

    anchor = create_anchor_record(log, sprint_id="BB0-test")

    # Tamper: append a new event after the anchor was created
    append_event(log, _minimal({"summary": "new event after anchor"}))

    result = verify_anchor(log, anchor)
    assert result.ok
    assert not result.match, "Modified log must NOT match old anchor"


# ---------------------------------------------------------------------------
# 13. Recomputing event hashes after tampering still fails old anchor digest
# ---------------------------------------------------------------------------


def test_recomputed_hashes_still_fail_old_anchor(tmp_path):
    """Fully recomputing the entire hash chain after tampering still fails old anchor.

    This proves the Git-anchored file digest catches a tamper that a fully
    internally-consistent chain (where ALL hashes are recomputed) would not.
    After the recompute, validate_log must pass (chain is consistent) but
    verify_anchor must still fail (file bytes differ from anchor).
    """
    log = tmp_path / "bb.jsonl"
    for i in range(3):
        append_event(log, _minimal({"summary": f"event {i}"}))

    anchor = create_anchor_record(log, sprint_id="BB0-test")
    old_digest = anchor["log_digest_sha256"]

    # Tamper event 1 and fully rebuild the entire hash chain from scratch
    lines = log.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines if line.strip()]

    # Modify first event content
    events[0]["summary"] = "FULLY_RECOMPUTED_TAMPERED_SUMMARY"

    # Rebuild every event's previous_event_hash and event_hash in order
    prev_hash: Optional[str] = None
    rebuilt = []
    for ev in events:
        ev["previous_event_hash"] = prev_hash
        ev.pop("event_hash", None)
        new_hash = _compute_event_hash(ev)
        ev["event_hash"] = new_hash
        rebuilt.append(_canonical_json(ev))
        prev_hash = new_hash

    log.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")

    # Internal chain is now consistent — validate_log should report ok
    vr = validate_log(log)
    assert vr.ok, (
        f"Fully recomputed chain must be internally consistent; errors={vr.errors}"
    )

    # But file bytes changed — old anchor digest must NOT match
    new_digest = compute_log_digest(log)
    assert new_digest != old_digest, (
        "File digest must differ from old anchor after full chain recompute"
    )

    result = verify_anchor(log, anchor)
    assert not result.match, (
        "Fully recomputed internal chain must still fail the old Git anchor digest"
    )


# ---------------------------------------------------------------------------
# 14. Concurrency: two threads append without duplicate sequence
# ---------------------------------------------------------------------------


def test_concurrency_no_duplicate_sequence(tmp_path):
    log = tmp_path / "concurrent.jsonl"
    results: list[AppendResult] = []
    lock = threading.Lock()

    def do_append(i: int) -> None:
        r = append_event(log, _minimal({"summary": f"concurrent event {i}"}))
        with lock:
            results.append(r)

    threads = [threading.Thread(target=do_append, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    failed = [r for r in results if not r.ok]
    assert not failed, f"Some appends failed: {[r.error for r in failed]}"

    sequences = [r.sequence for r in results]
    assert len(set(sequences)) == len(sequences), (
        f"Duplicate sequences detected: {sorted(sequences)}"
    )
    assert sorted(sequences) == list(range(1, 7)), (
        f"Expected sequences 1-6; got: {sorted(sequences)}"
    )


# ---------------------------------------------------------------------------
# 15. Redaction removes obvious secrets
# ---------------------------------------------------------------------------


def test_redaction_removes_telegram_token(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({
        "details": {"telegram_bot_token": "bot1234567890:ABC-secret_token_here"},
    }))

    content = log.read_text(encoding="utf-8")
    assert "bot1234567890" not in content, "Telegram token must be redacted"
    assert "[REDACTED]" in content


def test_redaction_removes_api_key(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({
        "details": {"api_key": "sk-abc123verylongapikey"},
    }))

    content = log.read_text(encoding="utf-8")
    assert "sk-abc123verylongapikey" not in content
    assert "[REDACTED]" in content


def test_redaction_removes_bearer_token_in_string(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({
        "summary": "called API with Bearer ABCDEFGH12345678token",
    }))

    content = log.read_text(encoding="utf-8")
    assert "ABCDEFGH12345678token" not in content
    assert "[REDACTED" in content


# ---------------------------------------------------------------------------
# 16. Redaction does not destroy normal text
# ---------------------------------------------------------------------------


def test_redaction_preserves_normal_text(tmp_path):
    log = tmp_path / "bb.jsonl"
    summary = "Sprint BB0 completed successfully with 247 tests passing."
    append_event(log, _minimal({"summary": summary}))

    content = log.read_text(encoding="utf-8")
    assert "247 tests passing" in content, (
        "Normal text must survive redaction"
    )
    assert "BB0 completed" in content


# ---------------------------------------------------------------------------
# 17. Raw diff/log evidence is not stored verbatim
# ---------------------------------------------------------------------------


def test_raw_diff_not_stored_verbatim(tmp_path):
    log = tmp_path / "bb.jsonl"
    raw_diff_content = "diff --git a/foo.py b/foo.py\n+added line\n-removed line"
    append_event(log, _minimal({
        "evidence": {"raw_diff": raw_diff_content},
    }))

    content = log.read_text(encoding="utf-8")
    assert raw_diff_content not in content, (
        "raw_diff content must not be stored verbatim"
    )
    assert "[REDACTED:raw_blob_not_allowed]" in content


def test_full_stdout_not_stored_verbatim(tmp_path):
    log = tmp_path / "bb.jsonl"
    stdout_blob = "line1\nline2\nline3\n" * 100
    append_event(log, _minimal({
        "details": {"full_stdout": stdout_blob},
    }))

    content = log.read_text(encoding="utf-8")
    assert stdout_blob not in content
    assert "[REDACTED:raw_blob_not_allowed]" in content


# ---------------------------------------------------------------------------
# 18. event_hash is deterministic
# ---------------------------------------------------------------------------


def test_event_hash_is_deterministic():
    body: dict[str, Any] = {
        "schema_version": 1,
        "sequence": 1,
        "event_type": "sprint_started",
        "sprint_id": "BB0",
        "actor": "ClaudeCode",
        "summary": "determinism test",
        "previous_event_hash": None,
    }
    h1 = _compute_event_hash(body)
    h2 = _compute_event_hash(body)
    assert h1 == h2, "Same body must always produce same hash"
    assert len(h1) == 64, "SHA-256 hex is 64 chars"


# ---------------------------------------------------------------------------
# 19. UTF-8 Turkish text survives round-trip
# ---------------------------------------------------------------------------


def test_turkish_text_survives_round_trip(tmp_path):
    log = tmp_path / "bb.jsonl"
    turkish = "Çalışma ağacı temiz, bugün kaldık, şüphe yok, İ doğru"
    append_event(log, _minimal({"summary": turkish}))

    raw = log.read_bytes()
    text = raw.decode("utf-8", errors="strict")

    event = json.loads(log.read_text(encoding="utf-8").strip())
    assert event["summary"] == turkish, (
        f"Turkish text must survive round-trip; got: {event['summary']!r}"
    )


# ---------------------------------------------------------------------------
# 20. Raw bytes decode strictly as UTF-8
# ---------------------------------------------------------------------------


def test_log_bytes_are_strict_utf8(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({"summary": "UTF-8 strict test"}))
    append_event(log, _minimal({"summary": "second event"}))

    raw = log.read_bytes()
    # Must not raise
    text = raw.decode("utf-8", errors="strict")
    assert text


# ---------------------------------------------------------------------------
# 21. No mojibake markers in output
# ---------------------------------------------------------------------------


def test_no_mojibake_in_output(tmp_path):
    log = tmp_path / "bb.jsonl"
    turkish_summary = (
        "Çalışma temiz — "
        "şüöçğı İ MARKER"
    )
    append_event(log, _minimal({"summary": turkish_summary}))

    text = log.read_text(encoding="utf-8")
    for marker in _MOJIBAKE_MARKERS:
        assert marker not in text, (
            f"Mojibake marker {marker!r} found in log output"
        )


# ---------------------------------------------------------------------------
# 22. commit_hash=null is valid (no self-referential requirement)
# ---------------------------------------------------------------------------


def test_null_commit_hash_is_valid(tmp_path):
    log = tmp_path / "bb.jsonl"
    result = append_event(log, _minimal({
        "event_type": "sprint_started",
        "commit_hash": None,
        "summary": "Sprint started; commit hash not yet known",
    }))

    assert result.ok, "commit_hash=None must not prevent append"
    assert result.appended

    event = json.loads(log.read_text(encoding="utf-8").strip())
    assert event["commit_hash"] is None


def test_human_gate_null_commit_is_valid(tmp_path):
    log = tmp_path / "bb.jsonl"
    result = append_event(log, {
        "event_type": "human_gate",
        "sprint_id": "BB0",
        "actor": "Ahmet",
        "summary": "Human gate: Ahmet approved BLACKBOX-0 scope",
        "commit_hash": None,
        "human_gate_required": True,
    })

    assert result.ok
    event = json.loads(log.read_text(encoding="utf-8").strip())
    assert event["commit_hash"] is None
    assert event["human_gate_required"] is True


# ---------------------------------------------------------------------------
# 23. Codex verdict event records PASS/CONCERN/BLOCKER
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["PASS", "CONCERN", "BLOCKER"])
def test_codex_verdict_event(tmp_path, status):
    log = tmp_path / f"codex_{status}.jsonl"
    result = append_event(log, {
        "event_type": "codex_verdict",
        "sprint_id": "BB0",
        "actor": "Codex",
        "summary": f"Codex returned {status} for BLACKBOX-0",
        "codex_status": status,
        "commit_hash": "abc123def456" + "0" * 52,
    })

    assert result.ok
    event = json.loads(log.read_text(encoding="utf-8").strip())
    assert event["codex_status"] == status
    assert event["event_type"] == "codex_verdict"


# ---------------------------------------------------------------------------
# 24. safety_flags records sprint constraints
# ---------------------------------------------------------------------------


def test_safety_flags_recorded(tmp_path):
    log = tmp_path / "bb.jsonl"
    flags = {
        "no_install": True,
        "no_real_mic": True,
        "no_telegram": True,
        "no_scheduler": True,
        "no_auto": True,
        "no_env": True,
    }
    append_event(log, _minimal({
        "safety_flags": flags,
        "summary": "sprint_started with all safety constraints",
    }))

    event = json.loads(log.read_text(encoding="utf-8").strip())
    assert event["safety_flags"] == flags


# ---------------------------------------------------------------------------
# 25. validate_log returns structured errors (not just False/bool)
# ---------------------------------------------------------------------------


def test_validate_log_returns_structured_errors(tmp_path):
    log = tmp_path / "bb.jsonl"
    log.write_bytes(b"TOTALLY_INVALID_JSON\n")

    result = validate_log(log)
    assert isinstance(result, ValidationResult)
    assert not result.ok
    assert isinstance(result.errors, list)
    assert len(result.errors) > 0
    # Must contain a message, not just True/False
    assert any(len(e) > 5 for e in result.errors)


def test_validate_log_nonexistent_returns_structured_error(tmp_path):
    log = tmp_path / "does_not_exist.jsonl"
    result = validate_log(log)

    assert isinstance(result, ValidationResult)
    assert not result.ok
    assert len(result.errors) > 0
    assert "does not exist" in result.errors[0].lower()


# ---------------------------------------------------------------------------
# Additional: anchor cross-checks
# ---------------------------------------------------------------------------


def test_anchor_record_has_required_fields(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal())

    anchor = create_anchor_record(log, git_head="deadbeef", sprint_id="BB0")

    assert anchor["anchor_type"] == "git_log_digest"
    assert len(anchor["log_digest_sha256"]) == 64
    assert anchor["last_sequence"] == 1
    assert anchor["git_head_when_anchor_created"] == "deadbeef"
    assert anchor["sprint_id"] == "BB0"


def test_verify_anchor_missing_log(tmp_path):
    anchor = {
        "log_digest_sha256": "a" * 64,
        "last_sequence": 1,
    }
    result = verify_anchor(tmp_path / "missing.jsonl", anchor)
    assert not result.match
    assert result.error is not None


def test_append_result_is_structured_dataclass(tmp_path):
    log = tmp_path / "bb.jsonl"
    result = append_event(log, _minimal())

    assert isinstance(result, AppendResult)
    assert result.ok
    assert isinstance(result.integrity_warnings, list)
    assert isinstance(result.redactions_applied, list)
    assert isinstance(result.event_hash, str)
    assert len(result.event_hash) == 64


def test_validate_single_event_ok(tmp_path):
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal())

    result = validate_log(log)
    assert result.ok
    assert result.event_count == 1
    assert result.last_sequence == 1
    assert result.last_event_hash is not None


# ---------------------------------------------------------------------------
# B2: validate_log must not crash on valid JSON non-object values
# ---------------------------------------------------------------------------


def test_validate_log_array_json_no_crash(tmp_path):
    """validate_log must return structured error, not crash, for [] on a line."""
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({"summary": "valid event first"}))
    with log.open("ab") as f:
        f.write(b"[]\n")

    result = validate_log(log)
    assert isinstance(result, ValidationResult)
    assert not result.ok
    assert any("not an object" in err.lower() or "array" in err.lower()
               or "list" in err.lower()
               for err in result.errors), (
        f"Expected non-object error; got: {result.errors}"
    )


def test_validate_log_string_json_no_crash(tmp_path):
    """validate_log must return structured error, not crash, for JSON string on a line."""
    log = tmp_path / "bb.jsonl"
    with log.open("ab") as f:
        f.write(b'"just a string"\n')

    result = validate_log(log)
    assert isinstance(result, ValidationResult)
    assert not result.ok
    assert any("not an object" in err.lower() or "str" in err.lower()
               for err in result.errors), (
        f"Expected non-object error; got: {result.errors}"
    )


# ---------------------------------------------------------------------------
# B3: append_event must still succeed after non-object JSON corruption
# ---------------------------------------------------------------------------


def test_append_after_array_json_corruption(tmp_path):
    """append_event must keep recording even when prior log has [] on a line."""
    log = tmp_path / "bb.jsonl"
    # Write a corrupt non-object line
    log.write_bytes(b"[]\n")

    result = append_event(log, _minimal({"summary": "event after [] corruption"}))

    assert result.ok, f"append_event must succeed after [] corruption; error={result.error}"
    assert result.appended
    assert len(result.integrity_warnings) > 0, (
        "Expected integrity_warnings about the non-object prior line"
    )

    # The file must now have two lines: the original [] and the new valid event
    lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2, f"Expected 2 lines; got {len(lines)}: {lines}"
    # Second line must be valid JSON object
    e = json.loads(lines[1])
    assert isinstance(e, dict)
    assert e["summary"] == "event after [] corruption"


# ---------------------------------------------------------------------------
# B4: corrupt final line without newline must not absorb appended event
# ---------------------------------------------------------------------------


def test_corrupt_final_line_no_newline_separator(tmp_path):
    """If log ends without newline, new event must land on its own line."""
    log = tmp_path / "bb.jsonl"
    # Write corrupt bytes without trailing newline
    log.write_bytes(b"{bad_json_no_newline")

    result = append_event(log, _minimal({"summary": "event after corrupt no-newline line"}))

    assert result.ok, f"Expected ok; error={result.error}"
    assert result.appended

    # Read raw bytes and split on newlines
    raw = log.read_bytes()
    lines = [l for l in raw.split(b"\n") if l.strip()]
    assert len(lines) == 2, f"Expected 2 lines; got {len(lines)}"

    # Second line must be valid JSON
    second_line = lines[1]
    e = json.loads(second_line.decode("utf-8"))
    assert isinstance(e, dict)
    assert e["summary"] == "event after corrupt no-newline line"


def test_valid_event_then_corrupt_no_newline_then_new_event(tmp_path):
    """append_event after a valid event + corrupt tail still produces separate lines."""
    log = tmp_path / "bb.jsonl"
    r1 = append_event(log, _minimal({"summary": "first valid"}))
    assert r1.ok

    # Manually append corrupt bytes without newline
    with log.open("ab") as f:
        f.write(b"{incomplete_corrupt")

    r2 = append_event(log, _minimal({"summary": "third event"}))
    assert r2.ok, f"Expected ok; error={r2.error}"

    raw = log.read_bytes()
    lines = [l for l in raw.split(b"\n") if l.strip()]
    # Must have: first event, corrupt fragment, third event — on separate lines
    assert len(lines) >= 2

    # Last line must be valid JSON
    last = json.loads(lines[-1].decode("utf-8"))
    assert last["summary"] == "third event"


# ---------------------------------------------------------------------------
# B5: Nested raw-blob evidence keys must be caught recursively
# ---------------------------------------------------------------------------


def test_nested_raw_diff_not_stored_verbatim(tmp_path):
    """Nested raw_diff inside details must be replaced, not stored verbatim."""
    log = tmp_path / "bb.jsonl"
    secret_diff = "diff --git a/secret.py\n+SECRET_CONTENT_NESTED"
    append_event(log, _minimal({
        "details": {"outer": {"raw_diff": secret_diff}},
    }))

    content = log.read_text(encoding="utf-8")
    assert secret_diff not in content, (
        "Nested raw_diff must not be stored verbatim"
    )
    assert "[REDACTED:raw_blob_not_allowed]" in content


def test_sanitize_forbidden_keys_is_recursive():
    """_sanitize_forbidden_keys catches keys at any depth."""
    data = {
        "top_level": "ok",
        "nested": {
            "also_ok": "value",
            "deep": {
                "full_stdout": "SECRET OUTPUT",
                "full_stderr": "SECRET ERRORS",
            },
        },
        "diff_text": "TOP LEVEL ALSO CAUGHT",
    }
    result, warnings = _sanitize_forbidden_keys(data)

    assert result["diff_text"] == "[REDACTED:raw_blob_not_allowed]"
    assert result["nested"]["deep"]["full_stdout"] == "[REDACTED:raw_blob_not_allowed]"
    assert result["nested"]["deep"]["full_stderr"] == "[REDACTED:raw_blob_not_allowed]"
    assert result["nested"]["also_ok"] == "value"
    assert result["top_level"] == "ok"
    assert len(warnings) == 3  # diff_text + full_stdout + full_stderr


# ---------------------------------------------------------------------------
# B6: Sensitive keys with dict/list values must be fully redacted
# ---------------------------------------------------------------------------


def test_nested_dict_under_sensitive_key_redacted(tmp_path):
    """A dict value under a sensitive key (token) must be fully redacted."""
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({
        "details": {
            "token": {"nested_key": "SHOULD_BE_REDACTED", "another": "ALSO_GONE"},
        },
    }))

    content = log.read_text(encoding="utf-8")
    assert "SHOULD_BE_REDACTED" not in content, "Nested value under 'token' key must be redacted"
    assert "ALSO_GONE" not in content
    assert "[REDACTED]" in content


def test_list_under_sensitive_key_redacted(tmp_path):
    """A list value under a sensitive key (secret) must be fully redacted."""
    log = tmp_path / "bb.jsonl"
    append_event(log, _minimal({
        "details": {
            "secret": ["SECRET_ITEM_1", "SECRET_ITEM_2"],
        },
    }))

    content = log.read_text(encoding="utf-8")
    assert "SECRET_ITEM_1" not in content
    assert "SECRET_ITEM_2" not in content
    assert "[REDACTED]" in content


def test_redact_dict_sensitive_key_before_recurse():
    """_redact_dict must redact sensitive key before recursing into nested dict."""
    d = {
        "safe_key": "safe_value",
        "api_key": {"nested": "REAL_SECRET_TOKEN_VALUE"},
    }
    result, notes = _redact_dict(d)

    assert result["safe_key"] == "safe_value"
    assert result["api_key"] == "[REDACTED]"
    assert "REAL_SECRET_TOKEN_VALUE" not in str(result)
    assert any("api_key" in n for n in notes)


# ---------------------------------------------------------------------------
# B1 (re-review): list-in-list and non-dict evidence sanitization
# ---------------------------------------------------------------------------


def test_list_in_list_raw_diff_sanitized(tmp_path):
    """evidence=[[{"raw_diff": "DEEP_LIST_DIFF_LEAK"}]] must not store the leak."""
    log = tmp_path / "bb.jsonl"
    leak = "DEEP_LIST_DIFF_LEAK"
    append_event(log, _minimal({
        "evidence": [[{"raw_diff": leak}]],
    }))

    content = log.read_text(encoding="utf-8")
    assert leak not in content, (
        "raw_diff nested inside list-in-list must be sanitized"
    )
    assert "[REDACTED:raw_blob_not_allowed]" in content


def test_non_dict_evidence_list_raw_diff_sanitized(tmp_path):
    """evidence=[{"raw_diff": "LEAK"}] (list at top level) must not store the leak."""
    log = tmp_path / "bb.jsonl"
    leak = "NON_DICT_EVIDENCE_LEAK"
    append_event(log, _minimal({
        "evidence": [{"raw_diff": leak}],
    }))

    content = log.read_text(encoding="utf-8")
    assert leak not in content, (
        "raw_diff inside non-dict (list) evidence must be sanitized"
    )
    assert "[REDACTED:raw_blob_not_allowed]" in content


def test_sanitize_value_list_in_list():
    """_sanitize_value must recurse into lists nested inside lists."""
    v = [["safe_item", {"raw_diff": "INNER_DIFF"}], {"diff_text": "ANOTHER"}]
    result, warnings = _sanitize_value(v, "evidence")

    # outer list[0] is a list
    inner = result[0]
    assert inner[0] == "safe_item"
    assert isinstance(inner[1], dict)
    assert inner[1]["raw_diff"] == "[REDACTED:raw_blob_not_allowed]"

    # outer list[1] is a dict
    assert result[1]["diff_text"] == "[REDACTED:raw_blob_not_allowed]"

    assert len(warnings) == 2


def test_sanitize_warns_for_non_dict_evidence(tmp_path):
    """integrity_warnings must be populated when non-dict evidence contains raw blobs."""
    log = tmp_path / "bb.jsonl"
    result = append_event(log, _minimal({
        "evidence": [{"raw_diff": "WARN_ME"}],
    }))

    assert result.ok
    assert any("raw_diff" in w.lower() or "forbidden" in w.lower()
               for w in result.integrity_warnings), (
        f"Expected sanitization warning; got: {result.integrity_warnings}"
    )


def test_safe_list_evidence_survives(tmp_path):
    """Safe structured list evidence must pass through sanitization unchanged."""
    log = tmp_path / "bb.jsonl"
    safe_evidence = [{"file": "tests/foo.py", "passed": 5}, "extra_string"]
    append_event(log, _minimal({
        "evidence": safe_evidence,
    }))

    content = log.read_text(encoding="utf-8")
    assert "tests/foo.py" in content, "Safe evidence must survive sanitization"
    assert "extra_string" in content
    assert "[REDACTED:raw_blob_not_allowed]" not in content


# ---------------------------------------------------------------------------
# B2 (re-review): validate_log must not crash on malformed field types
# ---------------------------------------------------------------------------


def _write_raw_event(path: "Path", event: dict) -> None:
    """Write a raw JSON event line (bypasses append_event validation)."""
    with path.open("ab") as f:
        f.write((json.dumps(event) + "\n").encode("utf-8"))


def test_validate_log_event_hash_integer_no_crash(tmp_path):
    """validate_log must return structured error when event_hash is an integer."""
    log = tmp_path / "bb.jsonl"
    bad = {
        "schema_version": 1,
        "ts_utc": "2026-01-01T00:00:00+00:00",
        "sequence": 1,
        "previous_event_hash": None,
        "event_hash": 123,
        "event_type": "sprint_started",
        "sprint_id": "BB0-test",
        "actor": "ClaudeCode",
        "summary": "bad event_hash type",
    }
    _write_raw_event(log, bad)

    result = validate_log(log)

    assert isinstance(result, ValidationResult), "Must return ValidationResult, not raise"
    assert not result.ok
    assert any("event_hash" in err for err in result.errors), (
        f"Expected event_hash type error; got: {result.errors}"
    )


def test_validate_log_previous_event_hash_integer_structured_error(tmp_path):
    """validate_log must return structured error when previous_event_hash is an integer."""
    log = tmp_path / "bb.jsonl"
    bad = {
        "schema_version": 1,
        "ts_utc": "2026-01-01T00:00:00+00:00",
        "sequence": 1,
        "previous_event_hash": 999,
        "event_hash": "a" * 64,
        "event_type": "sprint_started",
        "sprint_id": "BB0-test",
        "actor": "ClaudeCode",
        "summary": "bad previous_event_hash type",
    }
    _write_raw_event(log, bad)

    result = validate_log(log)

    assert isinstance(result, ValidationResult)
    assert not result.ok
    assert any("previous_event_hash" in err for err in result.errors), (
        f"Expected previous_event_hash type error; got: {result.errors}"
    )


def test_validate_log_sequence_string_structured_error(tmp_path):
    """validate_log must return structured error when sequence is a string."""
    log = tmp_path / "bb.jsonl"
    bad = {
        "schema_version": 1,
        "ts_utc": "2026-01-01T00:00:00+00:00",
        "sequence": "1",
        "previous_event_hash": None,
        "event_hash": "a" * 64,
        "event_type": "sprint_started",
        "sprint_id": "BB0-test",
        "actor": "ClaudeCode",
        "summary": "bad sequence type",
    }
    _write_raw_event(log, bad)

    result = validate_log(log)

    assert isinstance(result, ValidationResult)
    assert not result.ok
    assert any("sequence" in err for err in result.errors), (
        f"Expected sequence type error; got: {result.errors}"
    )


def test_append_after_malformed_event_hash_still_appends(tmp_path):
    """append_event must still succeed and warn when prior log has event_hash=123."""
    log = tmp_path / "bb.jsonl"
    bad = {
        "schema_version": 1,
        "ts_utc": "2026-01-01T00:00:00+00:00",
        "sequence": 1,
        "previous_event_hash": None,
        "event_hash": 123,
        "event_type": "sprint_started",
        "sprint_id": "BB0-test",
        "actor": "ClaudeCode",
        "summary": "bad event_hash type",
    }
    _write_raw_event(log, bad)

    result = append_event(log, _minimal({"summary": "after malformed hash event"}))

    assert result.ok, f"append_event must succeed; error={result.error}"
    assert result.appended
    assert len(result.integrity_warnings) > 0, (
        "Expected integrity_warnings about malformed event_hash in prior log"
    )

    # Verify the new valid event is present
    lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2
    last = json.loads(lines[-1])
    assert last["summary"] == "after malformed hash event"
