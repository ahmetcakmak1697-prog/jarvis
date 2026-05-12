"""
JARVIS SNAPSHOT v3 - UTF-8 zorlu, garanti calisir
Kullanim: python jarvis_snapshot.py > snapshot.txt
"""
import sys, io
# !!! Windows cp1254 cehennemini cozer
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import os, subprocess, platform
from pathlib import Path
from datetime import datetime

def bolum(ad):
    print()
    print("=" * 70)
    print(f"  {ad}")
    print("=" * 70)

def calistir(komut):
    try:
        sonuc = subprocess.run(komut, shell=True, capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=15)
        return (sonuc.stdout or "") + (sonuc.stderr if sonuc.returncode != 0 else "")
    except Exception as e:
        return f"HATA: {e}"

def yaz(metin):
    try:
        print(metin)
    except Exception:
        try:
            print(str(metin).encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        except Exception:
            print("[yazilamadi]")

# 1. SISTEM
bolum("1. SISTEM")
yaz(f"Tarih: {datetime.now()}")
yaz(f"Python: {sys.version.split()[0]}")
yaz(f"Platform: {platform.platform()}")
yaz(f"Islemci: {platform.processor()}")

# 2. RAM
bolum("2. RAM")
try:
    import psutil
    ram = psutil.virtual_memory()
    yaz(f"Toplam: {ram.total / (1024**3):.1f} GB")
    yaz(f"Bos: {ram.available / (1024**3):.1f} GB")
    yaz(f"Kullanim: %{ram.percent}")
except ImportError:
    yaz("psutil yok")

# 3. GPU
bolum("3. GPU")
yaz(calistir("nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu --format=csv"))

# 4. DISK
bolum("4. DISK")
try:
    import psutil
    for disk in psutil.disk_partitions():
        try:
            k = psutil.disk_usage(disk.mountpoint)
            yaz(f"{disk.device}  {k.used/(1024**3):.1f}/{k.total/(1024**3):.1f} GB  (bos: {k.free/(1024**3):.1f} GB)")
        except: pass
except: pass

# 5. OLLAMA
bolum("5. OLLAMA MODELLERI")
yaz(calistir("ollama list"))

# 6. KLASOR YAPISI
bolum("6. JARVIS KLASOR YAPISI")
haric = {"venv", "__pycache__", ".git", "node_modules", ".vscode"}
def listele(p, derinlik=0, maks=2):
    if derinlik > maks: return
    try:
        for c in sorted(p.iterdir()):
            if c.name in haric: continue
            girinti = "  " * derinlik
            try:
                if c.is_dir():
                    yaz(f"{girinti}[DIR] {c.name}/")
                    listele(c, derinlik+1, maks)
                else:
                    yaz(f"{girinti}  {c.name}  ({c.stat().st_size/1024:.1f} KB)")
            except: pass
    except: pass
listele(Path("."))

# 7. KLASOR BOYUTLARI
bolum("7. KLASOR BOYUTLARI")
for klasor in ["memory", "rag", "data", "logs", "outputs", "training", "eval", "agents", "tools", "voice", "mcp"]:
    p = Path(klasor)
    if p.exists():
        try:
            toplam = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            sayi = sum(1 for f in p.rglob("*") if f.is_file())
            yaz(f"{klasor}/  -> {toplam/(1024**2):.2f} MB  ({sayi} dosya)")
        except: pass

# 8. PYTHON DOSYALARI
bolum("8. PYTHON DOSYALARI (50+ satir)")
py_dosyalar = [p for p in Path(".").rglob("*.py") if not any(x in str(p) for x in ["venv", "__pycache__"])]
toplam_satir = 0
for f in py_dosyalar:
    try:
        satir = len(f.read_text(encoding='utf-8', errors='ignore').splitlines())
        toplam_satir += satir
        if satir > 50:
            yaz(f"{satir:5d} satir  {f}")
    except: pass
yaz(f"\nTOPLAM: {len(py_dosyalar)} dosya, {toplam_satir} satir")

# 9. PORTLAR
bolum("9. PORTLAR")
try:
    import psutil
    ilgi = {8000, 11434, 4040, 7860, 5000, 8501, 8888, 3000}
    for c in psutil.net_connections(kind='inet'):
        if c.status == 'LISTEN' and c.laddr.port in ilgi:
            try:
                p = psutil.Process(c.pid).name() if c.pid else "?"
            except: p = "?"
            yaz(f"Port {c.laddr.port} -> {p} (PID {c.pid})")
except Exception as e:
    yaz(f"Hata: {e}")

# 10. PIP
bolum("10. PIP PAKETLER (ilgili)")
ilgili = ["ollama", "chromadb", "sentence", "fastapi", "uvicorn", "openai", "anthropic", "torch", "transformers", "psutil", "langchain", "bge", "serper", "minimax"]
out = calistir(f'"{sys.executable}" -m pip list')
for satir in out.splitlines():
    for k in ilgili:
        if k.lower() in satir.lower():
            yaz(satir); break

# 11. .ENV
bolum("11. .ENV (maskelendi)")
env = Path(".env")
if env.exists():
    try:
        for satir in env.read_text(encoding='utf-8', errors='ignore').splitlines():
            if not satir.strip() or satir.startswith("#"):
                yaz(satir); continue
            if "=" in satir:
                k, _, v = satir.partition("=")
                yaz(f"{k}={v[:3]}***GIZLI" if len(v) > 6 else f"{k}=***")
    except: pass

# 12. SON LOGLAR
bolum("12. SON LOGLAR")
log = Path("logs")
if log.exists():
    loglar = sorted(log.rglob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
    for l in loglar:
        yaz(f"--- {l.name} ---")
        try:
            satirlar = l.read_text(encoding='utf-8', errors='ignore').splitlines()
            for s in satirlar[-15:]:
                yaz(s)
        except Exception as e:
            yaz(f"  okunamadi: {e}")

bolum("SNAPSHOT BITTI")
yaz(f"Tarih: {datetime.now()}")