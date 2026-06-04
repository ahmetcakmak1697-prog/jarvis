"""JARVIS Auto Runner - 24/7 background orchestrator.

Tek komut:
    python auto_runner.py

Gorevler:
- JARVIS server calismiyorsa baslatir
- /healthz ile server sagligini izler
- Ollama durumunu kontrol eder
- Saatlik self-improvement dener
- Loglari logs/auto_runner.log dosyasina yazar
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests


SERVER_URL = "http://127.0.0.1:8000"
HEALTH_URL = f"{SERVER_URL}/healthz"
OLLAMA_URL = "http://127.0.0.1:11434/api/tags"
LOG_PATH = Path("logs/auto_runner.log")


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_server_up() -> bool:
    try:
        response = requests.get(HEALTH_URL, timeout=3)
        if response.status_code != 200:
            return False
        data = response.json()
        return bool(data.get("ok"))
    except Exception:
        return False


def is_ollama_up() -> bool:
    try:
        response = requests.get(OLLAMA_URL, timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def start_server() -> subprocess.Popen:
    log("Server baslatiliyor...")
    return subprocess.Popen(
        [sys.executable, "jarvis_server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def run_self_improvement() -> None:
    if not is_ollama_up():
        log("Ollama calismiyor. Self-improvement atlandi.")
        return

    try:
        from agents.self_improver import SelfImprover

        result = SelfImprover().analyze_weaknesses()
        status = result.get("status", "done") if isinstance(result, dict) else "done"
        log(f"Self-improvement tamamlandi: {status}")
    except Exception as exc:
        log(f"Self-improvement hata verdi: {str(exc)[:160]}")


def schedule_jobs(stop_event: threading.Event) -> None:
    """Basit zamanlayici.

    Su an bilincli olarak sade tutuldu:
    - Saatlik self-improvement
    - Ileride sabah brifingi / aksam ozeti buraya eklenecek
    """
    last_improvement_hour: Optional[str] = None

    while not stop_event.is_set():
        now = datetime.now()
        current_hour = now.strftime("%Y-%m-%d %H")

        if current_hour != last_improvement_hour:
            last_improvement_hour = current_hour
            run_self_improvement()

        stop_event.wait(60)


def health_monitor(server_proc: Optional[subprocess.Popen], stop_event: threading.Event) -> None:
    """5 dakikada bir server sagligini kontrol eder."""
    while not stop_event.is_set():
        if not is_server_up():
            log("Server healthz yanit vermiyor.")

            if server_proc and server_proc.poll() is None:
                log("Server process hala calisiyor gorunuyor; yeniden baslatilmadi.")
            else:
                log("Server process kapali. Yeniden baslatiliyor.")
                server_proc = start_server()
                time.sleep(8)
        else:
            log("Server saglik kontrolu OK.")

        stop_event.wait(300)


def main() -> None:
    log("=" * 60)
    log("JARVIS Auto Runner baslatildi.")

    server_proc: Optional[subprocess.Popen]

    if is_server_up():
        log("Server zaten calisiyor. Yeni instance baslatilmadi.")
        server_proc = None
    else:
        server_proc = start_server()
        time.sleep(8)

        if is_server_up():
            log("Server baslatildi ve healthz OK.")
        else:
            log("Server baslatildi ama healthz henuz OK donmedi.")

    stop_event = threading.Event()

    threading.Thread(target=schedule_jobs, args=(stop_event,), daemon=True).start()
    threading.Thread(target=health_monitor, args=(server_proc, stop_event), daemon=True).start()

    log("Auto Runner aktif. Durdurmak icin Ctrl+C.")
    log("=" * 60)

    try:
        while not stop_event.is_set():
            stop_event.wait(3600)
    except KeyboardInterrupt:
        log("Durdurma sinyali alindi.")
        stop_event.set()

        if server_proc and server_proc.poll() is None:
            try:
                server_proc.terminate()
                log("Server process sonlandirildi.")
            except Exception as exc:
                log(f"Server sonlandirilirken hata: {str(exc)[:160]}")

        log("Auto Runner durduruldu.")


if __name__ == "__main__":
    main()
