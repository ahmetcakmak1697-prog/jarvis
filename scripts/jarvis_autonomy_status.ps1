# jarvis_autonomy_status.ps1 — Read-only autonomy session status
# No writes, no commits, no network, no secrets.

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host ""
Write-Host "=== JARVIS AUTONOMY STATUS ===" -ForegroundColor Cyan
Write-Host ""

# 1. Current directory
Write-Host "DIR:    $root"

# 2. Git branch
$branch = git branch --show-current 2>&1
Write-Host "BRANCH: $branch"

# 3. git status --short
$status = git status --short 2>&1
if ($status) {
    Write-Host "STATUS: $status"
} else {
    Write-Host "STATUS: clean"
}

# 4. Last commit
$lastCommit = git log -1 --oneline 2>&1
Write-Host "LAST:   $lastCommit"

Write-Host ""
Write-Host "--- automation/ harness ---" -ForegroundColor Yellow

# 5. automation/ directory
$autoDir = Join-Path $root "automation"
if (Test-Path $autoDir) {
    Write-Host "automation/  [EXISTS]"
} else {
    Write-Host "automation/  [MISSING]" -ForegroundColor Red
}

# 6. Required harness files
$files = @(
    "automation/README.md",
    "automation/AUTONOMY_RULES.md",
    "automation/GPT_TASK.md",
    "automation/CLAUDE_PLAN.md",
    "automation/CLAUDE_REPORT.md",
    "automation/GPT_REVIEW_PACKET.md",
    "automation/SESSION_SUMMARY.md",
    "automation/HUMAN_NEEDED.md",
    "automation/AUTONOMY_LOG.md"
)

foreach ($f in $files) {
    $full = Join-Path $root $f
    if (Test-Path $full) {
        Write-Host "  [OK]     $f"
    } else {
        Write-Host "  [MISSING] $f" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "--- Human Needed (preview) ---" -ForegroundColor Yellow

# 7. HUMAN_NEEDED.md preview
$humanFile = Join-Path $root "automation/HUMAN_NEEDED.md"
if (Test-Path $humanFile) {
    $lines = Get-Content $humanFile | Where-Object { $_ -match "^\- \[" } | Select-Object -First 5
    if ($lines) {
        $lines | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "  (none pending)"
    }
} else {
    Write-Host "  HUMAN_NEEDED.md not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "--- Next Step (preview) ---" -ForegroundColor Yellow

# 8. SESSION_SUMMARY.md next step preview
$summaryFile = Join-Path $root "automation/SESSION_SUMMARY.md"
if (Test-Path $summaryFile) {
    $content = Get-Content $summaryFile -Raw
    if ($content -match "(?m)^## Next Safe Step\s*\n([\s\S]*?)(\n## |\z)") {
        $nextStep = $Matches[1].Trim()
        if ($nextStep -and $nextStep -notmatch "^<!--") {
            Write-Host "  $nextStep"
        } else {
            Write-Host "  (not yet filled in SESSION_SUMMARY.md)"
        }
    } else {
        Write-Host "  (Next Safe Step section not found)"
    }
} else {
    Write-Host "  SESSION_SUMMARY.md not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""
