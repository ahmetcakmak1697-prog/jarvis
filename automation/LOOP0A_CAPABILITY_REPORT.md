# LOOP0A_CAPABILITY_REPORT.md — LOOP-0A Capability / Machine-Gate Probe

> Date: 2026-07-08
> Branch: auto/opencode-deepseek
> Git HEAD (at probe start): fa204fc41a9fcccafb31478fb94f896801ea63ed
> (fa204fc41 docs(automation): mark BLACKBOX-0 feature frozen)

---

## Purpose

Read-only capability discovery for a possible future LOOP-0 driver. This
probe does **not** implement LOOP-0. It only determines whether the local
machine can support future orchestration of: Claude Code, Codex review,
pytest JUnit XML, pytest collect-only, and git status/diff inspection,
plus BLACKBOX event logging — without modifying any source or test code.

---

## 1. Starting State

```
pwd            -> /c/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto
git branch --show-current -> auto/opencode-deepseek
git status --short        -> (clean, no output)
git log --oneline -5:
  fa204fc41 docs(automation): mark BLACKBOX-0 feature frozen
  9bfb0f900 fix(automation): finalize BLACKBOX-0 validator chain state
  24a5fce93 fix(automation): prevent malformed hash propagation in BLACKBOX-0
  d07671ac0 fix(automation): close BLACKBOX-0 malformed input blockers
  c662cb3b7 fix(automation): harden BLACKBOX-0 integrity and anchoring
```

Working tree was clean before the probe started, consistent with the
confirmed BLACKBOX-0 feature-freeze state.

---

## 2. Claude CLI Capability

```
where.exe claude  -> C:\Users\Ahmedov\.local\bin\claude.exe   (exit 0)
claude --version  -> 2.1.204 (Claude Code)                    (exit 0)
claude --help     -> exit 0, full usage printed
```

**Findings:** `claude --help` clearly documents a non-interactive/headless
mode:
- `-p, --print` — "Print response and exit (useful for pipes)"
- `--output-format <format>` — `text` | `json` | `stream-json` (only works
  with `--print`)
- `--input-format <format>` — `text` | `stream-json` (only works with
  `--print`)
- `--json-schema <schema>` — structured JSON-schema-validated output
- `--permission-mode <mode>` — `acceptEdits`, `auto`, `bypassPermissions`,
  `manual`, `dontAsk`, `plan`
- `--allowedTools` / `--disallowedTools` — tool allow/deny lists
- `--max-budget-usd` — spend cap (print mode only)
- `--dangerously-skip-permissions` exists as a documented flag but was
  **not invoked** during this probe (hard-banned by task instructions).

**Conclusion:** Headless/print/JSON/non-interactive capability is clearly
available. No nested interactive session or live prompt was run — only
`--version` and `--help`.

---

## 3. Codex CLI Capability

```
where.exe codex  -> C:\Users\Ahmedov\AppData\Local\Programs\OpenAI\Codex\bin\codex.exe  (exit 0)
codex --version  -> codex-cli 0.142.0                          (exit 0)
codex --help     -> exit 0, full usage printed
```

**Findings:** `codex --help` lists dedicated non-interactive subcommands:
- `exec` (alias `e`) — "Run Codex non-interactively"
- `review` — "Run a code review non-interactively"
- `-a, --ask-for-approval <never|on-request|on-failure|untrusted>` —
  approval policy, including a fully non-interactive `never` mode
- `-s, --sandbox <read-only|workspace-write|danger-full-access>`
- `--dangerously-bypass-approvals-and-sandbox` exists as a documented flag
  but was **not invoked** during this probe (hard-banned by task
  instructions).

**Conclusion:** Review-only/headless/non-interactive capability appears
available via `codex review` and `codex exec`. No interactive Codex
session was started, no update was triggered, nothing was installed.

---

## 4. Adopt-Over-Build: Local Control-Plane Findings

Checked local availability only — no install, no browsing:

| Tool | Local availability |
|---|---|
| `amux` | Not locally available / not evaluated |
| `tmux` | Not locally available / not evaluated |
| `powershell.exe` (Windows PowerShell 5.1) | Available — `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` |
| `pwsh` (PowerShell 7) | Not locally available / not evaluated |
| `python` / `py` (subprocess-capable) | Available — multiple interpreters found (`.venv`, `C:\Python314`, `C:\Program Files\Python311`, WindowsApps shim); `py.exe` launcher present |
| `claude` CLI | Available, headless-capable (see §2) |
| `codex` CLI | Available, headless-capable (see §3) |

**Assessment:** No ready-made multi-agent orchestration/control-plane tool
(e.g. `amux`, `tmux`) is present on this machine. What **is** available
locally — Windows PowerShell, Python subprocess, `claude -p`/`--output-format
json`, and `codex exec`/`review` — is sufficient to script a simple
one-shot or looped driver without adopting an external control plane.

Given the current scope — single user, single Windows machine, one local
repo, explicit human gate before any autonomous action — adopting a
general-purpose external orchestration tool (tmux-based session
management, amux-style multi-agent control plane, etc.) looks **oversized**
for the actual requirement, which is closer to "shell out to two CLIs,
read their exit codes/JSON output, check pytest results, log one BLACKBOX
event." A thin PowerShell or Python script driving already-available
headless CLI modes appears proportionate. This is a finding, not a final
architecture decision — no LOOP-0 design is adopted here.

---

## 5. Pytest JUnit XML Machine Gate

Command run (temporary probe artifact, later deleted):
```
py -3.11 -m pytest tests/test_blackbox_log.py -q --tb=short --junitxml=automation/.loop0a_probe_tmp/blackbox_junit.xml
```

- Exit code: **0**
- `76 passed in 0.87s` (stdout)
- JUnit XML file created: yes
- JUnit XML parsed successfully with `xml.etree.ElementTree` (stdlib, no
  install needed)
- Parsed root tag: `testsuites`
- Parsed counters: **tests=76, failures=0, errors=0, skipped=0**

**Conclusion:** The JUnit XML output is a reliable, parseable machine gate
for pytest results using only the Python standard library.

---

## 6. Pytest Collect-Only Machine Gate

Command run:
```
py -3.11 -m pytest tests/test_blackbox_log.py --collect-only -q
```

- Exit code: **0**
- Node IDs: fully visible and parseable, one per line, e.g.
  `tests/test_blackbox_log.py::test_first_event_sequence_and_prev_hash`
- Collected count line: `76 tests collected in 0.16s`
- **Matches JUnit XML test count exactly (76 == 76).**

**Conclusion:** collect-only output and JUnit XML output agree, confirming
both are usable as independent/cross-checking machine gates.

---

## 7. Git Diff/Status Machine Readability

Checked mid-probe, before writing the report or BLACKBOX event:
```
git status --short  -> "?? automation/.loop0a_probe_tmp/" (only the temp probe dir; no tracked file touched)
git diff --stat      -> (empty — no tracked file changed)
git diff --check     -> (empty — clean)
```

No source or test file was changed by the probe at any point. The only
filesystem change prior to cleanup was the untracked, git-ignorable
temporary probe directory, which was removed afterward (see §... below).

---

## 8. Cleanup of Temporary Probe Artifacts

```
rm -rf automation/.loop0a_probe_tmp/
```

Confirmed removed: a post-cleanup listing of `automation/` showed no
`.loop0a_probe_tmp` entry. Only the two intended output files remain new:
`automation/LOOP0A_CAPABILITY_REPORT.md` (this file) and one appended
event in `automation/BLACKBOX.jsonl`.

---

## 9. BLACKBOX Event

One event was appended via `agents.blackbox_log.append_event()` (never by
hand-editing the JSONL file) summarizing this probe's completion. See
`automation/BLACKBOX.jsonl` for the recorded `LOOP0A_CAPABILITY_PROBE`
event with status, branch, git_head, and the safety flags listed in
Task instructions.

---

## Risks / Blockers / Concerns

- **No blockers found.** All probed capabilities (Claude CLI headless
  mode, Codex CLI headless/review mode, pytest JUnit XML, pytest
  collect-only, git status/diff) behaved as expected and are machine-
  readable without modifying source or test code.
- **Concern (non-blocking):** No dedicated multi-agent control-plane tool
  (tmux, amux) is installed locally. This is not a blocker — the
  standard-library/CLI-native tools already available are adequate for
  the current single-user, single-machine scope — but it does mean any
  future LOOP-0 driver would be custom-scripted (PowerShell or Python)
  rather than adopting an existing framework.
- **Concern (non-blocking):** `--dangerously-skip-permissions` (Claude)
  and `--dangerously-bypass-approvals-and-sandbox` (Codex) exist as real
  flags on this machine. Their mere availability is a standing risk for
  any future automation design and should be explicitly and permanently
  excluded from any LOOP-0 proposal, not just avoided in this probe.

---

## Explicit Statements

- "LOOP-0A did not implement LOOP-0."
- "LOOP-0A did not enable auto-fix retry."
- "LOOP-0A did not use --dangerously-skip-permissions."
- "LOOP-0A did not start J0B/Piper/mic/audio/Telegram/scheduler."
- "LOOP-0A produced capability evidence only."

---

*Prepared by: Claude Code | Date: 2026-07-08 | Probe: LOOP-0A*
