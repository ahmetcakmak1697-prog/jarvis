# Windows Task Scheduler Setup — JARVIS Proactive Runner

> E1-S6C doc. No scheduler task is created by following this guide until you
> explicitly run the registration step. Default dry-run only.

---

## Overview

The proactive runner is a one-shot Python script triggered by Windows Task Scheduler.
It evaluates the proactive policy, logs what would be delivered, and exits.

**Default mode:** dry-run — no Telegram, no network, no `.env` needed.
**Live delivery:** blocked until E1-S4 Telegram smoke test passes with Ahmet's sign-off.

---

## Supported Invocation

Always call the runner as a **Python module** from the **repo root**:

```
py -3.11 -m agents.proactive_runner
```

Direct file invocation (`py agents/proactive_runner.py`) is **not supported** — it
fails with `ModuleNotFoundError` because `agents/` is not on `sys.path` without `-m`.

---

## Manual Smoke Test (run before scheduling)

Open a terminal at the repo root and run:

```powershell
cd C:\Users\Ahmedov\Desktop\Jarvis\jarvis-agent-auto

# 1. Dry-run (default) — should exit 0, print JSON with sent=false
py -3.11 -m agents.proactive_runner

# 2. Live flag — must exit 1 with "NOT IMPLEMENTED" until E1-S4
py -3.11 -m agents.proactive_runner --live
```

**Expected output — dry-run:**
```json
{
  "ts": "...",
  "dry_run": true,
  "decision": "suppress",
  "reason": "proactive_disabled",
  "priority": "normal",
  "plan_status": null,
  "sent": false,
  "delivery": null
}
```

**Expected output — `--live` (blocked):**
```json
{"error": "LIVE DELIVERY NOT IMPLEMENTED: complete E1-S4 live Telegram smoke first...", "sent": false}
```

Both outputs above are correct and safe. If `--live` exits 0 or sends anything,
**stop immediately** — there is a bug.

---

## Task Scheduler Setup (step-by-step, dry-run only)

> Use the helper script `scripts/create_jarvis_task.ps1` to print the exact
> `Register-ScheduledTask` command. Run it first without `-Apply` to preview.

### Prerequisites

1. Python 3.11 installed; `py -3.11` resolves to the correct interpreter.
2. All repo dependencies installed in that Python (or venv activated via the task action).
3. `JARVIS_PROACTIVE_ENABLED` is NOT set to `1` — keep it unset or `0` for dry-run.

### Manual registration (dry-run)

Open **PowerShell as Administrator** and run:

```powershell
$Action = New-ScheduledTaskAction `
    -Execute "py" `
    -Argument "-3.11 -m agents.proactive_runner" `
    -WorkingDirectory "C:\Users\Ahmedov\Desktop\Jarvis\jarvis-agent-auto"

$Trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -Once -At (Get-Date)

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew `
    -StopIfGoingOnBatteries $false

Register-ScheduledTask `
    -TaskName "JARVIS_ProactiveRunner_DryRun" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -RunLevel Highest `
    -Force
```

**Working directory** must be `C:\Users\Ahmedov\Desktop\Jarvis\jarvis-agent-auto` (repo root).
The `-WorkingDirectory` argument to `New-ScheduledTaskAction` sets this.

### Verifying the task

```powershell
# List registered task
Get-ScheduledTask -TaskName "JARVIS_ProactiveRunner_DryRun"

# Run immediately (test)
Start-ScheduledTask -TaskName "JARVIS_ProactiveRunner_DryRun"

# Check last result (0 = success)
(Get-ScheduledTaskInfo -TaskName "JARVIS_ProactiveRunner_DryRun").LastTaskResult
```

### Removing the task

```powershell
Unregister-ScheduledTask -TaskName "JARVIS_ProactiveRunner_DryRun" -Confirm:$false
```

---

## Enabling Live Delivery (E1-S4 gate)

> WARNING: Do NOT enable live delivery before E1-S4 Telegram smoke test passes.
> That gate requires Ahmet to set `.env` tokens and confirm a real Telegram message
> on his phone. Until then, `--live` always exits 1 by design.

When E1-S4 is approved:

1. Set `JARVIS_PROACTIVE_ENABLED=1` in the task's environment (via Task Scheduler
   UI → Edit Action → Environment Variables, or via a `.env` loader script).
2. Update the task action argument from:
   `-3.11 -m agents.proactive_runner`
   to:
   `-3.11 -m agents.proactive_runner --live`
   **Only after E1-S4 live wiring is implemented in the codebase.**
3. Re-run the Telegram smoke test before putting the task on a schedule.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: No module named 'agents'` | Direct file invocation used | Switch to `py -3.11 -m agents.proactive_runner` |
| Exit 1 on `--live` | Expected — live not implemented | Do not pass `--live` until E1-S4 |
| `sent: true` in dry-run output | Bug — gate not enforced | File an issue; do not schedule |
| Empty stdout / crash | Working directory wrong | Verify `-WorkingDirectory` is repo root |

---

*Written by: Claude Code | Date: 2026-06-27 | E1-S6C*
