$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvActivate = Join-Path $Root "venv\Scripts\Activate.ps1"

if (!(Test-Path $VenvActivate)) {
    Write-Host "[HATA] venv bulunamadi: $VenvActivate" -ForegroundColor Red
    exit 1
}

Write-Host "[JARVIS] Remote stack baslatiliyor..." -ForegroundColor Cyan
Write-Host "[JARVIS] Root: $Root" -ForegroundColor DarkCyan

$ServerCmd = @"
cd `"$Root`"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
. `"$VenvActivate`"
python .\jarvis_server.py
"@

$TelegramCmd = @"
cd `"$Root`"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
. `"$VenvActivate`"
python .\tools\telegram_agent.py
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $ServerCmd
Start-Sleep -Seconds 3
Start-Process powershell -ArgumentList "-NoExit", "-Command", $TelegramCmd

Write-Host "[OK] JARVIS server ve Telegram agent ayri terminallerde baslatildi." -ForegroundColor Green
Write-Host "[WEB] Local:     http://localhost:8000" -ForegroundColor Yellow
Write-Host "[WEB] Tailscale: http://100.79.65.38:8000" -ForegroundColor Yellow
Write-Host "[BOT] Telegram bot terminalini acik birak." -ForegroundColor Yellow
