@echo off
chcp 65001 >nul
title JARVIS - Windows Hazırlık

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     JARVIS KURULUM - ADIM 1              ║
echo  ║     Python + VS Code + Araçlar           ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ---- Python kontrolü ----
echo [*] Python kontrol ediliyor...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [!] Python bulunamadı. İndiriliyor...
    curl -L -o python_installer.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo [*] Python kuruluyor... (PATH'e ekle seçeneğini işaretle!)
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
    del python_installer.exe
    echo [✓] Python kuruldu.
) ELSE (
    echo [✓] Python zaten kurulu.
    python --version
)

:: ---- Git kontrolü ----
echo.
echo [*] Git kontrol ediliyor...
git --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [!] Git bulunamadı. İndiriliyor...
    curl -L -o git_installer.exe https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe
    start /wait git_installer.exe /SILENT
    del git_installer.exe
    echo [✓] Git kuruldu.
) ELSE (
    echo [✓] Git zaten kurulu.
    git --version
)

:: ---- VS Code kontrolü ----
echo.
echo [*] VS Code kontrol ediliyor...
code --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [!] VS Code bulunamadı. İndiriliyor...
    curl -L -o vscode_installer.exe "https://code.visualstudio.com/sha/download?build=stable&os=win32-x64-user"
    start /wait vscode_installer.exe /SILENT /mergetasks=!runcode,addcontextmenufiles,addcontextmenufolders,associatewithfiles,addtopath
    del vscode_installer.exe
    echo [✓] VS Code kuruldu.
) ELSE (
    echo [✓] VS Code zaten kurulu.
)

:: ---- Ollama kurulumu ----
echo.
echo [*] Ollama kontrol ediliyor... (Bu JARVIS'in beyni!)
ollama --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [!] Ollama bulunamadı. İndiriliyor...
    curl -L -o ollama_installer.exe https://ollama.com/download/OllamaSetup.exe
    start /wait ollama_installer.exe /S
    del ollama_installer.exe
    echo [✓] Ollama kuruldu.
) ELSE (
    echo [✓] Ollama zaten kurulu.
    ollama --version
)

echo.
echo ══════════════════════════════════════════════
echo  [✓] ADIM 1 TAMAMLANDI!
echo  Şimdi 2_model_indir.bat çalıştırın.
echo ══════════════════════════════════════════════
echo.
pause
