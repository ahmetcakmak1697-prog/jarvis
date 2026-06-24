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

When Ahmet says "Jarvis coding session start" or "haydi devam edelim", Claude does exactly this — nothing more:

1. Run `powershell -ExecutionPolicy Bypass -File scripts/jarvis_autonomy_status.ps1`
2. Read `automation/GPT_TASK.md` — if empty/template, **stop and wait for a task card**
3. Read `automation/SESSION_SUMMARY.md` for prior context
4. Write `automation/CLAUDE_PLAN.md` with safety classification before touching any file
5. If classification is `HUMAN_REQUIRED` → stop, add to `automation/HUMAN_NEEDED.md`, wait
6. If classification is `GPT_REVIEW_REQUIRED` → stop, explain, wait
7. Only proceed if `SAFE_AUTONOMOUS` and a valid task card exists

**Claude must not begin coding autonomously without a GPT-issued task card.**

---

## Normal Autonomous Session Flow

1. **GPT writes a task card** → saved to `automation/GPT_TASK.md`
2. **Claude bootstraps** (status script + reads task card + writes plan)
3. **Claude executes**: small patch → targeted tests → self-correct (max 3 attempts)
4. **Claude writes report** → `automation/CLAUDE_REPORT.md` and `automation/GPT_REVIEW_PACKET.md`
5. **Ahmet pastes GPT_REVIEW_PACKET.md to GPT** → GPT reviews and either:
   - Approves → next task
   - Flags risk → Claude fixes or escalates
   - Requires human → added to `automation/HUMAN_NEEDED.md`
6. **Session ends** → Claude updates `automation/SESSION_SUMMARY.md` and appends to `automation/AUTONOMY_LOG.md`

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
