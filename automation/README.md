# automation/ — Jarvis Autonomous Coding Harness

This folder coordinates autonomous roadmap-driven development sessions between
Ahmet, GPT, and Claude Code. It contains no runtime code — only operation
templates and session state files.

---

## Role Split

| Role | Responsibility |
|------|---------------|
| **Ahmet** | Product owner. Real-world tester. Final approver at human gates. |
| **GPT** | Architect. Reviewer. Safety gatekeeper. Task designer. |
| **Claude Code** | Local coding operator. Tester. Disciplined executor. Reporter. |
| **roadmap_state.json** | Single source of truth for task sequence and status. |

---

## Session Bootstrap

When Ahmet says "Jarvis coding session start" or "haydi devam edelim", Claude does exactly this:

1. Run `powershell -ExecutionPolicy Bypass -File scripts/jarvis_autonomy_status.ps1`
2. Read `roadmap_state.json` and `automation/SESSION_SUMMARY.md` for current state
3. Read decomposition file (e.g. `automation/FAZ3_E1_T1_DECOMPOSITION.md`) to find the next unblocked task
4. Classify the task: `SAFE_AUTONOMOUS` / `GPT_REVIEW_REQUIRED` / `HUMAN_REQUIRED`
5. Write `automation/CLAUDE_PLAN.md` with classification before touching any source file
6. If `SAFE_AUTONOMOUS` → execute immediately (no GPT task card needed)
7. If `GPT_REVIEW_REQUIRED` → stop, explain the ambiguity, wait for GPT
8. If `HUMAN_REQUIRED` → stop, add to `automation/HUMAN_NEEDED.md`, wait for Ahmet

**GPT task cards are for `GPT_REVIEW_REQUIRED` tasks only. Claude must not wait for a task card to start `SAFE_AUTONOMOUS` work.**

---

## Normal Autonomous Session Flow

### SAFE_AUTONOMOUS path (default — no waiting)
1. **Claude bootstraps** (status script → roadmap → decomposition → classify → plan)
2. **Claude executes**: small patch → targeted tests → self-correct (max 3 attempts)
3. **Claude commits** passing work with a focused commit message
4. **Claude continues** to the next `SAFE_AUTONOMOUS` task without pausing
5. **Claude stops** only when it reaches a `GPT_REVIEW_REQUIRED` or `HUMAN_REQUIRED` boundary
6. **Session ends** → Claude updates `automation/SESSION_SUMMARY.md` and appends to `automation/AUTONOMY_LOG.md`

### GPT_REVIEW_REQUIRED path
1. Claude implements, runs tests, then **stops** — does not commit
2. Claude writes `automation/GPT_REVIEW_PACKET.md`
3. **Ahmet pastes it to GPT** → GPT reviews and either:
   - Approves → Claude commits and continues
   - Flags risk → Claude fixes or escalates
   - Requires human → added to `automation/HUMAN_NEEDED.md`

### HUMAN_REQUIRED path
1. Claude stops immediately, describes what is needed, adds item to `automation/HUMAN_NEEDED.md`
2. Ahmet acts (live test, secret, hardware, etc.), confirms result
3. Claude continues from next task

---

## File Index

| File | Purpose |
|------|---------|
| `README.md` | This file |
| `AUTONOMY_RULES.md` | Claude's operating rules for this project |
| `GPT_TASK.md` | Current task card from GPT (overwrite each session) |
| `CLAUDE_PLAN.md` | Claude's pre-edit plan (overwrite each task) |
| `CLAUDE_REPORT.md` | Claude's post-execution report (overwrite each task) |
| `GPT_REVIEW_PACKET.md` | Compact packet Ahmet pastes to GPT (overwrite each task) |
| `SESSION_SUMMARY.md` | End-of-session state snapshot (overwrite each session) |
| `HUMAN_NEEDED.md` | Pending items that need Ahmet's presence |
| `AUTONOMY_LOG.md` | Append-only dated log of all sessions |
