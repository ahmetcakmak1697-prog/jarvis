# CODEX_REVIEW_REQUEST.md — Review Request

---

## E1-S6A CLOSED — PASS (2026-06-27)
## E1-S6B CLOSED — PASS (2026-06-27)
## E1-S6C CLOSED — PASS (2026-06-28)
## E1-S6D CLOSED — PASS (2026-06-28)
## E1-S6E CLOSED — PASS (2026-06-28)

Commits reviewed and closed:
- E1-S6A: c8eee9a84, cc0072ac5
- E1-S6B: 648b74455, a53001577
- E1-S6C: 4f6a5b6e0, 3de2e1035
- E1-S6D: b4670036b
- E1-S6E: c9c7d75b3, 399587609

---

## E1-S4 CLOSED — PASS + HUMAN CONFIRMED (2026-06-28)

Commits:
- 0739333da  feat(proactive): prepare E1-S4 Telegram smoke wiring
- a39db4568  fix(proactive): sanitize E1-S4 smoke errors  (Codex PASS)

Live execution: Ahmet ran `py -3.11 -m agents.proactive_runner --e1-s4-smoke`
Result: sent=true, ts=2026-06-27T22:51:38.969829+00:00
Phone receipt confirmed. One message sent. Token/chat_id not exposed.

---

## SPRINT-J0A — OPEN (2026-07-04)

**Commit 1:** 591ded854  feat(j0): add default-off realtime voice adapter skeleton
**Commit 2:** c619b2619  docs(j0): sprint audit, harvest map, backlog, adapter plan, third-party notes
**Commit 3:** c3d3ade28  docs(j0): add commit hashes to Codex review request
**Blocker-fix commit 1:** 76206e92e  fix(j0): address J0A Codex blockers
**Blocker-fix commit 2:** 93c3bc698  docs(j0): record blocker-fix commit hash in review request
**Blocker-fix commit 3:** 6ccb1d943  fix(j0): close remaining J0A review blockers

### Files Changed

**Commit 1 (code):**
- scripts/j0_voice_adapters.py
- scripts/j0_tts_adapters.py
- scripts/j0_voice_loop.py
- requirements-voice.txt
- tests/test_j0_voice_adapters.py
- tests/test_j0_voice_loop.py

**Commit 2 (docs):**
- docs/JARVIS_REPO_AUDIT.md
- docs/JARVIS_HARVEST_MAP.md
- docs/JARVIS_BACKLOG.md
- docs/j0_realtime_adapter_plan.md
- docs/THIRD_PARTY_VOICE.md
- automation/SESSION_SUMMARY.md
- automation/AUTONOMY_LOG.md
- automation/CODEX_REVIEW_REQUEST.md (this file)

### Test Counts

```
tests/test_j0_voice_adapters.py  -> 36 passed  (+1 from blocker-fix round 1: 2 real is_available tests, -1 tautological)
tests/test_j0_voice_loop.py      -> 41 passed  (+6 from blocker-fix round 1: 2 missing-dep, 4 Turkish raw-bytes)

J0A focused total (new): 77 passed

Existing J0 suites (no regression):
  test_j0_spike_b_latency_probe + test_j0_live_status_unicode + test_j0_live_status + test_j0_voice_latency_probe  -> 101 passed

Combined J0: 178 passed

Proactive suites:
  test_e1_s4_live_smoke_wiring + test_proactive_delivery + test_proactive_runtime  -> 69 passed

Unique total: 247 passed, 0 failed
```

### Evidence Pointers

- Default-off: `JARVIS_J0_REALTIME_ENABLED=0` → CLI prints `{"status": "disabled", ...}` + exit 0
- Import safety: sys.modules does not contain RealtimeSTT/sounddevice/pyaudio after import
- UTF-8 raw bytes: subprocess stdout decoded strict UTF-8, no UnicodeDecodeError
- No mojibake: markers Ã/Ä/Å/� absent from CLI output
- Route behavior: FakeSTTAdapter + injected status_provider → response contains live marker (not canned text)
- Live wiring: different injected in_progress content → different response
- TTS contract: FakeTTSAdapter.spoken grows by 1; first_audio_hint_ms=None, warning populated
- PiperSubprocessAdapter: NotImplementedError("J0B") always raised; no subprocess spawned
- build_piper_cmd: pure function tested with expected argv
- Static safety: no telegram/scheduler/requests/sendMessage imports (AST-checked)
- roadmap_state.json: unchanged (py -3.11 -m json.tool roadmap_state.json → VALID; git diff roadmap_state.json → empty)

### Explicit Claims for Codex to Verify

1. **DEFAULT-OFF**: importing or running j0_voice_loop.py with JARVIS_J0_REALTIME_ENABLED=0 produces exit 0 with {"status": "disabled"} JSON; never opens audio device.
2. **IMPORT SAFETY**: importing j0_voice_adapters, j0_tts_adapters, j0_voice_loop does NOT cause RealtimeSTT, sounddevice, or pyaudio to appear in sys.modules.
3. **UTF-8 RAW BYTES**: CLI stdout decodes via `bytes.decode("utf-8", errors="strict")` without error.
4. **NO LIVE PATHS**: no test triggers a real microphone, real RealtimeSTT, real subprocess, or network call.
5. **SCOPED DIFF**: no files outside the allowed write paths were modified; roadmap_state.json is unchanged.
6. **NO ROADMAP CHANGE**: roadmap_state.json diff is empty.
7. **DOCS TRUTHFULNESS**: audit counts (101+69=170 pre-existing tests; 77 new J0A = 247 total), harvest decisions, backlog sequencing accurately reflect repo state. BLACKBOX-0 is in sequencing everywhere.
8. **PIPER STUB**: PiperSubprocessAdapter.speak() raises NotImplementedError("J0B") in every code path; no subprocess.run or subprocess.Popen call exists in j0_tts_adapters.py.
9. **HONESTY**: TTSResult.first_audio_hint_ms is None (not 0, not fabricated) in FakeTTSAdapter; TTSResult(first_audio_hint_ms=0) raises ValueError.
10. **NO TELEGRAM / NO SCHEDULER / NO AUTO**: j0_voice_adapters.py, j0_tts_adapters.py, j0_voice_loop.py contain no telegram/scheduler/requests/sendMessage imports or references (AST-verifiable).

### Known Style Deviation (not a blocker)

- Turkish string literals in _ROUTE_PHRASES and _FOLD_TABLE in j0_voice_loop.py use literal UTF-8 chars
  (e.g., "nerede kaldık") rather than `\uXXXX` escapes (project rule: survives CP1254 paste).
- The Write tool writes UTF-8 directly; at runtime these chars are identical to the escaped forms.
- The inline comment in j0_voice_loop.py (formerly false "uses \uXXXX") has been corrected in
  blocker-fix commit 3 to honestly say "UTF-8 source bytes (Python 3 default). See module docstring."
- The module docstring was already correct from blocker-fix commit 1 (76206e92e).
- All tests pass. Functionally correct. Comment is now truthful.

### Review Verdict Expected
PASS / CONCERN / BLOCKER

---

*Prepared by: Claude Code | Date: 2026-07-04 | Sprint: J0A*

---

## SPRINT-BLACKBOX-0 — OPEN (2026-07-05)

**Purpose:** Offline, deterministic, human-gated append-only audit log foundation
for supervised JARVIS sprints.

**Commits:**
- **Implementation commit:** TBD — feat(automation): add BLACKBOX-0 append-only sprint audit log
- **Docs commit:** TBD — docs(automation): document BLACKBOX-0 runbook and review evidence

### Files Changed

- `agents/blackbox_log.py` — new: audit log module (pure functions, no network, no subprocess)
- `tests/test_blackbox_log.py` — new: 36 tests
- `automation/BLACKBOX_RUNBOOK.md` — new: runbook and usage guide
- `automation/CODEX_REVIEW_REQUEST.md` — updated: added this section

### Test Counts

```
tests/test_blackbox_log.py  -> 36 passed, 0 failed

Regression (no change):
  test_j0_voice_adapters + test_j0_voice_loop  -> 77 passed
  J0 existing suites                           -> 101 passed
  Proactive suites                             -> 69 passed

Grand total: 283 passed, 0 failed
```

### Explicit Claims for Codex to Verify

1. **APPEND-ONLY**: append_event never rewrites old events. Opens file in "ab" mode.
2. **ATOMIC APPEND**: lock file using O_CREAT|O_EXCL acquired before read-then-write.
3. **HASH CHAIN**: each event_hash covers all fields except event_hash itself (canonical JSON, sort_keys, SHA-256).
4. **CONTINUES ON CORRUPTION**: append_event returns integrity_warnings and still appends when prior log is corrupt.
5. **NO NETWORK**: no requests, no Telegram, no sendMessage, no network import in blackbox_log.py.
6. **NO SUBPROCESS**: no subprocess.run or subprocess.Popen in blackbox_log.py.
7. **NO .ENV**: no .env read, no os.environ access to secrets in blackbox_log.py.
8. **NO AUTO-COMMIT**: create_anchor_record returns a dict; module never calls git commit.
9. **EVIDENCE GUARDRAILS**: raw_diff, diff_text, full_stdout, full_stderr, secret_dump, env_dump keys in details/evidence are replaced with [REDACTED:raw_blob_not_allowed]; not stored verbatim.
10. **REDACTION**: keys containing token/api_key/secret/password/bearer/webhook redacted; Bearer tokens in string values redacted.
11. **UTF-8**: all writes use UTF-8; canonical JSON uses ensure_ascii=False; Turkish text survives round-trip.
12. **NULL COMMIT HASH**: commit_hash=None is valid; no self-referential commit-hash requirement.
13. **STRUCTURED ERRORS**: validate_log returns ValidationResult dataclass with errors list; not just bool.
14. **ANCHOR VERIFY**: verify_anchor detects changed log bytes against old anchor digest.
15. **NO SCHEDULER / NO AUTONOMOUS**: no loop, no scheduler, no cron, no AUTO in blackbox_log.py.

### Honest Limitations (stated clearly, not claimed fixed)

- Hash chain alone is not tamper-proof. Rewriting events and recomputing hashes produces an internally valid chain. Real tamper evidence requires Git-anchored digest comparison.
- Lock file protects same-machine concurrent writers using this module. Does not protect OS-level file replacement.
- Redaction is a safety net, not full DLP.
- Local Git history can be rewritten by an actor with repo control; reflog and external anchors are the defence.
- Stronger options (signed commits, remote mirror) are out of BLACKBOX-0 scope and documented as future.

### Review Verdict Expected
PASS / CONCERN / BLOCKER

---

*Prepared by: Claude Code | Date: 2026-07-05 | Sprint: BLACKBOX-0*
