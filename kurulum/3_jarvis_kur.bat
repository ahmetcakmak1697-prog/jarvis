@echo off
chcp 65001 >nul
title JARVIS - Python Ortamı Kurulumu

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     JARVIS KURULUM - ADIM 3              ║
echo  ║     Python Ortamı + Kütüphaneler         ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Script'in bulunduğu klasörden bir üst dizine geç (jarvis klasörü)
cd /d "%~dp0.."
echo [*] Çalışma dizini: %CD%

:: ---- Virtual environment ----
echo.
echo [*] Python sanal ortam oluşturuluyor...
IF EXIST "venv" (
    echo [✓] Sanal ortam zaten var, atlanıyor.
) ELSE (
    python -m venv venv
    echo [✓] Sanal ortam oluşturuldu.
)

:: ---- Aktifleştir ----
echo [*] Sanal ortam aktifleştiriliyor...
call venv\Scripts\activate.bat

:: ---- Pip güncelle ----
echo [*] Pip güncelleniyor...
python -m pip install --upgrade pip --quiet

:: ---- Temel kütüphaneler ----
echo.
echo [*] Temel kütüphaneler kuruluyor...
pip install anthropic python-dotenv rich typer --quiet
echo [✓] Temel kütüphaneler tamam.

:: ---- Hafıza sistemi ----
echo [*] Hafıza sistemi kuruluyor...
pip install chromadb sentence-transformers --quiet
echo [✓] Hafıza sistemi tamam.

:: ---- Ollama Python client ----
echo [*] Ollama Python bağlantısı kuruluyor...
pip install ollama --quiet
echo [✓] Ollama client tamam.

:: ---- İnternet araçları ----
echo [*] İnternet erişim araçları kuruluyor...
pip install requests beautifulsoup4 duckduckgo-search --quiet
echo [✓] İnternet araçları tamam.

:: ---- Diğerleri ----
echo [*] Yardımcı araçlar kuruluyor...
pip install gitpython tiktoken pathspec schedule --quiet
echo [✓] Yardımcı araçlar tamam.

:: ---- .env dosyası ----
echo.
echo [*] Yapılandırma dosyası kontrol ediliyor...
IF NOT EXIST ".env" (
    echo # JARVIS Yapılandırma > .env
    echo JARVIS_NAME=Jarvis >> .env
    echo JARVIS_LANGUAGE=tr >> .env
    echo # Claude API (opsiyonel - lokal model kullanılacak) >> .env
    echo ANTHROPIC_API_KEY= >> .env
    echo # Lokal model ayarları >> .env
    echo LOCAL_MODEL=mistral >> .env
    echo USE_LOCAL_MODEL=true >> .env
    echo [✓] .env dosyası oluşturuldu.
) ELSE (
    echo [✓] .env dosyası zaten var.
)

echo.
echo ══════════════════════════════════════════════
echo  [✓] ADIM 3 TAMAMLANDI!
echo  Şimdi 4_baslat.bat ile Jarvis'i başlatın!
echo ══════════════════════════════════════════════
echo.
pause
