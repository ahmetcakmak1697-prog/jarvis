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

    [switch]$PrecheckOnly
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
        [string]$TaskFilePath
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    try {
        $pinfo = New-Object System.Diagnostics.ProcessStartInfo
        $pinfo.FileName = "cmd.exe"
        $pinfo.Arguments = "/c opencode run `"$Prompt`""
        $pinfo.RedirectStandardOutput = $true
        $pinfo.RedirectStandardError = $true
        $pinfo.UseShellExecute = $false
        $pinfo.CreateNoWindow = $true
        $pinfo.WorkingDirectory = $RepoRoot
        $pinfo.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        $pinfo.StandardErrorEncoding = [System.Text.Encoding]::UTF8
        $proc = [System.Diagnostics.Process]::Start($pinfo)
        $stdout = $proc.StandardOutput.ReadToEnd()
        $stderr = $proc.StandardError.ReadToEnd()
        $proc.WaitForExit()
        $exitCode = $proc.ExitCode
        $log = @"
--- opencode run ---
timestamp: $timestamp
runner_cwd: $RunnerCwd
process_working_directory: $RepoRoot
task_file_path: $TaskFilePath
prompt_length: $($Prompt.Length)
round: $Round
exit_code: $exitCode
--- stdout ---
$stdout
--- stderr ---
$stderr
"@
        $log | Set-Content -Path $OutFile -Encoding UTF8
        $failed = $false
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
        return @{ ExitCode = $exitCode; Stdout = $stdout; Stderr = $stderr; Failed = $failed }
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
exit_code: -1
--- stdout ---
--- stderr ---
$errMsg
"@
        $log | Set-Content -Path $OutFile -Encoding UTF8
        return @{ ExitCode = -1; Stdout = ""; Stderr = $errMsg; Failed = $true }
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
    $ocResult = Invoke-OpenCodeRun -Prompt $prompt -OutFile $ocOutFile -Round $round -TaskFilePath $ResolvedTaskFile
    if ($ocResult.Failed) {
        $ocFailed = $true
        $ocExitCode = $ocResult.ExitCode
        Write-Step "opencode exit code: $ocExitCode"
        Write-ErrorStep "opencode failure detected (exit code $ocExitCode or task read failure)"
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

    # c) verifier_runner
    if ([string]::IsNullOrEmpty($ContractPath)) {
        $verifierPath = Join-Path -Path $ScriptRoot -ChildPath "docs\templates\outcome_contract.example.json"
    } else {
        $verifierPath = $ContractPath
        if (-not (Test-Path -LiteralPath $ContractPath)) {
            Write-ErrorStep "ContractPath not found: $ContractPath"
            exit 1
        }
        Write-Step "Using contract path: $ContractPath" -Color Cyan
    }
    if ((-not $SkipVerifier) -and (Test-Path -LiteralPath $verifierPath)) {
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
    } else {
        if ($SkipVerifier) {
            Write-Step "Verifier SKIPPED (SkipVerifier)" -Color Yellow
        } else {
            Write-Step "Verifier SKIPPED (contract not found)" -Color Yellow
        }
        $testOutput += "`n--- verifier --- SKIPPED`n"
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
