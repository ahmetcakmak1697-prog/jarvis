# BLACKBOX_RUNBOOK.md — BLACKBOX-0 Sprint Audit Log

> Sprint: BLACKBOX-0 | Date: 2026-07-05 | Status: FEATURE-FROZEN
> Module: agents/blackbox_log.py | Tests: tests/test_blackbox_log.py

---

## Feature-freeze closeout (2026-07-08)

- **Final fix commit:** `9bfb0f900` — fix(automation): finalize BLACKBOX-0 validator chain state
- **Codex final verdict:** PASS
- **Meaning:** The BLACKBOX-0 validator-state blocker (canonical-but-structurally-unusable
  event_hash values contaminating `_read_log_state`/`validate_log` chain state) is resolved.
  `_read_log_state` and `validate_log` now agree on structural chain usability.
- **Scope:** Offline validation/logging only. No behavior outside
  `agents/blackbox_log.py` and its tests was changed.
- **Explicitly restated (unchanged from BLACKBOX-0 inception):**
  - No autonomous execution enabled.
  - No scheduler enabled.
  - No Telegram enabled.
  - No mic/audio/J0B/Piper enabled.
  - No .env/secret behavior added.
- **Manual validation evidence:**
  - `py -3.11 -m pytest tests/test_blackbox_log.py -q --tb=short` -> 76 passed
  - `py -3.11 -m pytest tests/test_blackbox_log.py tests/test_j0_voice_adapters.py tests/test_j0_voice_loop.py -q --tb=short` -> 153 passed
  - `py -3.11 -m pytest tests/test_j0_spike_b_latency_probe.py tests/test_j0_live_status_unicode.py tests/test_j0_live_status.py tests/test_j0_voice_latency_probe.py -q --tb=short` -> 101 passed
  - `py -3.11 -m pytest tests/test_e1_s4_live_smoke_wiring.py tests/test_proactive_delivery.py tests/test_proactive_runtime.py -q --tb=short` -> 69 passed
  - `py -3.11 -m json.tool roadmap_state.json` -> valid JSON
  - `git diff --check` -> clean except benign CRLF/LF warnings
- **Next step after freeze:** LOOP-0A capability/machine-gate probe (not J0B directly).

---

## What BLACKBOX-0 Is

An offline, deterministic, human-gated append-only JSONL audit trail for
supervised JARVIS sprints. Every sprint start, human gate, file change, test
run, commit, Codex verdict, and risk note can be recorded as a structured
event with a cryptographic hash chain and external Git anchoring.

**Primary purpose:** Make sprint decisions traceable, tamper-detectable, and
auditable without requiring an external service, network, or database.

---

## What BLACKBOX-0 Is NOT

- **Not autonomous execution.** No code in blackbox_log.py schedules, loops,
  or makes decisions.
- **Not J0B.** BLACKBOX-0 does not start Piper/TTS, real-mic, or any audio.
- **Not a Telegram sender.** No network calls.
- **Not a scheduler.** No background loops or recurring jobs.
- **Not an .env reader.** The module never touches .env or any secrets file.
- **Not an auto-committer.** The module never calls git commit.
- **Not a legal/compliance-grade immutable ledger.** See Limitations below.

---

## How Append-Only JSONL Works

Each event is one line of compact canonical JSON (`sort_keys=True`,
`ensure_ascii=False`) followed by a newline. The file is opened in append-binary
mode (`"ab"`); old lines are never rewritten. A UTF-8 round-trip is guaranteed
for all content including Turkish characters.

Event schema (required fields):
```
schema_version   integer    always 1 in BLACKBOX-0
ts_utc           string     ISO 8601 UTC timestamp
sequence         integer    monotonically increasing from 1
previous_event_hash  string|null  event_hash of the preceding event, or null
event_hash       string     SHA-256 of canonical JSON of this event (excl. event_hash)
event_type       string     sprint_started | human_gate | files_changed |
                             tests_run | commit_created | codex_verdict |
                             sprint_completed | risk_noted | anchor_created
sprint_id        string     e.g. "BB0", "J0A"
actor            string     Ahmet | ClaudeCode | Codex | GPT
summary          string     one-line human-readable description
```

Optional fields:
```
task_id          string|null
details          object     structured facts (see Evidence Guardrails)
evidence         object     structured facts (see Evidence Guardrails)
safety_flags     object     no_install, no_real_mic, no_telegram, etc.
commit_hash      string|null  null when commit does not yet exist
codex_status     PASS|CONCERN|BLOCKER|null
human_gate_required  boolean
redactions_applied  list    populated automatically by append_event
integrity_warnings  list    populated automatically by append_event
```

---

## How the Internal Event Hash Chain Works

Each event's `event_hash` is the SHA-256 of the canonical JSON of that event
with the `event_hash` field itself excluded. This hash covers every other
field including `previous_event_hash`, which equals the `event_hash` of the
preceding event (or null for the first event).

Validation (`validate_log`) checks:
1. Each line is valid JSON.
2. All required fields are present.
3. Sequence numbers are consecutive (no gaps, no duplicates).
4. `previous_event_hash` equals the `event_hash` of the prior event.
5. Each `event_hash` matches the computed hash of that event's content.

---

## Why the Hash Chain Alone Is NOT Tamper-Proof

An actor who rewrites event N and recomputes all subsequent hashes can produce
a chain that looks internally valid. The chain proves *internal consistency*
of the current file, not that the file has not been rewritten.

**Real tamper evidence comes from external anchoring** (see next section).

Under this project's workflow:
- `git reset --hard`, `git rebase`, and `git push --force` are forbidden.
- `git reflog` can detect force-rewrites of local history.
- A stronger future option is signed commits or a remote append-only mirror.
  These are NOT in BLACKBOX-0 scope.

---

## How Git Anchoring Works

At important milestones (after a Codex PASS, before starting a new phase),
Claude or Ahmet may record a log digest into Git:

1. Compute the log digest:
   ```python
   from agents.blackbox_log import compute_log_digest
   digest = compute_log_digest("automation/BLACKBOX.jsonl")
   ```

2. Create an anchor record:
   ```python
   from agents.blackbox_log import create_anchor_record
   import subprocess
   head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
   anchor = create_anchor_record("automation/BLACKBOX.jsonl", git_head=head, sprint_id="BB0")
   ```

3. Save the anchor dict to a file (e.g., `automation/BLACKBOX_ANCHORS.jsonl`) and
   commit it with a scoped commit:
   ```
   docs(automation): anchor BLACKBOX-0 log digest at Codex PASS
   ```
   The commit hash of THIS commit becomes the external anchor.

4. The anchor file in Git history is the external tamper evidence. Anyone
   with Git access can verify: if the current log's digest matches the
   digest stored in a past commit, the log has not changed since that commit.

---

## How to Compute a Log Digest and Compare to an Anchor

```python
from agents.blackbox_log import compute_log_digest, verify_anchor
import json

# Current digest
current_digest = compute_log_digest("automation/BLACKBOX.jsonl")

# Load an old anchor from the anchors file
anchor = json.loads(open("automation/BLACKBOX_ANCHORS.jsonl").readlines()[0])

# Verify
result = verify_anchor("automation/BLACKBOX.jsonl", anchor)
print(result.match)   # True = log unchanged since anchor; False = log modified
```

---

## What Tampering This Detects

| Scenario | Detected |
|---|---|
| A new line appended after anchor | Yes — digest differs |
| An old line rewritten (content change) | Yes — digest differs |
| An old line deleted | Yes — digest differs |
| Sequence renumbered after rewrite | Yes — digest differs (file bytes differ) |
| All internal hashes recomputed after rewrite | Yes — file bytes still differ from anchor |

---

## What It Does NOT Guarantee

- Does not detect tampering that happened BEFORE an anchor was created.
- Does not protect against an actor who also rewrites the anchor commit in Git history.
- Does not provide non-repudiation (no digital signatures in BLACKBOX-0).
- Anchor file stored locally can be replaced — external mirror would be stronger.

---

## Why append_event Keeps Recording Despite Corrupt Prior Log

The black box should keep recording even when previous entries are damaged.
Stopping the recorder on corruption would make the log useless for post-mortem
analysis of what happened during and after the corruption event.

`append_event`:
- Reads existing log and populates `integrity_warnings` if it finds problems.
- Stores the warnings inside the new event (so the log self-documents the
  corruption it observed).
- Continues to write the new event.
- **Never rewrites old events.**

`validate_log` is the audit gate: run it to check full log integrity before
trusting the log for decision-making.

---

## Why validate_log Is Separate from append_event

`append_event` is the recorder — it should always record.
`validate_log` is the auditor — run it at checkpoints to assert clean state.

They are intentionally separate so that:
1. A corrupt log can still receive new events.
2. Validation errors do not prevent logging of the error itself.
3. Callers can validate as frequently or infrequently as needed.

---

## How Lock/Atomic Append Works and Its Limits

`append_event` acquires a lock file (`<log>.lock`) before reading the current
sequence number and writing the new event. The lock uses `os.open` with
`O_CREAT | O_EXCL`, which is atomic on POSIX filesystems and NTFS.

The read-then-write (determine next sequence → write line) is protected by
the lock, preventing two writers from generating the same sequence number.

**Limits:**
- Protects concurrent writers running on the same machine (threads or
  cooperating processes) that both use this module's lock protocol.
- Does not protect against a process that bypasses the lock and writes
  directly to the file.
- Lock timeout is 5 seconds; a deadlock (process crash while holding lock)
  requires manual deletion of the `.lock` file.
- On network file systems, `O_CREAT | O_EXCL` may not be atomic.

---

## Why Evidence/Details Must Be Structured, Not Raw Blobs

Raw diff/stdout/stderr blobs embedded in an audit log:
- May contain secrets (API keys, tokens, env vars) that bypass redaction.
- Bloat the log, making it impractical to validate and compare digests.
- Are not needed for audit purposes — file paths, counts, hashes, and
  command names are sufficient to reconstruct context.

`append_event` replaces any `raw_diff`, `diff_text`, `full_stdout`,
`full_stderr`, `secret_dump`, or `env_dump` keys in `details`/`evidence`
with `[REDACTED:raw_blob_not_allowed]` and records a warning.

Allowed content in details/evidence:
- file paths
- test counts and totals
- commit hashes
- exit codes
- command names (not outputs)
- Codex verdicts
- references to external log files

---

## How Redaction Works and Its Limits

Before writing, `append_event` scans all dict keys and string values:
- Keys matching sensitive fragments (`token`, `api_key`, `secret`, `password`,
  `bearer`, `webhook`, `telegram_bot_token`, etc.): string values are replaced
  with `[REDACTED]`.
- String values containing `Bearer XXXX` patterns: the token portion is
  replaced with `[REDACTED:bearer_token]`.

**Limits:**
- Redaction is a safety net, not a primary security control.
- It does not implement full DLP (data loss prevention).
- It does not scan binary data or base64-encoded content.
- The primary defense is: never pass secrets to `append_event` at all.

---

## Why commit_hash May Be Null at Event Creation

A commit does not exist before it is created. Recording a `sprint_started`
event for a sprint whose commits are still in progress requires
`commit_hash: null`. The hash may be recorded in a later `commit_created`
event once the commit exists.

This avoids the self-referential loop where a commit's event requires the
commit hash, but the hash only exists after the commit, which requires the
event to already contain the hash.

**Rule:** Never require a commit to contain its own final hash before the
commit exists. Record `commit_hash: null`; update in a later event if useful.

---

## How Future Sprints Should Record Events

### Sprint start
```python
from agents.blackbox_log import append_event
append_event("automation/BLACKBOX.jsonl", {
    "event_type": "sprint_started",
    "sprint_id": "J0B",
    "actor": "ClaudeCode",
    "summary": "SPRINT-J0B started: Piper subprocess + Edge TTS fallback",
    "commit_hash": None,  # not yet created
    "safety_flags": {
        "no_install": True, "no_real_mic": True, "no_telegram": True,
        "no_scheduler": True, "no_auto": True, "no_env": True,
    },
})
```

### Human gate
```python
append_event("automation/BLACKBOX.jsonl", {
    "event_type": "human_gate",
    "sprint_id": "J0B",
    "actor": "Ahmet",
    "summary": "Ahmet confirmed BLACKBOX-0 offline validation complete",
    "human_gate_required": True,
    "commit_hash": None,
})
```

### Files changed
```python
append_event("automation/BLACKBOX.jsonl", {
    "event_type": "files_changed",
    "sprint_id": "J0B",
    "actor": "ClaudeCode",
    "summary": "Created PiperSubprocessAdapter implementation",
    "details": {
        "files": ["scripts/j0_tts_adapters.py", "tests/test_j0_tts_adapters.py"],
        "change_type": "implementation",
    },
    "commit_hash": None,
})
```

### Test run
```python
append_event("automation/BLACKBOX.jsonl", {
    "event_type": "tests_run",
    "sprint_id": "J0B",
    "actor": "ClaudeCode",
    "summary": "pytest test_j0_tts_adapters.py: 45 passed, 0 failed",
    "evidence": {
        "test_file": "tests/test_j0_tts_adapters.py",
        "passed": 45,
        "failed": 0,
        "total": 45,
    },
    "commit_hash": None,
})
```

### Commit created
```python
append_event("automation/BLACKBOX.jsonl", {
    "event_type": "commit_created",
    "sprint_id": "J0B",
    "actor": "ClaudeCode",
    "summary": "feat(j0b): implement PiperSubprocessAdapter",
    "commit_hash": "abc123def456...",  # the actual hash
})
```

### Codex verdict
```python
append_event("automation/BLACKBOX.jsonl", {
    "event_type": "codex_verdict",
    "sprint_id": "J0B",
    "actor": "Codex",
    "summary": "Codex returned PASS for J0B",
    "codex_status": "PASS",
    "commit_hash": "abc123def456...",
})
```

### Sprint completed
```python
append_event("automation/BLACKBOX.jsonl", {
    "event_type": "sprint_completed",
    "sprint_id": "J0B",
    "actor": "ClaudeCode",
    "summary": "SPRINT-J0B complete. Codex PASS. Awaiting BLACKBOX-1 validation.",
    "commit_hash": "abc123def456...",
})
```

### Anchor created

**CRITICAL ORDER:** Append the `anchor_created` log event FIRST, then compute
the digest, then save the external anchor. Never compute the digest and then
append to the same log — doing so invalidates the anchor immediately because
the file bytes change after the digest is captured.

```python
from agents.blackbox_log import create_anchor_record, append_event
import json, subprocess

head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()

# Step 1: Append anchor_created event FIRST (before computing digest)
append_event("automation/BLACKBOX.jsonl", {
    "event_type": "anchor_created",
    "sprint_id": "J0B",
    "actor": "ClaudeCode",
    "summary": "Log digest anchored at Codex PASS commit",
    "details": {
        "git_head": head,
        "anchor_file": "automation/BLACKBOX_ANCHORS.jsonl",
    },
    "commit_hash": head,
})

# Step 2: NOW compute digest (log is final — no more appends after this)
anchor = create_anchor_record("automation/BLACKBOX.jsonl", git_head=head, sprint_id="J0B")

# Step 3: Save anchor to EXTERNAL file only (never back into BLACKBOX.jsonl)
with open("automation/BLACKBOX_ANCHORS.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(anchor, sort_keys=True, ensure_ascii=False) + "\n")

# Step 4: Commit both files
# git add automation/BLACKBOX_ANCHORS.jsonl automation/BLACKBOX.jsonl
# git commit -m "docs(automation): anchor J0B log digest at Codex PASS"
```

**Why this order matters:** `create_anchor_record` computes SHA-256 over the
raw file bytes at the moment it is called. Any subsequent write to that file
(including appending the `anchor_created` event itself) changes the file bytes
and immediately invalidates the anchor. The anchor must be computed AFTER the
log is finished, and saved ONLY to an external file — never appended back into
the log it anchors.

---

## Safety Statement

BLACKBOX-0 does not enable autonomous execution.
BLACKBOX-0 does not start J0B, Piper/TTS, or real-mic.
BLACKBOX-0 does not send Telegram.
BLACKBOX-0 does not run a scheduler.
BLACKBOX-0 does not read .env.
BLACKBOX-0 does not auto-commit anchors.
BLACKBOX-0 is offline validation/logging only.

---

*Prepared by: Claude Code | Date: 2026-07-05 | Sprint: BLACKBOX-0*
