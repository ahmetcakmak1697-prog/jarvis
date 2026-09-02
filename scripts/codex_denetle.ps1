# codex_denetle.ps1 -- Codex'i DENETCI rolunde calistirir.
#
#   .\scripts\codex_denetle.ps1                 # commit edilmemis degisiklikleri denetle
#   .\scripts\codex_denetle.ps1 -Commit <sha>   # belirli bir commit'i denetle
#   .\scripts\codex_denetle.ps1 -Base main      # bir dala gore denetle
#
# NEDEN BU SCRIPT VAR: Ahmet'i "Claude'un diff'ini kopyalayip Codex'e yapistiran
# kopru" olmaktan cikarmak icin. Talimat metni dosyada duruyor
# (automation/CODEX_REVIEW_TALIMATI.md), Ahmet 26.08'de onayladi.
#
# ONEMLI -- POWERSHELL ZORUNLU:
# Bu script Bash/MSYS altinda CALISTIRILMAZ. ESP-IDF ve bazi arac zincirleri
# MSYS'te sessizce basarisiz oluyor (24.08'de esphome derlemesi bu yuzden
# "basarili" deyip hic .bin uretmedi). Ayni tuzaga dusmemek icin kural:
# derleme/denetim komutlari daima PowerShell.
#
# CIKIS KODLARI (otonom dongu bunlari okur):
#   0 = PASS
#   1 = CONCERN
#   2 = BLOCKER
#   3 = verdict metinden okunamadi (Codex calisti ama karar yazmadi)
#   4 = denetlenecek degisiklik yok (DIKKAT: bu PASS DEGILDIR)
#   5 = codex calistirilamadi (kimlik/ag/arguman hatasi)

param(
    [string]$Commit = "",
    [string]$Base = "",
    [switch]$Sessiz    # ciktiyi sadece dosyaya yaz, ekrana basma
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "codex_verdict.ps1")

$talimatYolu = Join-Path $repo "automation\CODEX_REVIEW_TALIMATI.md"

if (-not (Test-Path $talimatYolu)) {
    Write-Error "Denetci talimati bulunamadi: $talimatYolu"
    exit 5
}

$talimat = Get-Content $talimatYolu -Raw -Encoding UTF8

# Hedef secimi.
# DIKKAT: codex CLI, ozel talimat (PROMPT) ile kapsam bayragini (--uncommitted,
# --base, --commit) AYNI ANDA kabul etmiyor:
#   "error: the argument --uncommitted cannot be used with [PROMPT]"
# (0.150.0'da da boyle -- `codex review --help` ile dogrulandi 27.08.)
# Bu yuzden kapsam, talimatin ICINE cumle olarak yaziliyor.
$argListesi = @("review")
if ($Commit) {
    $kapsamCumlesi = "Incelenecek kapsam: $Commit commitinin getirdigi degisiklikler."
    $hedef = "commit $Commit"
} elseif ($Base) {
    $kapsamCumlesi = "Incelenecek kapsam: $Base dalina gore olan degisiklikler."
    $hedef = "base $Base"
} else {
    $kapsamCumlesi = "Incelenecek kapsam: calisma agacindaki commit edilmemis degisiklikler (staged, unstaged ve untracked dosyalar dahil)."
    $hedef = "commit edilmemis degisiklikler"
}

# Talimat stdin'den veriliyor ("-" argumani), boylece uzun metin komut
# satirinda kacis sorunu yaratmiyor.
$argListesi += "-"

$zaman = Get-Date -Format "yyyy-MM-dd_HHmmss"
$ciktiYolu = Join-Path $repo "automation\codex_denetim_$zaman.txt"

Write-Host "=== CODEX DENETIMI ===" -ForegroundColor Cyan
Write-Host "Hedef : $hedef"
Write-Host "Cikti : $ciktiYolu"
Write-Host ""

# Denetlenecek bir sey var mi? Yoksa Codex'i bosuna calistirma.
# Ayri cikis kodu (4) kullaniliyor: "hic bakilmadi" ile "bakildi, temiz cikti"
# ayni sey degil. 0 donmek otonom dongude sahte PASS kaydi uretirdi.
if (-not $Commit -and -not $Base) {
    $degisiklik = git -C $repo status --porcelain
    if (-not $degisiklik) {
        Write-Host "Calisma agaci temiz -- denetlenecek degisiklik yok." -ForegroundColor Yellow
        exit 4
    }
}

$tamTalimat = $kapsamCumlesi + "`n`n" + $talimat

# NEDEN ErrorActionPreference gecici olarak gevsetiliyor:
# PowerShell 5.1'de bir NATIVE exe'nin stderr'ini 2>&1 ile birlestirmek her
# satiri ErrorRecord'a sarar (NativeCommandError). $ErrorActionPreference="Stop"
# altinda bu TERMINATING hataya donusur ve script, cikti dosyasi yazilmadan
# olur. 26-27.08 gecesi iki denetim tam olarak burada oldu: ekrana yalnizca
# baslik basildi, codex_denetim_*.txt hic olusmadi.
$oncekiEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$ham = $tamTalimat | & codex @argListesi 2>&1
$codexKod = $LASTEXITCODE
$ErrorActionPreference = $oncekiEAP

# ErrorRecord nesnelerini duz metne cevir; yoksa dosyaya nesne adi yazilir.
$sonuc = $ham | ForEach-Object {
    if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { $_ }
}

# BOM'suz UTF-8 yaz. Out-File -Encoding UTF8 PS 5.1'de BOM ekler; bu depoda
# BOM daha once Turkce icerikte sorun cikardi (CLAUDE.md bolum 5).
$metinDosya = ($sonuc | Out-String)
[System.IO.File]::WriteAllText($ciktiYolu, $metinDosya, (New-Object System.Text.UTF8Encoding($false)))

if (-not $Sessiz) { $sonuc | Write-Host }

# --- VERDICT COZUMLEME ---
# Mantik ayri dosyada (scripts/codex_verdict.ps1) cunku otonom dongunun kapisi
# burasi ve test edilebilir olmasi gerekiyor: tests/test_codex_verdict.py
# GERCEK fonksiyonu cagirip dogruluyor, kopyasini degil.
$verdict = Get-CodexVerdict -Cikti ($sonuc -join "`n") -YankilananTalimat $tamTalimat

# Codex hic calismadiysa metin cozumlemesine guvenme.
if ($verdict -eq "BELIRSIZ" -and $codexKod -ne 0) {
    Write-Host ""
    Write-Host "codex calistirilamadi (cikis kodu $codexKod). Ayrinti: $ciktiYolu" -ForegroundColor Red
    exit 5
}

Write-Host ""
Write-Host "=== VERDICT: $verdict ===" -ForegroundColor $(
    switch ($verdict) { "PASS" { "Green" } "CONCERN" { "Yellow" } "BLOCKER" { "Red" } default { "Gray" } }
)

switch ($verdict) {
    "PASS"    { exit 0 }
    "CONCERN" { exit 1 }
    "BLOCKER" { exit 2 }
    default   { exit 3 }
}
