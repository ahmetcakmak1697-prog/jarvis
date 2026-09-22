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

:: Sanal ortamı aktifleştir. İki isim de destekleniyor: ana depo "venv",
:: çalışma ağaçları ".venv" kullanıyor. Eskiden yalnız "venv" aranıyordu ve
:: çalışma ağacında başlatıcı sessizce yanlış Python'a düşüyordu.
set "JARVIS_VENV="
IF EXIST ".venv\Scripts\activate.bat" set "JARVIS_VENV=.venv"
IF NOT DEFINED JARVIS_VENV IF EXIST "venv\Scripts\activate.bat" set "JARVIS_VENV=venv"
IF NOT DEFINED JARVIS_VENV (
    echo [!] Sanal ortam bulunamadı! Önce 3_jarvis_kur.bat çalıştırın.
    pause
    exit
)
call "%JARVIS_VENV%\Scripts\activate.bat"
echo [✓] Ortam hazır (%JARVIS_VENV%).

:: ── SES ONAYI ─────────────────────────────────────────────────────────
:: Ahmet'in kararı, 22.09.2026: Edge TTS açık.
:: Bu bir veri-çıkışı onayıdır (CLAUDE.md §7): seslendirilen her cümle
:: Microsoft'un bulut servisine gider. Hassas içerik zaten gitmez --
:: voice_loop.say() sentezden ÖNCE sınıflandırır ve hassassa ekranda
:: bırakır; sınıflandırma hata verirse de göndermez.
:: GERİ ALMAK İÇİN: aşağıdaki iki satırı başına "rem " koyarak kapat.
set JARVIS_J0_EDGE_TTS_ENABLED=1
set JARVIS_VOICE=1
:: Akış varsayılan olarak AÇIK. Eski tek-parça davranışa dönmek için:
::   set JARVIS_STREAM=0
:: ──────────────────────────────────────────────────────────────────────

echo [✓] Ses açık, akış açık. JARVIS başlatılıyor...
echo.

python main.py

pause
