# JARVIS Memory Backup Script
# P0.2 - scripts/backup_memory.ps1
#
# Amac:
#   memory/ ve chroma_db altindaki kritik verileri yedekler.
#   .env ASLA yedeklenmez (secrets).
#   jarvis_checkpoint_*.zip ve *.bak ZATEN .gitignore'da.
#
# Kullanim:
#   .\scripts\backup_memory.ps1             # varsayilan: scripts'in bir ust klasoru
#   .\scripts\backup_memory.ps1 -JarvisRoot "C:\path\to\jarvis"
#   .\scripts\backup_memory.ps1 -DryRun     # yazma, goster
#
# Otomasyona baglamak icin:
#   Gorev Zamanlayici (Task Scheduler) ile haftada bir calistir.
#   Ornek: Her Pazar 03:00'te.

param(
    [string]$JarvisRoot = (Split-Path $PSScriptRoot -Parent),
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ─── Konfigurasyon ───────────────────────────────────────────────────────────
$Timestamp   = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir   = Join-Path $JarvisRoot "backups"
$BackupFile  = Join-Path $BackupDir "jarvis_memory_backup_$Timestamp.zip"

# Yedeklenecek klasorler/dosyalar (proje kokunden goreli)
$IncludePaths = @(
    "memory\conversations.json",
    "memory\memory_candidates.json",
    "memory\audit_log.jsonl",
    "memory\task_history.json",
    "memory\user_profile.json",
    "memory\jarvis_memory.db",
    "memory\chroma_db"
)

# Asla yedeklenmeyecekler
$ExcludePatterns = @(
    ".env",
    ".env.*",
    "*.bak",
    "jarvis_checkpoint_*.zip",
    "jarvis_sync_snapshot_*.zip"
)

# ─── Fonksiyonlar ────────────────────────────────────────────────────────────
function Write-Status {
    param([string]$Msg, [string]$Color = "Cyan")
    Write-Host $Msg -ForegroundColor $Color
}

function Get-HumanSize {
    param([long]$Bytes)
    if ($Bytes -ge 1MB) { return "{0:N1} MB" -f ($Bytes / 1MB) }
    if ($Bytes -ge 1KB) { return "{0:N1} KB" -f ($Bytes / 1KB) }
    return "$Bytes B"
}

# ─── Ana akis ────────────────────────────────────────────────────────────────
Write-Status "`n═══════════════════════════════════════"
Write-Status " JARVIS Memory Backup"
Write-Status "═══════════════════════════════════════"
Write-Status "Kok      : $JarvisRoot"
Write-Status "Yedek    : $BackupFile"
if ($DryRun) { Write-Status "[DRY-RUN] Hicbir sey yazilmayacak" -Color Yellow }
Write-Status ""

# Kok dogrulaması
if (-not (Test-Path $JarvisRoot)) {
    Write-Status "[HATA] JarvisRoot bulunamadi: $JarvisRoot" -Color Red
    exit 1
}

# Mevcut dosyalari topla
$FilesToBackup = @()
foreach ($rel in $IncludePaths) {
    $full = Join-Path $JarvisRoot $rel
    if (Test-Path $full) {
        $FilesToBackup += $full
        $size = if ((Get-Item $full).PSIsContainer) {
            (Get-ChildItem $full -Recurse -File | Measure-Object -Property Length -Sum).Sum
        } else {
            (Get-Item $full).Length
        }
        Write-Status ("  [EKLE]  {0,-40} {1}" -f $rel, (Get-HumanSize $size)) -Color Green
    } else {
        Write-Status ("  [YOK ]  {0}" -f $rel) -Color DarkGray
    }
}

if ($FilesToBackup.Count -eq 0) {
    Write-Status "[UYARI] Yedeklenecek dosya bulunamadi." -Color Yellow
    exit 0
}

Write-Status ""
Write-Status "Toplam $($FilesToBackup.Count) kaynak bulundu."

if ($DryRun) {
    Write-Status "`n[DRY-RUN] Gercek yedek alinmadi. -DryRun'u kaldirin." -Color Yellow
    exit 0
}

# Backups klasorü
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Write-Status "Klasor olusturuldu: $BackupDir"
}

# Zip olustur
Write-Status "`nYedek olusturuluyor..."
try {
    Compress-Archive -Path $FilesToBackup -DestinationPath $BackupFile -Force
    $zipSize = (Get-Item $BackupFile).Length
    Write-Status "[OK] Yedek olusturuldu: $BackupFile ($(Get-HumanSize $zipSize))" -Color Green
} catch {
    Write-Status "[HATA] Yedek olusturulamadi: $_" -Color Red
    exit 1
}

# Eski yedekleri temizle (son 5'i sakla)
$OldBackups = Get-ChildItem $BackupDir -Filter "jarvis_memory_backup_*.zip" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 5

if ($OldBackups) {
    Write-Status ""
    Write-Status "Eski yedekler temizleniyor ($($OldBackups.Count) adet)..."
    foreach ($old in $OldBackups) {
        Remove-Item $old.FullName -Force
        Write-Status "  [SILINDI] $($old.Name)" -Color DarkGray
    }
}

Write-Status ""
Write-Status "═══════════════════════════════════════"
Write-Status " Yedek tamamlandi: $Timestamp" -Color Green
Write-Status "═══════════════════════════════════════`n"

# .env asla yedeklenmedi - bunu acikca dogrula
$envPath = Join-Path $JarvisRoot ".env"
if (Test-Path $envPath) {
    Write-Status "[GUVENLIK] .env dosyasi yedege DAHIL EDILMEDI (secrets korundu)." -Color Yellow
}
