"""
JARVIS Proactive Core
Central state builder for daily briefing, security, system, music and suggestions.

B1 goal:
- Never crash if optional modules fail.
- Produce one stable JSON-like dict for UI/API.
- Keep runtime state in memory/proactive_state.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime


class ProactiveCore:
    def __init__(self, state_path: str = "memory/proactive_state.json"):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def build_state(self) -> dict:
        now = datetime.now()

        state = {
            "ok": True,
            "version": "B1.1",
            "ts": now.isoformat(timespec="seconds"),
            "date": now.date().isoformat(),
            "time": now.strftime("%H:%M"),
            "briefing": self._briefing_stub(now),
            "weather": self._weather_stub(),
            "music": self._music_stub(),
            "security": self._security_stub(),
            "system": self._system_stub(),
            "suggestion": self._suggestion_stub(now),
            "tasks": self._tasks_stub(),
        }

        self._save_state(state)
        return state

    def latest(self) -> dict:
        if not self.state_path.exists():
            return self.build_state()

        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return self.build_state()
            return data
        except Exception:
            return self.build_state()

    def _save_state(self, state: dict) -> None:
        self.state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _briefing_stub(self, now: datetime) -> dict:
        hour = now.hour

        if 5 <= hour < 12:
            tone = "morning"
            title = "Sabah brifingi"
            text = "Günaydın efendim. Sistemler hazır; günün önceliklerini toparlamak için beklemedeyim."
        elif 12 <= hour < 18:
            tone = "day"
            title = "Gün ortası durumu"
            text = "Efendim, gün devam ediyor. Öncelikleri sade tutarsak sistem verimi yüksek kalır."
        else:
            tone = "evening"
            title = "Kapanış değerlendirmesi"
            text = "Efendim, günün kapanışı için kısa bir kontrol ve özet uygun görünüyor."

        return {
            "title": title,
            "tone": tone,
            "text": text,
            "ready": True,
        }

    def _weather_stub(self) -> dict:
        return {
            "city": "İzmir",
            "status": "pending",
            "summary": "Hava durumu modülü B1.2 aşamasında gerçek veriyle bağlanacak.",
            "temperature_c": None,
            "week": [],
        }

    def _music_stub(self) -> dict:
        return {
            "status": "local",
            "suggestion": {
                "artist": "AC/DC",
                "track": "Shoot to Thrill",
                "reason": "Enerjiyi yükseltir; sistemi fazla dağıtmaz.",
            },
        }


    def _security_stub(self) -> dict:
        try:
            from tools.security_snapshot import get_security_snapshot
            snap = get_security_snapshot()

            return {
                "level": snap.get("level", "normal"),
                "shield": snap.get("shield", "active"),
                "failed_login_24h": snap.get("failed_login_24h", 0),
                "failed_login_total": snap.get("failed_login_total", 0),
                "blocked_ips": snap.get("blocked_ips", 0),
                "blocked_ip_list": snap.get("blocked_ip_list", []),
                "active_sessions": snap.get("active_sessions", 0),
                "last_fail": snap.get("last_fail"),
                "last_external": snap.get("last_external"),
                "line": snap.get("line", "Koruma Kalkanı aktif."),
            }

        except Exception as e:
            return {
                "level": "unknown",
                "shield": "fallback",
                "failed_login_24h": 0,
                "failed_login_total": 0,
                "blocked_ips": 0,
                "blocked_ip_list": [],
                "active_sessions": 0,
                "last_fail": None,
                "last_external": None,
                "line": f"Koruma verisi alınamadı: {str(e)[:120]}",
            }



    def _system_stub(self) -> dict:
        try:
            from tools.system_intelligence import get_system_status, get_health_score

            status = get_system_status()
            health = get_health_score(status)

            cpu = status.get("cpu_percent", 0)
            ram = status.get("ram", {})
            disk = status.get("disk", {})
            gpu = status.get("gpu", {})

            line = (
                f"CPU %{cpu}, RAM %{ram.get('percent', 0)}, "
                f"Disk %{disk.get('percent', 0)}. "
                f"Sağlık: {health.get('label', 'Bilinmiyor')}."
            )

            if gpu.get("available"):
                line += (
                    f" GPU %{gpu.get('percent', 0)}, "
                    f"VRAM %{gpu.get('memory_percent', 0)}, "
                    f"Sıcaklık {gpu.get('temperature', '--')}°C."
                )
            else:
                line += " GPU bilgisi alınamadı."

            return {
                "health": health.get("level", "normal"),
                "health_score": health.get("score", 100),
                "health_label": health.get("label", "Stabil"),
                "health_note": health.get("threshold_note", ""),
                "cpu_percent": cpu,
                "ram_percent": ram.get("percent", 0),
                "ram_used_gb": ram.get("used_gb", 0),
                "ram_total_gb": ram.get("total_gb", 0),
                "disk_percent": disk.get("percent", 0),
                "disk_used_gb": disk.get("used_gb", 0),
                "disk_total_gb": disk.get("total_gb", 0),
                "gpu": gpu,
                "model": "mistral-nemo:latest",
                "local_core": "online",
                "line": line,
            }

        except Exception as e:
            return {
                "health": "unknown",
                "health_score": 0,
                "health_label": "Bilinmiyor",
                "health_note": "Sistem verisi okunamadı.",
                "model": "mistral-nemo:latest",
                "local_core": "fallback",
                "line": f"Sistem verisi alınamadı: {str(e)[:120]}",
            }


    def _suggestion_stub(self, now: datetime) -> dict:
        if now.hour < 12:
            return {
                "title": "Günün açılışı",
                "text": "Önce sistem sağlığını, sonra bugünkü ana hedefi netleştirelim.",
                "action": "Sağlık Kontrolü",
            }

        if now.hour < 18:
            return {
                "title": "Odak önerisi",
                "text": "90 dakikalık tek bir blok, bugün en çok ilerleme sağlayacak alan olabilir.",
                "action": "Odak Modu",
            }

        return {
            "title": "Kapanış rutini",
            "text": "Günün kısa özetini ve bir sonraki adımı kaydetmek iyi olur.",
            "action": "Gün Özeti",
        }


    def _tasks_stub(self) -> dict:
        try:
            from tools.task_snapshot import get_task_snapshot
            snap = get_task_snapshot()

            return {
                "pending": snap.get("pending", 0),
                "running": snap.get("running", 0),
                "completed": snap.get("completed", 0),
                "failed": snap.get("failed", 0),
                "recent": snap.get("recent", []),
                "line": snap.get("line", "Görev durumu okunamadı."),
            }

        except Exception as e:
            return {
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "recent": [],
                "line": f"Görev verisi alınamadı: {str(e)[:120]}",
            }



if __name__ == "__main__":
    core = ProactiveCore()
    print(json.dumps(core.build_state(), ensure_ascii=False, indent=2))
