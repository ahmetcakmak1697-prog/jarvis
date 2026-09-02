"""JARVIS v5 Setup — tek komutla kurulum."""
import sys
import subprocess
from pathlib import Path


def run(cmd, check=True):
    print(f"$ {cmd}")
    return subprocess.run(cmd, shell=True, check=check)


def step(n, msg):
    print(f"\n{'='*60}\n  ADIM {n}: {msg}\n{'='*60}")


def main():
    print("\n" + "="*60)
    print("  🤖 JARVIS v5 — OPERATION OVERMIND KURULUMU")
    print("="*60)

    step(1, "Klasörleri oluştur")
    for d in ["memory", "logs", "outputs", "uploads", "training",
              "logs/improvement_reports"]:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {d}/")

    step(2, "Python paketlerini kur")
    pip_cmd = (f'"{sys.executable}" -m pip install -r requirements.txt '
               f'--upgrade --quiet')
    run(pip_cmd, check=False)
    print("  ✓ Paketler kuruldu (faster-whisper hata verirse: opsiyonel)")

    step(3, "Ollama kontrol")
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        print(f"  ✓ Ollama çalışıyor")
        models = [m["name"] for m in r.json().get("models", [])]
        if "mistral-nemo:latest" not in models:
            print("  ⚠️  mistral-nemo yok. Çalıştır: ollama pull mistral-nemo")
        else:
            print(f"  ✓ mistral-nemo hazır")
    except:
        print("  ⚠️  Ollama erişilemedi. Başlat: ollama serve")

    step(4, "Format migration (eski veri varsa)")
    try:
        sys.path.insert(0, str(Path("training")))
        from training.migrate_format import migrate
        migrate()
    except Exception as e:
        print(f"  Migration: {e}")

    step(5, "Playwright (opsiyonel — browser agent)")
    print("  Çalıştır: python -m playwright install chromium")

    print("\n" + "="*60)
    print("  ✅ KURULUM TAMAM!")
    print("="*60)
    print("\n🚀 BAŞLAT:")
    print("   python auto_runner.py     (önerilen — 7/24 her şey)")
    print("\n   veya")
    print("   python jarvis_server.py   (sadece web server)")
    print("\n📊 DASHBOARD:")
    print("   python training/dashboard.py")
    print("\n🌐 ARAYÜZ: http://localhost:8000")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
