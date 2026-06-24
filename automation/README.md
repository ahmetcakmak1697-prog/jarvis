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

## Normal Autonomous Session Flow

1. **GPT writes a task card** → saved to `automation/GPT_TASK.md`
2. **Claude reads roadmap + task card** → writes plan to `automation/CLAUDE_PLAN.md`
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
