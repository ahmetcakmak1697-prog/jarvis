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
        return {
            "level": "normal",
            "shield": "active",
            "failed_login_24h": 0,
            "blocked_ips": 0,
            "line": "Koruma Kalkanı aktif. Olağan dışı bir hareket saptanmadı.",
        }

    def _system_stub(self) -> dict:
        return {
            "health": "stable",
            "model": "mistral-nemo:latest",
            "local_core": "standby",
            "line": "Yerel çekirdek beklemede.",
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
        return {
            "pending": 0,
            "completed": 0,
            "failed": 0,
            "running": False,
        }


if __name__ == "__main__":
    core = ProactiveCore()
    print(json.dumps(core.build_state(), ensure_ascii=False, indent=2))
