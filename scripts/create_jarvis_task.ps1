#Requires -Version 5.1
<#
.SYNOPSIS
    Prints (or optionally registers) a Windows Task Scheduler task for the
    JARVIS proactive dry-run runner.

.DESCRIPTION
    Default mode: PRINT ONLY. Displays the intended task configuration and the
    equivalent Register-ScheduledTask command. Does NOT create a task. No
    ScheduledTask cmdlets are called in preview mode.

    Pass -Apply to actually register the task. Requires PowerShell as
    Administrator.

    SAFETY RULES (read before using -Apply):
      - This script schedules DRY-RUN mode only. No --live flag is used.
      - Live delivery is BLOCKED until E1-S4 Telegram smoke test passes.
      - Do NOT add --live to the task action until E1-S4 is signed off.
      - Do NOT set JARVIS_PROACTIVE_ENABLED=1 in the task environment until
        E1-S4 live wiring is implemented and tested.
      - This script does NOT read .env, touch tokens, or call Telegram.

.PARAMETER Apply
    If set, registers the scheduled task. Requires Administrator privileges.
    Omit to print only (default/safe mode).

.PARAMETER TaskName
    Name for the scheduled task. Defaults to "JARVIS_ProactiveRunner_DryRun".

.PARAMETER RepeatMinutes
    How often to run (minutes). Defaults to 30.

.EXAMPLE
    # Preview only (safe - no task created, no ScheduledTask cmdlets called)
    .\create_jarvis_task.ps1

.EXAMPLE
    # Actually register the task (requires Admin, only after E1-S4 passes)
    .\create_jarvis_task.ps1 -Apply
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$Apply,
    [string]$TaskName      = "JARVIS_ProactiveRunner_DryRun",
    [int]   $RepeatMinutes = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Config - edit these if your environment differs
# ---------------------------------------------------------------------------
$RepoRoot      = "C:\Users\Ahmedov\Desktop\Jarvis\jarvis-agent-auto"
$PythonExe     = "py"
$PythonVersion = "-3.11"
$RunnerModule  = "-m agents.proactive_runner"
# NOTE: no --live flag. Live delivery blocked until E1-S4 Telegram smoke passes.

$FullArgument  = "$PythonVersion $RunnerModule"

# ---------------------------------------------------------------------------
# Print preview (always shown - no ScheduledTask cmdlets called here)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "===== JARVIS Task Scheduler - DRY-RUN TEMPLATE =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "Task name       : $TaskName"
Write-Host "Executable      : $PythonExe $FullArgument"
Write-Host "Working dir     : $RepoRoot"
Write-Host "Repeat interval : every $RepeatMinutes minutes"
Write-Host "Mode            : DRY-RUN (no live flag; no Telegram send)"
Write-Host ""
Write-Host "LIVE DELIVERY IS BLOCKED until E1-S4 Telegram smoke test." -ForegroundColor Yellow
Write-Host "Do NOT add --live until E1-S4 is signed off by Ahmet." -ForegroundColor Yellow
Write-Host ""
Write-Host "--- Equivalent PowerShell command (run as Admin with -Apply) ---"
Write-Host "Register-ScheduledTask ``"
Write-Host "    -TaskName   $TaskName ``"
Write-Host "    -Action     (New-ScheduledTaskAction -Execute $PythonExe -Argument '$FullArgument' -WorkingDirectory '$RepoRoot') ``"
Write-Host "    -Trigger    (New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes $RepeatMinutes) -Once -At (Get-Date)) ``"
Write-Host "    -Settings   (New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew -DontStopIfGoingOnBatteries) ``"
Write-Host "    -RunLevel   Highest ``"
Write-Host "    -Force"
Write-Host ""

# ---------------------------------------------------------------------------
# Exit here in preview mode - nothing below runs without -Apply
# ---------------------------------------------------------------------------
if (-not $Apply) {
    Write-Host "--- PREVIEW ONLY (task NOT created) ---" -ForegroundColor Green
    Write-Host "Pass -Apply to actually register the task (requires Admin)."
    Write-Host ""
    exit 0
}

# ---------------------------------------------------------------------------
# Registration (only with -Apply) - ScheduledTask cmdlets called here only
# ---------------------------------------------------------------------------

# Safety check: warn if live env var is set
$liveEnv = [System.Environment]::GetEnvironmentVariable("JARVIS_PROACTIVE_ENABLED")
if ($liveEnv -eq "1") {
    Write-Warning "JARVIS_PROACTIVE_ENABLED=1 is set in the current environment."
    Write-Warning "The registered task will inherit this if run in the same context."
    Write-Warning "Ensure E1-S4 Telegram smoke test has passed before proceeding."
}

$Action = New-ScheduledTaskAction `
    -Execute          $PythonExe `
    -Argument         $FullArgument `
    -WorkingDirectory $RepoRoot

$Trigger = New-ScheduledTaskTrigger `
    -RepetitionInterval (New-TimeSpan -Minutes $RepeatMinutes) `
    -Once `
    -At (Get-Date)

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit     (New-TimeSpan -Minutes 2) `
    -MultipleInstances      IgnoreNew `
    -DontStopIfGoingOnBatteries

if ($PSCmdlet.ShouldProcess($TaskName, "Register-ScheduledTask")) {
    Register-ScheduledTask `
        -TaskName  $TaskName `
        -Action    $Action `
        -Trigger   $Trigger `
        -Settings  $Settings `
        -RunLevel  Highest `
        -Force | Out-Null

    Write-Host "Task registered: $TaskName" -ForegroundColor Green
    Write-Host "Verify : Get-ScheduledTask -TaskName '$TaskName'"
    Write-Host "Run now: Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host ""
    Write-Host "To remove: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
}
