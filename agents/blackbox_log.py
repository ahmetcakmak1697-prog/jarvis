"""
agents/blackbox_log.py — BLACKBOX-0 append-only sprint audit log foundation.

Provides an offline, deterministic, testable audit trail for supervised JARVIS
sprints. Human-gated; never autonomous.

Public API:
  append_event(path, event)  -> AppendResult
  validate_log(path)         -> ValidationResult
  compute_log_digest(path)   -> str
  create_anchor_record(...)  -> dict
  verify_anchor(...)         -> AnchorVerifyResult

Design notes:
  - Append-only JSONL: one event per line, UTF-8, canonical JSON (sort_keys).
  - Internal hash chain: event_hash + previous_event_hash for cheap consistency.
  - External anchoring: Git-committed log digest for tamper evidence.
  - Atomic append via lock file (cross-platform, no third-party deps).
  - append_event keeps recording even if prior log is corrupt (returns warnings).
  - validate_log is the audit gate; append_event is the recorder.
  - Structured evidence guardrails: no raw diff/stdout/stderr blobs.
  - Basic secret redaction before write (safety net, not full DLP).

Limitations (documented honestly):
  - Hash chain alone is NOT tamper-proof. An actor who rewrites events and
    recomputes all subsequent hashes can produce a valid-looking chain.
  - Real tamper evidence requires comparing the current log digest against a
    previously Git-anchored digest stored in a separate commit.
  - Local Git history can be rewritten by an actor with repository control;
    under this project's workflow, reset/rebase/clean are forbidden and
    reflog checks help detect such actions.
  - Lock file protects concurrent writers cooperating on the same machine.
    It does not protect against OS-level file replacement.
  - Redaction is a safety net, not a primary security control.
  - This module NEVER auto-commits to Git. Anchoring is a manual step.

BLACKBOX-0 does NOT:
  - Enable autonomous execution.
  - Start J0B, Piper/TTS, or real-mic.
  - Send Telegram.
  - Run scheduler or background loops.
  - Read .env or any secrets file.
  - Auto-commit Git.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION: int = 1

REQUIRED_FIELDS = frozenset({
    "schema_version", "ts_utc", "sequence", "previous_event_hash",
    "event_hash", "event_type", "sprint_id", "actor", "summary",
})

VALID_EVENT_TYPES = frozenset({
    "sprint_started", "human_gate", "files_changed", "tests_run",
    "commit_created", "codex_verdict", "sprint_completed", "risk_noted",
    "anchor_created",
})

VALID_CODEX_STATUSES = frozenset({"PASS", "CONCERN", "BLOCKER"})

# Evidence keys indicating raw blobs — forbidden in details/evidence sub-dicts.
_FORBIDDEN_EVIDENCE_KEYS = frozenset({
    "raw_diff", "diff_text", "full_stdout", "full_stderr",
    "secret_dump", "env_dump",
})

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AppendResult:
    ok: bool
    appended: bool
    sequence: int
    event_hash: str
    previous_event_hash: Optional[str]
    integrity_warnings: List[str] = field(default_factory=list)
    redactions_applied: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ValidationResult:
    ok: bool
    event_count: int
    last_sequence: int
    last_event_hash: Optional[str]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class AnchorVerifyResult:
    ok: bool
    log_path: str
    anchor_digest: str
    current_digest: str
    match: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Redaction (safety net — not full DLP)
# ---------------------------------------------------------------------------

_SENSITIVE_KEY_FRAGMENTS = frozenset({
    "telegram_bot_token", "api_key", "openai_api_key", "anthropic_api_key",
    "gemini_api_key", "deepseek_api_key", "token", "secret", "password",
    "bearer", "webhook",
})

_BEARER_RE = re.compile(r'Bearer\s+\S{8,}', re.IGNORECASE)


def _redact_string_value(value: str) -> tuple[str, bool]:
    """Redact Bearer tokens from a string. Returns (result, was_changed)."""
    result = _BEARER_RE.sub("[REDACTED:bearer_token]", value)
    return result, result != value


def _redact_dict(d: dict, _path: str = "") -> tuple[dict, list[str]]:
    """Recursively redact a dict. Returns (redacted_copy, notes).

    Key-sensitivity check happens FIRST, before any recursion, so sensitive
    keys with dict/list values are redacted as a whole (not traversed).
    This prevents nested tokens under sensitive keys from surviving.
    """
    result: dict = {}
    all_notes: list[str] = []

    for k, v in d.items():
        full_key = f"{_path}.{k}" if _path else k
        key_lower = k.lower()

        # B6: check key sensitivity before type-based recursion
        if any(frag in key_lower for frag in _SENSITIVE_KEY_FRAGMENTS) and v:
            all_notes.append(f"key '{full_key}' matches sensitive-key pattern")
            result[k] = "[REDACTED]"
            continue

        if isinstance(v, dict):
            rv, notes = _redact_dict(v, full_key)
            result[k] = rv
            all_notes.extend(notes)
        elif isinstance(v, list):
            rv_list = []
            for item in v:
                if isinstance(item, dict):
                    ri, notes = _redact_dict(item, full_key)
                    rv_list.append(ri)
                    all_notes.extend(notes)
                elif isinstance(item, str):
                    ri_s, changed = _redact_string_value(item)
                    rv_list.append(ri_s)
                    if changed:
                        all_notes.append(f"list item under '{full_key}' contained bearer token")
                else:
                    rv_list.append(item)
            result[k] = rv_list
        elif isinstance(v, str):
            redacted, changed = _redact_string_value(v)
            if changed:
                all_notes.append(f"value of '{full_key}' contained bearer-like token")
            result[k] = redacted
        else:
            result[k] = v

    return result, all_notes


# ---------------------------------------------------------------------------
# Structured evidence guardrails
# ---------------------------------------------------------------------------


def _sanitize_value(v: Any, path: str = "") -> tuple[Any, list[str]]:
    """Recursively sanitize any value for forbidden raw-blob keys.

    - dict: scans keys via _sanitize_forbidden_keys
    - list: recurses into every item (handles list-in-list)
    - scalar: passed through unchanged
    """
    if isinstance(v, dict):
        return _sanitize_forbidden_keys(v, path)
    if isinstance(v, list):
        warnings: list[str] = []
        new_list: list = []
        for i, item in enumerate(v):
            ri, w = _sanitize_value(item, f"{path}[{i}]")
            new_list.append(ri)
            warnings.extend(w)
        return new_list, warnings
    return v, []


def _sanitize_forbidden_keys(d: dict, _path: str = "") -> tuple[dict, list[str]]:
    """Recursively replace forbidden raw-blob keys at any nesting depth."""
    result: dict = {}
    warnings: list[str] = []
    for k, v in d.items():
        full_key = f"{_path}.{k}" if _path else k
        if k.lower() in _FORBIDDEN_EVIDENCE_KEYS:
            warnings.append(
                f"Forbidden raw-blob key '{full_key}' replaced. "
                "Store file paths, counts, hashes, or verdicts instead."
            )
            result[k] = "[REDACTED:raw_blob_not_allowed]"
        else:
            new_v, w = _sanitize_value(v, full_key)
            result[k] = new_v
            warnings.extend(w)
    return result, warnings


def _sanitize_evidence(event: dict) -> tuple[dict, list[str]]:
    """Replace forbidden raw-blob keys in details/evidence at any depth.

    Raw diff/stdout/stderr/secret blobs must not be embedded in the log.
    Store file paths, counts, hashes, verdicts, or references instead.
    Both dict and non-dict top-level values (list, scalar) are sanitized.
    Returns (modified_event_copy, warning_list).
    """
    warnings: list[str] = []
    new_event = dict(event)
    for top_key in ("details", "evidence"):
        sub = new_event.get(top_key)
        if sub is None:
            continue
        new_sub, w = _sanitize_value(sub, top_key)
        warnings.extend(w)
        new_event[top_key] = new_sub
    return new_event, warnings


# ---------------------------------------------------------------------------
# Canonicalization and hashing
# ---------------------------------------------------------------------------


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _compute_event_hash(event: dict) -> str:
    """SHA-256 over canonical JSON of event, excluding the 'event_hash' field."""
    body = {k: v for k, v in event.items() if k != "event_hash"}
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Lock file (cross-platform, no third-party deps)
# ---------------------------------------------------------------------------


def _acquire_lock(lock_path: Path, timeout: float = 5.0) -> int:
    """Acquire a lock file using O_CREAT | O_EXCL (atomic on POSIX and NTFS).
    Returns the file descriptor. Raises TimeoutError on timeout.

    On Windows, PermissionError may be raised instead of FileExistsError when
    another thread is in the process of creating or releasing the lock file
    (e.g., between os.close and unlink). Both are treated as transient
    lock-contention and retried within the timeout.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            return fd
        except (FileExistsError, PermissionError):
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Could not acquire lock {lock_path} within {timeout}s"
                )
            time.sleep(0.01)


def _release_lock(lock_path: Path, fd: int) -> None:
    try:
        os.close(fd)
    except Exception:
        pass
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Internal: read log state (used inside the lock)
# ---------------------------------------------------------------------------


def _read_log_state(path: Path) -> tuple[int, Optional[str], list[str]]:
    """Return (last_sequence, last_event_hash, integrity_warnings).

    Does not raise on corrupt lines; returns warnings instead so append_event
    can continue recording even when prior log is damaged.
    """
    if not path.exists():
        return 0, None, []

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        return 0, None, [f"Could not read log: {e}"]

    warnings: list[str] = []
    last_sequence = 0
    last_hash: Optional[str] = None
    prev_hash: Optional[str] = None
    expected_seq = 1

    for lineno, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as e:
            warnings.append(f"Line {lineno}: invalid JSON: {e}")
            continue

        if not isinstance(event, dict):
            warnings.append(
                f"Line {lineno}: JSON value is not an object (got {type(event).__name__})"
            )
            continue

        seq = event.get("sequence")
        evt_hash = event.get("event_hash")
        prev = event.get("previous_event_hash")

        # A canonical event_hash is necessary but not sufficient to become
        # chain state: the line itself must also be structurally usable for
        # the chain (all required fields present, correct sequence, correct
        # previous_event_hash link). line_chain_usable tracks that; a
        # canonical hash on a structurally broken line must still be
        # reported as broken, but must never be trusted as the next
        # expected previous hash. This must mirror validate_log's notion of
        # structural usability exactly, or append_event and validate_log
        # disagree on chain state and validate_log ends up falsely blaming
        # a clean event that append_event legitimately chained to None.
        line_chain_usable = True

        missing = REQUIRED_FIELDS - set(event.keys())
        if missing:
            warnings.append(
                f"Line {lineno}: missing required fields: {sorted(missing)}"
            )
            line_chain_usable = False

        if not isinstance(seq, int):
            warnings.append(f"Line {lineno}: sequence not an integer: {seq!r}")
            line_chain_usable = False
        elif seq != expected_seq:
            warnings.append(
                f"Line {lineno}: sequence {seq} (expected {expected_seq})"
            )
            line_chain_usable = False

        if prev != prev_hash:
            warnings.append(
                f"Line {lineno}: previous_event_hash mismatch "
                f"(expected {prev_hash!r}, got {prev!r})"
            )
            line_chain_usable = False

        # A usable event_hash must be a non-empty string. Any other value
        # (missing, None, 0, False, [], {}, "", int, ...) is malformed and
        # must never be propagated as a future event's previous_event_hash —
        # doing so would write a structurally invalid new event. Falsey
        # malformed values (0, False, [], {}, "") must warn just like any
        # other malformed value, so this check no longer short-circuits on
        # truthiness.
        usable_hash: Optional[str] = None
        if "event_hash" not in event or evt_hash is None:
            warnings.append(f"Line {lineno}: missing 'event_hash'")
        elif not isinstance(evt_hash, str) or evt_hash == "":
            warnings.append(
                f"Line {lineno}: 'event_hash' must be a non-empty string "
                f"(got {type(evt_hash).__name__}: {evt_hash!r}); "
                "not usable as a previous_event_hash for future events"
            )
        else:
            computed = _compute_event_hash(event)
            if computed != evt_hash:
                warnings.append(
                    f"Line {lineno}: event_hash mismatch "
                    f"(stored={evt_hash[:12]}..., computed={computed[:12]}...); "
                    "not usable as a previous_event_hash for future events"
                )
            elif line_chain_usable:
                usable_hash = evt_hash
            else:
                warnings.append(
                    f"Line {lineno}: event_hash is canonical but the line is "
                    "structurally unusable for the chain; "
                    "not usable as a previous_event_hash for future events"
                )

        last_sequence = seq if isinstance(seq, int) else last_sequence
        last_hash = usable_hash
        prev_hash = usable_hash
        expected_seq = (last_sequence or 0) + 1

    return last_sequence, last_hash, warnings


# ---------------------------------------------------------------------------
# Public API: append_event
# ---------------------------------------------------------------------------


def append_event(path: "Path | str", event: dict) -> AppendResult:
    """Append one event to the JSONL audit log at path.

    Acquires a lock file before reading current state and writing. Redacts
    secrets and sanitizes raw-blob evidence keys. Writes one atomic UTF-8
    JSONL line. Continues recording even if the existing log is corrupt
    (returns integrity_warnings). Never rewrites old events.

    commit_hash may be None when the commit does not yet exist at event
    creation time. Callers may record the hash in a later event.

    Returns AppendResult with ok=True on success, or ok=False with error
    on write failure or lock timeout.
    """
    path = Path(path)
    lock_path = path.with_suffix(path.suffix + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)

    integrity_warnings: list[str] = []
    redactions: list[str] = []

    try:
        fd = _acquire_lock(lock_path, timeout=5.0)
    except TimeoutError as e:
        return AppendResult(
            ok=False, appended=False, sequence=0, event_hash="",
            previous_event_hash=None, error=str(e),
        )

    try:
        last_seq, last_hash, iw = _read_log_state(path)
        integrity_warnings.extend(iw)

        next_seq = last_seq + 1
        prev_hash = last_hash

        # Sanitize raw-blob evidence keys
        event, ev_warnings = _sanitize_evidence(event)
        integrity_warnings.extend(ev_warnings)

        # Build canonical body (without event_hash yet)
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "sequence": next_seq,
            "previous_event_hash": prev_hash,
            "event_type": event.get("event_type", ""),
            "sprint_id": event.get("sprint_id", ""),
            "task_id": event.get("task_id"),
            "actor": event.get("actor", ""),
            "summary": event.get("summary", ""),
            "details": event.get("details") or {},
            "evidence": event.get("evidence") or {},
            "safety_flags": event.get("safety_flags") or {},
            "commit_hash": event.get("commit_hash"),
            "codex_status": event.get("codex_status"),
            "human_gate_required": bool(event.get("human_gate_required", False)),
            "redactions_applied": [],
            "integrity_warnings": [],
        }

        # Redact secrets
        body, rn = _redact_dict(body)
        redactions.extend(rn)

        # Finalise warnings/redactions in body, then hash
        body["redactions_applied"] = redactions
        body["integrity_warnings"] = integrity_warnings

        event_hash = _compute_event_hash(body)
        body["event_hash"] = event_hash

        line_bytes = (_canonical_json(body) + "\n").encode("utf-8")

        # B4: if existing file does not end with '\n', write delimiter first so
        # the new event does not get glued onto a corrupt final line.
        prefix = b""
        if path.exists() and path.stat().st_size > 0:
            with path.open("rb") as f:
                f.seek(-1, 2)
                if f.read(1) != b"\n":
                    prefix = b"\n"

        with path.open("ab") as f:
            f.write(prefix + line_bytes)

        return AppendResult(
            ok=True,
            appended=True,
            sequence=next_seq,
            event_hash=event_hash,
            previous_event_hash=prev_hash,
            integrity_warnings=integrity_warnings,
            redactions_applied=redactions,
        )

    except Exception as e:
        return AppendResult(
            ok=False, appended=False, sequence=0, event_hash="",
            previous_event_hash=None, error=str(e),
            integrity_warnings=integrity_warnings,
        )

    finally:
        _release_lock(lock_path, fd)


# ---------------------------------------------------------------------------
# Public API: validate_log
# ---------------------------------------------------------------------------


def validate_log(path: "Path | str") -> ValidationResult:
    """Validate every event in the log. Returns structured result with errors.

    Checks:
      - Valid JSON per line
      - Required fields present
      - Sequence order (no gaps, no duplicates)
      - previous_event_hash chain
      - event_hash correctness

    Does not raise on invalid log; reports errors in the result.
    """
    path = Path(path)

    if not path.exists():
        return ValidationResult(
            ok=False, event_count=0, last_sequence=0, last_event_hash=None,
            errors=["Log file does not exist."],
        )

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        return ValidationResult(
            ok=False, event_count=0, last_sequence=0, last_event_hash=None,
            errors=[f"Could not read log: {e}"],
        )

    errors: list[str] = []
    warnings: list[str] = []
    event_count = 0
    last_sequence = 0
    last_hash: Optional[str] = None
    prev_hash: Optional[str] = None
    expected_seq = 1
    seen_seqs: set[int] = set()

    for lineno, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            warnings.append(f"Line {lineno}: blank line (skipped)")
            continue

        try:
            event = json.loads(stripped)
        except json.JSONDecodeError as e:
            errors.append(f"Line {lineno}: invalid JSON: {e}")
            continue

        if not isinstance(event, dict):
            errors.append(
                f"Line {lineno}: JSON value is not an object (got {type(event).__name__})"
            )
            continue

        event_count += 1

        # A canonical event_hash is necessary but not sufficient to become
        # chain state: the line itself must also be structurally usable for
        # the chain (all required fields present, correct/non-duplicate
        # sequence, correct previous_event_hash link). line_chain_usable
        # tracks that; a canonical hash on a structurally broken line must
        # still be reported as broken, but must never be trusted as the
        # next expected previous hash.
        line_chain_usable = True

        missing = REQUIRED_FIELDS - set(event.keys())
        if missing:
            errors.append(
                f"Line {lineno}: missing required fields: {sorted(missing)}"
            )
            line_chain_usable = False

        seq = event.get("sequence")
        evt_hash = event.get("event_hash")
        prev = event.get("previous_event_hash")

        if not isinstance(seq, int):
            errors.append(f"Line {lineno}: 'sequence' not an integer: {seq!r}")
            line_chain_usable = False
        else:
            if seq in seen_seqs:
                errors.append(f"Line {lineno}: duplicate sequence {seq}")
                line_chain_usable = False
            seen_seqs.add(seq)
            if seq != expected_seq:
                errors.append(
                    f"Line {lineno}: out-of-order sequence {seq} (expected {expected_seq})"
                )
                line_chain_usable = False

        if prev is not None and not isinstance(prev, str):
            errors.append(
                f"Line {lineno}: 'previous_event_hash' must be a string or null "
                f"(got {type(prev).__name__}: {prev!r})"
            )
            line_chain_usable = False
        elif prev != prev_hash:
            errors.append(
                f"Line {lineno}: previous_event_hash mismatch "
                f"(expected {prev_hash!r}, got {prev!r})"
            )
            line_chain_usable = False

        # A raw stored event_hash must never become validator chain state by
        # itself. Only a hash that is a non-empty string AND matches the
        # computed canonical hash for this event AND belongs to a
        # structurally usable line is "usable" and may become the expected
        # previous hash for the next event. Any other case (missing, wrong
        # type, empty, wrong non-empty string, or canonical-but-structurally
        # -broken) is reported here as an error on THIS line, and chain
        # state resets to None so the next line is judged on its own merits
        # instead of being falsely blamed for a mismatch against a
        # malformed/wrong/untrustworthy value.
        usable_hash: Optional[str] = None
        if not isinstance(evt_hash, str) or not evt_hash:
            errors.append(
                f"Line {lineno}: 'event_hash' must be a non-empty string "
                f"(got {type(evt_hash).__name__}: {evt_hash!r})"
            )
        else:
            computed = _compute_event_hash(event)
            if computed != evt_hash:
                errors.append(
                    f"Line {lineno}: event_hash mismatch "
                    f"(stored={evt_hash[:12]}..., computed={computed[:12]}...)"
                )
            elif line_chain_usable:
                usable_hash = evt_hash
            else:
                errors.append(
                    f"Line {lineno}: event_hash is canonical but the line is "
                    "structurally unusable for the chain; "
                    "not usable as a previous_event_hash for future events"
                )

        last_sequence = seq if isinstance(seq, int) else last_sequence
        last_hash = usable_hash
        prev_hash = usable_hash
        expected_seq = (last_sequence or 0) + 1

    return ValidationResult(
        ok=len(errors) == 0,
        event_count=event_count,
        last_sequence=last_sequence,
        last_event_hash=last_hash,
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Public API: anchor
# ---------------------------------------------------------------------------


def compute_log_digest(path: "Path | str") -> str:
    """SHA-256 over raw UTF-8 bytes of the log file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Log not found: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_anchor_record(
    log_path: "Path | str",
    git_head: Optional[str] = None,
    sprint_id: Optional[str] = None,
    notes: str = "",
) -> dict:
    """Return a structured anchor record dict. Does NOT commit to Git.

    Caller saves this to a file and commits it as a normal scoped Git commit.
    The commit hash becomes the external tamper-evidence anchor.
    This module never auto-commits.
    """
    log_path = Path(log_path)
    digest = compute_log_digest(log_path)
    last_seq, last_hash, _ = _read_log_state(log_path)

    return {
        "schema_version": SCHEMA_VERSION,
        "anchor_type": "git_log_digest",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "sprint_id": sprint_id,
        "log_path": str(log_path),
        "log_digest_sha256": digest,
        "last_event_hash": last_hash,
        "last_sequence": last_seq,
        "git_head_when_anchor_created": git_head,
        "notes": notes,
    }


def verify_anchor(
    log_path: "Path | str", anchor_record: dict
) -> AnchorVerifyResult:
    """Compare current log digest against the digest in anchor_record.

    match=True: log bytes have not changed since the anchor was created.
    match=False: log bytes differ — either legitimate new appends or tampering.

    A new legitimate append also produces match=False, so mismatch alone does
    not prove malicious tampering. Use validate_log + sequence/hash chain for
    detail. To distinguish new legitimate appends from rewrites, compare the
    last_event_hash in the anchor against the current log's chain.
    """
    log_path = Path(log_path)
    anchor_digest = anchor_record.get("log_digest_sha256", "")

    try:
        current_digest = compute_log_digest(log_path)
    except FileNotFoundError as e:
        return AnchorVerifyResult(
            ok=False, log_path=str(log_path),
            anchor_digest=anchor_digest, current_digest="",
            match=False, error=str(e),
        )

    return AnchorVerifyResult(
        ok=True,
        log_path=str(log_path),
        anchor_digest=anchor_digest,
        current_digest=current_digest,
        match=(current_digest == anchor_digest),
    )
