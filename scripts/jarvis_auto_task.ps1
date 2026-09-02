<#
.SYNOPSIS
  JARVIS Auto-Coder Runner -- runs OpenCode/DeepSeek coding tasks non-interactively
  with deterministic checks and optional auto-commit.

.DESCRIPTION
  This script:
  1. Validates preconditions (TaskFile exists, git clean, opencode available).
  2. Runs OpenCode with the task file for up to MaxRounds.
  3. Runs deterministic checks (py_compile, pytest, verifier_runner).
  4. If checks fail, sends a repair prompt to OpenCode.
  5. On success, optionally auto-commits.

  FIRST-TIME BOOTSTRAP (before using this runner for real tasks):
  1. Create/edit this runner script.
  2. Manually review for correctness.
  3. Manually run: .\scripts\jarvis_auto_task.ps1 -TaskFile <taskfile> -PrecheckOnly
  4. Manually verify syntax and precheck output.
  5. Manually commit the runner itself.
  6. Only after that, use this runner for future automation tasks.

.PARAMETER TaskFile
  Required path to TASK_*.md file.

.PARAMETER CommitMessage
  Required when -AutoCommit is used. The git commit message.

.PARAMETER MaxRounds
  Maximum repair rounds (default 3).

.PARAMETER AutoCommit
  Switch: if set, auto-commits on success.

.PARAMETER SkipVerifier
  Switch: if set, skip the verifier_runner.py check.

.PARAMETER SkipFullTests
  Switch: if set, run pytest --collect-only instead of full test suite.

.EXAMPLE
  .\scripts\jarvis_auto_task.ps1 -TaskFile .\TASK_XXX.md -MaxRounds 4

.EXAMPLE
  .\scripts\jarvis_auto_task.ps1 -TaskFile .\TASK_XXX.md -CommitMessage "feat: add widget" -AutoCommit
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$TaskFile,

    [Parameter(Mandatory = $false)]
    [string]$CommitMessage,

    [Parameter(Mandatory = $false)]
    [int]$MaxRounds = 3,

    [switch]$AutoCommit,
    [switch]$SkipVerifier,
    [switch]$SkipFullTests,

    [Parameter(Mandatory = $false)]
    [string]$ContractPath = "",

    [Parameter(Mandatory = $false)]
    [string[]]$CommitPaths,

    [switch]$PrecheckOnly,

    [Parameter(Mandatory = $false)]
    [ValidateRange(1, [int]::MaxValue)]
    [int]$OpenCodeTimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Path $PSScriptRoot -Parent
$RunnerCwd = (Get-Location).Path
$RepoRoot = $ScriptRoot
$LogDir = Join-Path -Path $ScriptRoot -ChildPath ".verifier\reports"
$null = New-Item -ItemType Directory -Path $LogDir -Force

function Write-Section {
    param([string]$Title)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-Step {
    param(
        [string]$Msg,
        [string]$Color = "White"
    )
    Write-Host "  >> $Msg" -ForegroundColor $Color
}

function Write-ErrorStep {
    param([string]$Msg)
    Write-Host "  !! $Msg" -ForegroundColor Red
}

function Invoke-OpenCodeRun {
    param(
        [string]$Prompt,
        [string]$OutFile,
        [int]$Round,
        [string]$TaskFilePath,
        [int]$TimeoutSeconds = 900
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $tempDir = Join-Path -Path $LogDir -ChildPath "tmp"
    $null = New-Item -ItemType Directory -Path $tempDir -Force
    $stdoutFile = Join-Path -Path $tempDir -ChildPath "oc_stdout_$Round.txt"
    $stderrFile = Join-Path -Path $tempDir -ChildPath "oc_stderr_$Round.txt"

    # Early log marker: write "running" status before launch
    $earlyLog = @"
--- opencode run ---
timestamp: $timestamp
runner_cwd: $RunnerCwd
process_working_directory: $RepoRoot
task_file_path: $TaskFilePath
prompt_length: $($Prompt.Length)
round: $Round
timeout_seconds: $TimeoutSeconds
process_id: (not yet launched)
status: running
--- stdout ---
(not yet available)
--- stderr ---
(not yet available)
"@
    $earlyLog | Set-Content -Path $OutFile -Encoding UTF8

    try {
        $pinfo = New-Object System.Diagnostics.ProcessStartInfo
        $pinfo.FileName = "cmd.exe"
        # Redirect stdout/stderr to temp files to avoid deadlock
        $cmdArgs = "/c opencode run `"$Prompt`" > `"$stdoutFile`" 2> `"$stderrFile`""
        $pinfo.Arguments = $cmdArgs
        $pinfo.RedirectStandardOutput = $false
        $pinfo.RedirectStandardError = $false
        $pinfo.UseShellExecute = $false
        $pinfo.CreateNoWindow = $true
        $pinfo.WorkingDirectory = $RepoRoot
        $proc = [System.Diagnostics.Process]::Start($pinfo)

        $pidFile = $proc.Id
        Write-Step "OpenCode process ID: $pidFile" -Color Cyan
        Write-Step "OpenCode timeout: $TimeoutSeconds seconds" -Color Cyan

        # Wait for process with timeout
        $timedOut = -not $proc.WaitForExit($TimeoutSeconds * 1000)

        if ($timedOut) {
            Write-Step "OpenCode TIMEOUT after $TimeoutSeconds seconds -- killing process tree." -Color Yellow
            try {
                & taskkill.exe /PID $pidFile /T /F 2>$null | Out-Null
            } catch {
                try { $proc.Kill() } catch { }
            }
            try {
                if (-not $proc.HasExited) {
                    try { $proc.Kill() } catch { }
                }
                $proc.WaitForExit(5000) | Out-Null
            } catch { }
            $exitCode = -1
            $failed = $true
            $timeoutReason = "TIMEOUT: opencode did not finish within $TimeoutSeconds seconds (PID $pidFile). Process tree kill attempted."
        } else {
            $exitCode = $proc.ExitCode
            $failed = $false
            $timeoutReason = $null
        }

        # Read temp files
        $stdout = ""
        $stderr = ""
        if (Test-Path -LiteralPath $stdoutFile) {
            $stdout = Get-Content -Path $stdoutFile -Raw -Encoding UTF8
        }
        if (Test-Path -LiteralPath $stderrFile) {
            $stderr = Get-Content -Path $stderrFile -Raw -Encoding UTF8
        }

        # Clean up temp files
        if (Test-Path -LiteralPath $stdoutFile) { Remove-Item -Path $stdoutFile -Force }
        if (Test-Path -LiteralPath $stderrFile) { Remove-Item -Path $stderrFile -Force }

        # Build final log
        $log = @"
--- opencode run ---
timestamp: $timestamp
runner_cwd: $RunnerCwd
process_working_directory: $RepoRoot
task_file_path: $TaskFilePath
prompt_length: $($Prompt.Length)
round: $Round
timeout_seconds: $TimeoutSeconds
process_id: $pidFile
status: completed
exit_code: $exitCode
timed_out: $($timedOut -eq $true)
"@

        if ($timedOut) {
            $log += @"

--- stdout ---
(not available — timed out)
--- stderr ---
$timeoutReason
"@
        } else {
            $log += @"

--- stdout ---
$stdout
--- stderr ---
$stderr
"@
        }

        $log | Set-Content -Path $OutFile -Encoding UTF8

        # False-success detection (only if not timeout)
        if (-not $timedOut) {
            if ($exitCode -ne 0) {
                $failed = $true
            } else {
                $taskName = Split-Path -Leaf $TaskFilePath
                $combined = "$stdout $stderr"
                $failurePatterns = @(
                    "Read.*$taskName.*failed",
                    "File not found:.*$taskName",
                    "The file does not exist in the current directory"
                )
                foreach ($pat in $failurePatterns) {
                    if ($combined -match $pat) {
                        $failed = $true
                        break
                    }
                }
            }
        }

        return @{ ExitCode = $exitCode; Stdout = $stdout; Stderr = $stderr; Failed = $failed; TimedOut = $timedOut }
    } catch {
        $errMsg = "opencode process launch failed with exception: $_"
        $log = @"
--- opencode run ---
timestamp: $timestamp
runner_cwd: $RunnerCwd
process_working_directory: $RepoRoot
task_file_path: $TaskFilePath
prompt_length: $($Prompt.Length)
round: $Round
timeout_seconds: $TimeoutSeconds
process_id: (launch failed)
status: error
exit_code: -1
timed_out: false
--- stdout ---
--- stderr ---
$errMsg
"@
        $log | Set-Content -Path $OutFile -Encoding UTF8
        return @{ ExitCode = -1; Stdout = ""; Stderr = $errMsg; Failed = $true; TimedOut = $false }
    }
}

# ─── PRECHECK ─────────────────────────────────────────────────────────────────
Write-Section "PRECHECK"

# 1. Check TaskFile exists and resolve to absolute path
$ResolvedTaskFile = Resolve-Path -LiteralPath $TaskFile -ErrorAction Stop
$ResolvedTaskFile = $ResolvedTaskFile.Path
Write-Step "TaskFile OK: $ResolvedTaskFile"

# 2. Check opencode availability
try {
    $ocVer = & opencode --version
    Write-Step "opencode $ocVer"
} catch {
    Write-ErrorStep "opencode not available (opencode --version failed)"
    exit 1
}

# 3. Print current branch and git status
$branch = git branch --show-current
Write-Step "Branch: $branch"
Write-Step "Git status:"
$statusLines = git status --short
if ($statusLines) {
    foreach ($line in $statusLines) {
        Write-Host "       $line" -ForegroundColor Gray
    }
} else {
    Write-Step "(clean)" -Color Gray
}

# 4. Refuse if there are existing non-ignored changes
$changedFiles = git status --short
if ($changedFiles) {
    Write-ErrorStep "Working tree has uncommitted changes. Please commit or stash first."
    exit 1
}
Write-Step "Working tree clean"

# 5. Refuse if AutoCommit without CommitMessage
if ($AutoCommit -and [string]::IsNullOrEmpty($CommitMessage)) {
    Write-ErrorStep "-CommitMessage is required when -AutoCommit is used."
    exit 1
}

# 6. PrecheckOnly mode: validate only, do not run opencode or tests
if ($PrecheckOnly) {
    Write-Step "PrecheckOnly mode -- all preconditions satisfied." -Color Green
    exit 0
}

# Log timeout value
Write-Step "OpenCodeTimeoutSeconds = $OpenCodeTimeoutSeconds" -Color Cyan

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────
$allPassed = $false
$roundLogs = @()

for ($round = 1; $round -le $MaxRounds; $round++) {
    $skipThisRound = $false
    Write-Section "ROUND $round of $MaxRounds"

    $logFile = Join-Path -Path $LogDir -ChildPath "autocoder_round_$round.log"
    $roundLogs += $logFile

    if ($round -eq 1) {
        $prompt = "Read and follow @$ResolvedTaskFile exactly. Stay inside this worktree only. Do not inspect sibling worktrees or parent directories. Follow all safety rules in the task file."
    } else {
        # Repair round: read the failure log
        $prevLog = Join-Path -Path $LogDir -ChildPath "autocoder_round_$($round - 1).log"
        $prompt = "The previous attempt failed. Read the failure log at $prevLog, fix only the task-related issues, stay inside the allowed files from the task, then rerun required tests."
    }

    Write-Step "Running opencode..."
    $ocOutFile = Join-Path -Path $LogDir -ChildPath "opencode_round_$round.log"
    $ocFailed = $false
    $ocResult = Invoke-OpenCodeRun -Prompt $prompt -OutFile $ocOutFile -Round $round -TaskFilePath $ResolvedTaskFile -TimeoutSeconds $OpenCodeTimeoutSeconds
    if ($ocResult.Failed) {
        $ocFailed = $true
        $ocExitCode = $ocResult.ExitCode
        if ($ocResult.TimedOut) {
            Write-ErrorStep "opencode TIMED OUT after ${OpenCodeTimeoutSeconds}s"
        } else {
            Write-Step "opencode exit code: $ocExitCode"
            Write-ErrorStep "opencode failure detected (exit code $ocExitCode or task read failure)"
        }
        Write-Step "See $ocOutFile for details" -Color Yellow
    } else {
        $ocExitCode = $ocResult.ExitCode
        Write-Step "opencode exit code: $ocExitCode"
        if ($ocExitCode -ne 0) {
            Write-ErrorStep "opencode exited with code $ocExitCode"
            $ocFailed = $true
        }
    }

    if ($ocFailed) {
        $testFailed = $true
        Write-ErrorStep "OpenCode failure - skipping tests this round."
        # Use a flag to avoid 'continue' inside try/catch loop iteration (PS 5.1 bug)
        $skipThisRound = $true
    }

    if (-not $skipThisRound) {
    # ─── TESTS ────────────────────────────────────────────────────────────────
    Write-Section "TESTS"

    $testOutput = @"
Round $round
$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@
    $testFailed = $false

    # a) py_compile verifier_runner.py
    Write-Step "py_compile verifier_runner.py..."
    $compileResult = & py -3.11 -m py_compile .\scripts\verifier_runner.py 2>&1
    $testOutput += "`n--- py_compile ---`n$($compileResult | Out-String)"
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorStep "py_compile FAILED"
        $testFailed = $true
    } else {
        Write-Step "py_compile OK" -Color Green
    }

    # b) pytest
    if ($SkipFullTests) {
        Write-Step "pytest --collect-only (SkipFullTests)..."
        $pytestResult = & py -3.11 -m pytest .\tests\ --collect-only -q 2>&1
        $testOutput += "`n--- pytest collect-only ---`n$($pytestResult | Out-String)"
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorStep "pytest collection FAILED"
            $testFailed = $true
        } else {
            Write-Step "pytest collect OK" -Color Green
        }
    } else {
        Write-Step "pytest full suite..."
        $pytestResult = & py -3.11 -m pytest .\tests\ -q --tb=no 2>&1
        $testOutput += "`n--- pytest ---`n$($pytestResult | Out-String)"
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorStep "pytest FAILED"
            $testFailed = $true
        } else {
            Write-Step "pytest OK" -Color Green
        }
    }

    # c) verifier_runner -- fail closed: require explicit valid ContractPath when verifier runs
    if ($SkipVerifier) {
        Write-Step "Verifier SKIPPED (SkipVerifier)" -Color Yellow
        $testOutput += "`n--- verifier --- SKIPPED`n"
    } else {
        if ([string]::IsNullOrEmpty($ContractPath)) {
            Write-ErrorStep "ContractPath is required when verifier runs. Use -ContractPath <path> or -SkipVerifier."
            exit 1
        }
        if (-not (Test-Path -LiteralPath $ContractPath)) {
            Write-ErrorStep "ContractPath not found: $ContractPath"
            exit 1
        }
        Write-Step "Using contract path: $ContractPath" -Color Cyan
        $verifierPath = $ContractPath
        Write-Section "VERIFIER"
        Write-Step "Running verifier_runner.py..."
        $verifierResult = & py -3.11 .\scripts\verifier_runner.py $verifierPath 2>&1
        $testOutput += "`n--- verifier ---`n$($verifierResult | Out-String)"
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 2) {
            Write-ErrorStep "verifier FAILED (exit $LASTEXITCODE)"
            $testFailed = $true
        } elseif ($LASTEXITCODE -eq 2) {
            Write-Step "verifier NEEDS_HUMAN (exit 2)" -Color Yellow
        } else {
            Write-Step "verifier OK" -Color Green
        }
    }

    # Write round log
    $testOutput | Set-Content -Path $logFile -Encoding UTF8

    if (-not $testFailed) {
        $allPassed = $true
        Write-Step "All checks PASSED!" -Color Green
        break
    }

    if ($round -lt $MaxRounds) {
        Write-Step "Checks failed. Will retry in round $($round + 1)" -Color Yellow
    }
    } # end if(-not $skipThisRound)
}

# ─── FINAL RESULT ─────────────────────────────────────────────────────────────
if (-not $allPassed) {
    Write-Section "FAILED"
    Write-ErrorStep "Checks did not pass after $MaxRounds rounds."
    Write-Step "Check logs in $LogDir"
    exit 1
}

Write-Section "DONE"

# ─── COMMIT ───────────────────────────────────────────────────────────────────
if ($AutoCommit) {
    Write-Section "COMMIT"

    # Safety: check for .env, secrets, credentials, memory/ in staged/tracked changes
    $statusBefore = git status --short
    foreach ($line in $statusBefore) {
        if ($line -match '\.env|memory/|credentials|secrets') {
            Write-ErrorStep "BLOCKED: git status contains sensitive files: $line"
            exit 1
        }
    }

    # Infer paths if CommitPaths not provided, excluding sensitive/auto-generated patterns
    if (-not $CommitPaths -or $CommitPaths.Count -eq 0) {
        Write-Step "CommitPaths not provided -- inferring safe paths from git status..."
        $excludedPatterns = @('\.opencode/', 'TASK_*.md', '.verifier/', 'memory/', '*.env', '*secret*', '*credential*')
        $CommitPaths = @()
        foreach ($line in $statusBefore) {
            $path = $line.Substring(3).Trim()
            $excluded = $false
            foreach ($pat in $excludedPatterns) {
                if ($path -like $pat) { $excluded = $true; break }
            }
            if (-not $excluded) {
                $CommitPaths += $path
            }
        }
        Write-Step "Inferred paths: $($CommitPaths -join ', ')" -Color Gray
    }

    if ($CommitPaths.Count -eq 0) {
        Write-ErrorStep "No files to stage after filtering. Aborting commit."
        exit 1
    }

    git log --oneline -1
    Write-Step "Staging only CommitPaths..."
    git add -- $CommitPaths
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorStep "git add failed"
        exit 1
    }

    git commit -m $CommitMessage
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorStep "git commit failed"
        exit 1
    }

    Write-Step "Committed." -Color Green
    git log --oneline -5
    Write-Step "Final status:"
    git status --short
}

Write-Step "Done." -Color Green
exit 0
