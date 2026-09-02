@echo off
chcp 65001 >nul
title JARVIS - Model İndirme (RTX 3070 Optimize)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     JARVIS KURULUM - ADIM 2              ║
echo  ║     RTX 3070 için AI Model İndirme       ║
echo  ║     (8GB VRAM - Optimize Seçim)          ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  Sisteminiz için önerilen modeller:
echo  ──────────────────────────────────
echo  [1] mistral (7B) - Hızlı, günlük kullanım - 4GB VRAM
echo  [2] llama3.2 (3B) - Ultra hızlı, anlık sorular - 2GB VRAM  
echo  [3] llama3.1 (8B) - Daha zeki, biraz yavaş - 6GB VRAM
echo  [4] mixtral (8x7B) - En akıllı, yavaş - 8GB VRAM (sınırda)
echo  [5] HEPSİNİ indir (önerilen - zeki + hızlı kombinasyon)
echo.
set /p secim="Seçiminiz (1-5): "

IF "%secim%"=="1" GOTO MISTRAL
IF "%secim%"=="2" GOTO LLAMA_SMALL
IF "%secim%"=="3" GOTO LLAMA_BIG
IF "%secim%"=="4" GOTO MIXTRAL
IF "%secim%"=="5" GOTO HEPSI
GOTO MISTRAL

:MISTRAL
echo.
echo [*] Mistral 7B indiriliyor... (~4GB, yaklaşık 5 dakika)
ollama pull mistral
echo [✓] Mistral hazır!
GOTO BITTI

:LLAMA_SMALL
echo.
echo [*] Llama 3.2 (3B) indiriliyor... (~2GB, yaklaşık 3 dakika)
ollama pull llama3.2
echo [✓] Llama 3.2 hazır!
GOTO BITTI

:LLAMA_BIG
echo.
echo [*] Llama 3.1 (8B) indiriliyor... (~6GB, yaklaşık 8 dakika)
ollama pull llama3.1
echo [✓] Llama 3.1 hazır!
GOTO BITTI

:MIXTRAL
echo.
echo [*] Mixtral 8x7B indiriliyor... (~8GB, yaklaşık 10 dakika)
echo [!] UYARI: 8GB VRAM sınırında, yavaş çalışabilir!
ollama pull mixtral
echo [✓] Mixtral hazır!
GOTO BITTI

:HEPSI
echo.
echo [*] Mistral 7B indiriliyor... (Ana model)
ollama pull mistral
echo [✓] Mistral hazır!
echo.
echo [*] Llama 3.2 indiriliyor... (Hızlı sorular için)
ollama pull llama3.2
echo [✓] Llama 3.2 hazır!
echo.
echo [*] Llama 3.1 indiriliyor... (Derin analiz için)
ollama pull llama3.1
echo [✓] Llama 3.1 hazır!

:BITTI
echo.
echo [*] Model listesi:
ollama list
echo.
echo ══════════════════════════════════════════════
echo  [✓] ADIM 2 TAMAMLANDI!
echo  Şimdi 3_jarvis_kur.bat çalıştırın.
echo ══════════════════════════════════════════════
echo.
pause
