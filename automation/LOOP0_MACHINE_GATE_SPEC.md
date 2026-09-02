# LOOP0_MACHINE_GATE_SPEC.md

> Date: 2026-07-08
> Branch: auto/opencode-deepseek
> Status: SPECIFICATION ONLY — NOT IMPLEMENTED

---

## 1. Purpose

- This spec defines future LOOP-0 machine gates.
- It does not implement LOOP-0.
- It does not enable autonomous development.
- It does not enable auto-fix retry.
- It does not start J0B/Piper/mic/audio/Telegram/scheduler.

This document is a design reference for a future implementation step. No
runner, orchestrator, or automation code is created by this document.

---

## 2. Current evidence base

Reference the prior capability proof:

- BLACKBOX-0 is FEATURE-FROZEN (`fa204fc41`).
- LOOP-0A confirmed (`f2015d0d3`):
  - Claude CLI is available and headless-capable.
  - Codex CLI is available and review/headless-capable.
  - pytest JUnit XML works and is parseable.
  - pytest collect-only works.
  - JUnit and collect-only counts matched: 76/76.
  - BLACKBOX append_event works.
  - no auto-fix retry was enabled.
  - no source/test/code files were modified by LOOP-0A.

This is capability evidence only. It is not implementation, and it does
not imply LOOP-0 is approved to run autonomously.

---

## 3. Adopt-over-build check

Before implementing custom LOOP-0 parsing/control code, what mature
existing tools can be used?

- pytest already emits JUnit XML.
- Python stdlib `xml.etree.ElementTree` is enough for JUnit XML parsing
  at current scope.
- pytest collect-only output is available as a cross-check.
- Extra pytest JSON/report plugins may be considered later, but are not
  needed now unless a clear machine-gate gap appears.
- PowerShell + Python subprocess are sufficient for a single-user,
  single-Windows-machine, local-repo workflow.
- tmux/amux style control planes were not locally available in LOOP-0A
  and appear oversized for current scope.
- This remains a design finding, not final implementation.

---

## 4. Permanent forbidden list

This section is central and explicit. Future LOOP-0 must never use:

- Claude `--dangerously-skip-permissions`
- Codex `--dangerously-bypass-approvals-and-sandbox`
- `danger-full-access` sandbox mode
- `git push`
- `git reset`
- `git checkout` unless explicitly approved for a recovery task
- `git rebase`
- secret/.env reads
- package installs
- live Telegram
- scheduler activation
- mic/audio/Piper/J0B activation
- autonomous task selection
- automatic commit
- automatic next-task continuation

These are not task-by-task suggestions; they are central policy.

---

## 5. Auto-fix retry status

**Auto-fix retry is NOT approved.**

Current rule:
- Codex BLOCKER means STOP and return to Ahmet.
- LOOP-0B/C must not implement automatic repair attempts.

Future possible rule: a limited retry mechanism may be considered later
only after explicit Ahmet approval and only with all four constraints:

1. Every attempt is written to BLACKBOX with attempt number, blocker
   reason, diff summary/hash, machine-gate result, and Codex verdict.
2. Identical or near-identical diff/fingerprint causes early stop with
   `repeated_identical_fix`.
3. No retry attempt may commit automatically.
4. Retry scope remains locked to the original task card allowed paths;
   any scope escape stops immediately.

Until separately approved, this section is informational only and not
implementable.

---

## 6. Machine gate PASS definition

Machine-gate PASS requires all of the following.

### 6.1 pytest execution gate

- pytest command exits with code 0.
- JUnit XML file exists.
- JUnit XML is parseable.
- JUnit tests > 0.
- JUnit failures == 0.
- JUnit errors == 0.

### 6.2 collect-only gate

- pytest collect-only exits with code 0.
- collected node IDs are visible and parseable.
- collected node count > 0.
- collected count matches JUnit tests count, unless the spec explicitly
  allows a documented exception.

### 6.3 git cleanliness/scope gate

- `git status --short` is machine-readable.
- changed files are limited to task card allowed paths.
- `git diff --check` is clean, except explicitly classified benign
  CRLF/LF warnings.
- no untracked junk files remain.
- no source/test weakening patterns are allowed unless the task
  explicitly allows test changes.

### 6.4 baseline protection

- expected test nodes may be stored or captured before a task.
- missing baseline nodes after a task are a blocker unless the task
  explicitly authorizes test deletion/rename.
- `tests_zero` is always blocker.

---

## 7. Machine gate failure taxonomy

- `pytest_exit_nonzero`
- `junit_xml_missing`
- `junit_xml_unparseable`
- `tests_zero`
- `junit_failures`
- `junit_errors`
- `collect_exit_nonzero`
- `collect_nodes_empty`
- `count_mismatch`
- `git_diff_check_failed`
- `untracked_junk_file`
- `diff_scope_violation`
- `forbidden_command_detected`
- `forbidden_file_modified`
- `test_weakening_detected`
- `baseline_node_missing`
- `codex_not_called_because_machine_gate_failed`
- `codex_blocker`
- `codex_concern`
- `human_gate_required`

---

## 8. Codex review gate

- Codex review is called only after machine gate PASS.
- Codex is review-only.
- Codex must not edit.
- Codex must not commit.
- Codex must not install or update.
- Codex output must be classified as PASS / BLOCKER / CONCERN.

Rules:

- PASS means candidate is eligible for Ahmet approval, not automatic
  commit.
- BLOCKER means stop and return to Ahmet.
- CONCERN means stop and return to Ahmet unless the concern is
  explicitly classified as post-freeze/non-blocking by Ahmet.
- No automatic next task after Codex PASS.

---

## 9. Human gate rules

Even if:
- Claude finishes
- machine gate PASSes
- Codex PASSes

LOOP-0 must stop and ask Ahmet before:

- commit
- next task
- scope expansion
- retry/fix attempt
- roadmap change
- feature-freeze declaration
- enabling runtime behavior
- live Telegram/scheduler/mic/audio/Piper
- any .env/secret-related action

Ahmet is the gate, not the copy-paste carrier.

---

## 10. BLACKBOX logging requirements

Future LOOP-0 should log:

- `task_start`
- `claude_attempt_start`
- `claude_attempt_end`
- `machine_gate_result`
- `codex_review_requested`
- `codex_verdict`
- `human_gate_required`
- `task_pass_candidate`
- `task_blocked`
- `task_concern`
- `commit_recorded`, only after Ahmet-approved commit

Required event fields should include:
- `task_id`
- `attempt_number`, if applicable
- `branch`
- `git_head_before`
- `git_head_after`, if commit happened
- `allowed_paths`
- `changed_files`
- `diff_stat`
- `diff_hash`/fingerprint
- `pytest_exit_code`
- JUnit `tests`/`failures`/`errors`
- `collect_only` count
- `codex_status`
- `blocker_or_concern_summary`
- `safety_flags`

BLACKBOX logging must never replace human approval.

---

## 11. Unicode / UTF-8 reporting rule

All future LOOP-0 generated reports/logs must be written as UTF-8 text
using the existing project UTF-8 discipline.

Future implementation must avoid mojibake-prone output and must
test/report:
- report files are UTF-8 readable
- JSON/JSONL logs are UTF-8 readable
- Turkish characters and em dash style punctuation do not corrupt
  CLI-readable artifacts

This is a specification rule only. No tests are added by this document.

---

## 12. Allowed future LOOP-0B shape

LOOP-0B is a future stub task, not implemented here.

LOOP-0B may only:
- run a tiny pre-approved stub task
- produce JUnit XML
- parse collect-only
- call Codex review-only after machine gate PASS
- write BLACKBOX events
- stop at Ahmet human gate

LOOP-0B may not:
- auto-fix
- commit automatically
- choose another task
- run J0B/Piper
- activate runtime systems

---

## 13. Open decisions

The following are open / not approved:

- auto-fix retry
- repeated-diff fingerprint policy
- exact diff hash algorithm
- JSON schema for Claude output
- exact Codex invocation mode
- commit automation
- task queue format
- whether a BLACKBOX event is required for every probe/spec step or
  only implementation steps

---

## 14. Change log

- 2026-07-08: LOOP-0S machine-gate spec drafted (docs only). See
  `automation/AUTONOMY_LOG.md` for the corresponding session entry.

---

*Prepared by: Claude Code | Date: 2026-07-08 | Sprint: LOOP-0S (spec only)*
