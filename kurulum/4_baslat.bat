@echo off
chcp 65001 >nul
title JARVIS - Başlatılıyor...

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║          J A R V I S                     ║
echo  ║     Lokal AI Sistemi Başlatılıyor        ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0.."

:: Ollama çalışıyor mu kontrol et
echo [*] Ollama servisi kontrol ediliyor...
ollama list >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [!] Ollama başlatılıyor...
    start /min "" ollama serve
    timeout /t 3 /nobreak >nul
    echo [✓] Ollama hazır.
) ELSE (
    echo [✓] Ollama çalışıyor.
)

:: Sanal ortamı aktifleştir
call venv\Scripts\activate.bat 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo [!] Sanal ortam bulunamadı! Önce 3_jarvis_kur.bat çalıştırın.
    pause
    exit
)

echo [✓] Ortam hazır. JARVIS başlatılıyor...
echo.

python main.py

pause
