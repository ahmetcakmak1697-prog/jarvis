"""JARVIS Auto Runner — 24/7 background orchestrator.
Tek komut: python auto_runner.py
- Server'ı başlatır
- Gece curation (02:00)
- Sabah brifing (08:00)
- Akşam özeti (22:00)
- Saatlik self-improvement
- Health monitor (5 dak)
"""
import sys
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime
import requests

def log(msg):
    Path("logs").mkdir(exist_ok=True)
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open("logs/auto_runner.log", "a", encoding='utf-8') as f:
        f.write(line + "\n")

def is_server_up():
    try:
        r = requests.get("http://localhost:8000/status", timeout=3)
        return r.status_code == 200
    except:
        return False

def is_ollama_up():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except:
        return False

def start_server():
    log("🚀 Server başlatılıyor...")
    return subprocess.Popen(
        [sys.executable, "jarvis_server.py"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def health_monitor(server_proc):
    """5 dakikada bir sağlık kontrolü"""
    while True:
        time.sleep(300)
        if not is_ollama_up():
            log("❌ Ollama down — restart manuel: ollama serve")
        if not is_server_up():
            log("❌ Server down — yeniden başlatılıyor")
            try:
                server_proc.terminate()
            except:
                pass
            server_proc = start_server()
        else:
            log("💚 Health OK")

def schedule_jobs():
    try:
        import schedule
    except ImportError:
        log("schedule yok — pip install schedule")
        return

    def digest_job():
        log("🌅 Daily Digest...")
        try:
            from agents.daily_digest import DailyDigest
            d = DailyDigest()
            r = d.generate()
            log(f"✅ Digest: {r.get('content', '')[:120]}")
        except Exception as e:
            log(f"❌ Digest: {e}")

    def cleanup_job():
        log("🧹 Memory Cleanup...")
        try:
            from agents.memory_scorer import MemoryScorer
            s = MemoryScorer()
            n = s.cleanup_old(days=30)
            log(f"✅ Temizlendi: {n} eski hafıza silindi")
        except Exception as e:
            log(f"❌ Cleanup: {e}")

    def curate_job():
        log("🌙 Curation başlıyor...")
        try:
            from training.data_curator import run_once
            run_once(verbose=False)
            log("✅ Curation tamam")
        except Exception as e:
            log(f"❌ Curation: {e}")

    def morning_job():
        log("🌅 Sabah brifingi...")
        try:
            r = requests.get("http://localhost:8000/briefing/morning", timeout=120)
            log(f"✅ Brifing: {r.json().get('briefing', '')[:100]}")
        except Exception as e:
            log(f"❌ Brifing: {e}")

    def evening_job():
        log("🌙 Akşam özeti...")
        try:
            r = requests.get("http://localhost:8000/briefing/evening", timeout=120)
            log(f"✅ Özet: {r.json().get('briefing', '')[:100]}")
        except Exception as e:
            log(f"❌ Özet: {e}")

    def improvement_job():
        log("🔍 Self-improvement...")
        try:
            from agents.self_improver import SelfImprover
            r = SelfImprover().analyze_weaknesses()
            log(f"✅ Improvement: {r.get('status', 'done')}")
        except Exception as e:
            log(f"❌ Improvement: {e}")

    def summary_job():
        log("📝 Günlük özet...")
        try:
            from training.conversation_summarizer import summarize_day
            summarize_day()
            log("✅ Özet tamam")
        except Exception as e:
            log(f"❌ Özet: {e}")

    # Zamanlamalar
    schedule.every().day.at("02:00").do(curate_job)
    schedule.every().day.at("08:00").do(morning_job)
    schedule.every().day.at("08:05").do(digest_job)
    schedule.every().monday.at("03:00").do(cleanup_job)
    schedule.every().day.at("22:00").do(evening_job)
    schedule.every().day.at("23:00").do(summary_job)
    schedule.every(2).hours.do(improvement_job)

    log("📅 Scheduler aktif:")
    log("   • 02:00 curation")
    log("   • 08:00 sabah brifing")
    log("   • 08:05 daily digest 🌅")
    log("   • 22:00 akşam özeti")
    log("   • 23:00 günlük özet")
    log("   • Her 2 saat: self-improvement")
    log("   • Pazartesi 03:00: memory cleanup 🧹")

    while True:
        schedule.run_pending()
        time.sleep(30)

def main():
    log("="*60)
    log("🤖 JARVIS AUTO RUNNER — OPERATION OVERMIND")
    log("="*60)
    if not is_ollama_up():
        log("⚠️  Ollama çalışmıyor — Ollama'yı başlat: ollama serve")
        log("   Server yine de başlayacak")
    
    if is_server_up():
        log("⚠️  Server zaten çalışıyor — yeni instance başlatılmadı")
        server_proc = None
    else:
        server_proc = start_server()
        time.sleep(8)
        
    threading.Thread(target=schedule_jobs, daemon=True).start()
    
    if server_proc:
        threading.Thread(target=health_monitor, args=(server_proc,), daemon=True).start()
        
    log("✅ Auto Runner aktif — Ctrl+C ile durdur")
    log("="*60)
    
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log("⏹  Durduruluyor...")
        if server_proc:
            try:
                server_proc.terminate()
            except:
                pass

if __name__ == "__main__":
    main()