# AUTONOMY_RULES.md — Claude Code Operating Rules for Jarvis

These rules govern every autonomous coding session in this repo.
Claude must follow these rules without exception.

---

## 0. Session Start Protocol

Every session begins with these steps in order — no exceptions:

1. **Status first** — run `scripts/jarvis_autonomy_status.ps1` (read-only)
2. **Roadmap second** — read `roadmap_state.json` and `automation/FAZ3_E1_T1_DECOMPOSITION.md` (or equivalent decomposition file); identify the next unblocked `SAFE_AUTONOMOUS` task
3. **Safety classification third** — classify the task as `SAFE_AUTONOMOUS`, `GPT_REVIEW_REQUIRED`, or `HUMAN_REQUIRED`
4. **Plan before edits** — write `automation/CLAUDE_PLAN.md` before touching any source file
5. **If `SAFE_AUTONOMOUS`** → execute immediately; do not wait for a GPT task card
6. **If `GPT_REVIEW_REQUIRED`** → stop, explain the ambiguity, wait for GPT
7. **If `HUMAN_REQUIRED`** → stop, add to `automation/HUMAN_NEEDED.md`, wait for Ahmet

---

## 1. Roadmap-First Execution

- Always read `roadmap_state.json` before starting any work.
- Select only the next unblocked step with `status: todo` or `status: in_progress`.
- Never skip dependencies (`depends_on` must all be `done`).
- Never work outside the active task's `allowed_paths`.

---

## 2. Token-Saver, High-Intelligence Mode

- Think deeply. Output compactly.
- Do not repeat project summaries each turn.
- Do not narrate obvious steps.
- Read only the files needed for the active task (targeted, not broad).
- Prefer grep/search before opening large files.
- Do not run redundant tests.

---

## 3. Small Patch Discipline

- Touch only files listed in the task card's allowed scope.
- No speculative features, no "while I'm here" cleanups.
- Every changed line must be traceable to the task requirement.
- Patch must be idempotent where possible.
- PowerShell paste: use `@'...'@` here-strings for Turkish content; never paste raw Unicode.

---

## 4. Test Gate

- Run the smallest relevant test first.
- Run broader regression only when shared logic is touched or before a commit recommendation.
- Self-correct test failures up to 3 attempts. Stop and report if still failing.
- Never claim success without seeing passing test output.

---

## 5. Commit Gate

- **`SAFE_AUTONOMOUS` tasks**: commit automatically after tests pass, git diff is known, and risks are low. Do not wait for explicit per-commit approval.
- **`GPT_REVIEW_REQUIRED` tasks**: prepare the commit, write `GPT_REVIEW_PACKET.md`, stop and wait.
- **`HUMAN_REQUIRED` tasks**: never commit until Ahmet explicitly says so.
- "Commit-ready" = tests pass + git diff known + risks disclosed.
- Never push unless Ahmet explicitly approves.
- After committing a `SAFE_AUTONOMOUS` task, continue immediately to the next `SAFE_AUTONOMOUS` task from the roadmap. Do not wait for acknowledgement.

---

## 6. Human Gate

Stop and ask before any of the following:

- Voice enrollment / microphone / speaker calibration
- Camera / room / presence sensor test
- Hardware pairing (Zigbee, Z-Wave, Sonoff, ESP32, Raspberry Pi)
- Home Assistant / live device control
- BMS / Niagara / Modbus / RS485 / router / camera / lock / alarm access
- API keys, tokens, secrets, `.env` edits, browser profiles, SSH keys
- Payment, purchase, email sending, official submission
- Destructive git: reset --hard, clean -f, branch -D, push --force
- Dependency install (pip install, npm install, etc.)
- Broad refactor (>3 files, unrelated to current task)

---

## 7. Forbidden Operations (always)

- Do not read or write `.env`, `.env.*`, secrets, credentials files.
- Do not call live web/API unless the task explicitly enables it.
- Do not use microphone, camera, speakers.
- Do not modify Telegram runtime delivery.
- Do not modify proactive runtime delivery.
- Do not add scheduler or background loop unless roadmap-specified.
- Do not use `git add -A` or `git add .` — stage specific files only.

---

## 8. Model Recommendation Rules

**Sonnet by default** for:
- Normal implementation, test fixes, small refactors
- CLI fixes, UI polish, report file generation
- Roadmap status updates, ordinary debugging

**Opus only** for:
- Major architecture decisions
- Cross-phase roadmap redesign
- Security/privacy boundary design
- Multi-agent orchestration design
- Complex concurrency/async/race-condition analysis
- Deep failure analysis after 3+ failed fixes
- Anything where wrong reasoning creates long-term technical debt

Do not request Opus to sound smarter. If Sonnet can do it, say so.

---

## 9. End-of-Task Report

Every task ends with this exact format (see `CLAUDE_REPORT.md` template):

```
TASK:
FILES CHANGED:
COMMANDS RUN:
TEST RESULTS:
GIT STATUS:
RISKS:
HUMAN NEEDED:
COMMIT READY: yes/no
SUGGESTED COMMIT:
NEXT SAFE STEP:
```
