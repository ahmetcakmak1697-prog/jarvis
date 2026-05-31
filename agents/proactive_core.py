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
    def __init__(self, state_path: str = "memory/proactive_state.json", profile_path: str = "memory/user_profile.json"):
        self.state_path = Path(state_path)
        self.profile_path = Path(profile_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def build_state(self) -> dict:
        now = datetime.now()
        profile = self._load_profile()

        state = {
            "ok": True,
            "version": "B1.1",
            "ts": now.isoformat(timespec="seconds"),
            "date": now.date().isoformat(),
            "time": now.strftime("%H:%M"),
            "profile": self._profile_summary(profile),
            "briefing": self._briefing_stub(now, profile),
            "weather": self._weather_stub(profile),
            "music": self._music_stub(profile),
            "security": self._security_stub(),
            "system": self._system_stub(),
            "suggestion": self._suggestion_stub(now, profile),
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


    def _load_profile(self) -> dict:
        try:
            if not self.profile_path.exists():
                return {}
            data = json.loads(self.profile_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _profile_summary(self, profile: dict) -> dict:
        identity = profile.get("identity", {}) if isinstance(profile.get("identity"), dict) else {}
        location = profile.get("location_context", {}) if isinstance(profile.get("location_context"), dict) else {}
        briefing = profile.get("briefing", {}) if isinstance(profile.get("briefing"), dict) else {}
        proactive = profile.get("proactive_rules", {}) if isinstance(profile.get("proactive_rules"), dict) else {}

        return {
            "name": identity.get("full_name") or profile.get("name"),
            "city": location.get("city") or profile.get("city"),
            "district": location.get("district") or profile.get("district"),
            "neighborhood": location.get("neighborhood"),
            "briefing_mode": briefing.get("mode"),
            "briefing_time": briefing.get("time"),
            "briefing_format": proactive.get("briefing_format"),
            "profile_version": (profile.get("e1_meta") or {}).get("version") if isinstance(profile.get("e1_meta"), dict) else None,
        }

    def _address(self, profile: dict) -> str:
        identity = profile.get("identity", {}) if isinstance(profile.get("identity"), dict) else {}
        names = identity.get("preferred_names") or []
        if isinstance(names, list) and names:
            return str(names[0])
        return (profile.get("preferences") or {}).get("hitap", "efendim") if isinstance(profile.get("preferences"), dict) else "efendim"

    def _primary_project(self, profile: dict) -> str:
        projects = profile.get("current_projects") or []
        if isinstance(projects, list) and projects:
            return str(projects[0])

        work = profile.get("work_profile", {}) if isinstance(profile.get("work_profile"), dict) else {}
        work_projects = work.get("current_projects") or []
        if isinstance(work_projects, list) and work_projects:
            return str(work_projects[0])

        return "JARVIS yerel AI asistanı"

    def _briefing_stub(self, now: datetime, profile: dict | None = None) -> dict:
        profile = profile or {}
        hour = now.hour
        address = self._address(profile)
        project = self._primary_project(profile)

        if 5 <= hour < 12:
            tone = "morning"
            title = "Sabah brifingi"
            text = f"Günaydın {address}. Sistemler hazır; bugün ana odağı kısa tutalım: {project}."
        elif 12 <= hour < 18:
            tone = "day"
            title = "Gün ortası durumu"
            text = f"{address}, gün devam ediyor. Öncelikleri sade tutarsak verim yüksek kalır."
        else:
            tone = "evening"
            title = "Kapanış değerlendirmesi"
            text = f"{address}, kapanış için kısa kontrol iyi olur. Detay istersen başlıkları açarım."

        return {
            "title": title,
            "tone": tone,
            "text": text,
            "ready": True,
            "profile_aware": bool(profile),
            "project": project,
        }

    def _weather_stub(self, profile: dict | None = None) -> dict:
        profile = profile or {}
        location = profile.get("location_context", {}) if isinstance(profile.get("location_context"), dict) else {}
        city = location.get("city") or profile.get("city") or "İzmir"
        district = location.get("district") or profile.get("district")
        default_location = "/".join([x for x in [city, district] if x])

        return {
            "city": city,
            "district": district,
            "default_location": default_location,
            "status": "pending",
            "summary": "Hava durumu E1.4 aşamasında D2.4 cache/rate-limit korumasıyla gerçek veriye bağlanacak.",
            "temperature_c": None,
            "week": [],
            "profile_aware": bool(profile),
        }

    def _music_stub(self, profile: dict | None = None) -> dict:
        profile = profile or {}
        music = profile.get("music", {}) if isinstance(profile.get("music"), dict) else {}
        artists = music.get("artists_groups") or ["AC/DC"]

        artist = "AC/DC"
        if isinstance(artists, list) and artists:
            artist = "AC/DC" if "AC/DC" in artists else str(artists[0])

        track = "Shoot to Thrill" if artist == "AC/DC" else None

        return {
            "status": "local",
            "suggestion": {
                "artist": artist,
                "track": track,
                "reason": "Enerjiyi yükseltir; sistemi fazla dağıtmaz.",
            },
            "profile_aware": bool(profile),
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


    def _suggestion_stub(self, now: datetime, profile: dict | None = None) -> dict:
        profile = profile or {}
        project = self._primary_project(profile)
        proactive = profile.get("proactive_rules", {}) if isinstance(profile.get("proactive_rules"), dict) else {}
        briefing_format = proactive.get("briefing_format", "kısa")

        if now.hour < 12:
            return {
                "title": "Günün açılışı",
                "text": f"Önce sistem sağlığını, sonra {project} için bugünkü tek ana hedefi netleştirelim.",
                "action": "Sağlık Kontrolü",
                "briefing_format": briefing_format,
                "profile_aware": bool(profile),
            }

        if now.hour < 18:
            return {
                "title": "Odak önerisi",
                "text": "90 dakikalık tek bir blok, bugün en çok ilerleme sağlayacak alan olabilir.",
                "action": "Odak Modu",
                "briefing_format": briefing_format,
                "profile_aware": bool(profile),
            }

        return {
            "title": "Kapanış rutini",
            "text": "Günün kısa özetini ve bir sonraki adımı kaydetmek iyi olur.",
            "action": "Gün Özeti",
            "briefing_format": briefing_format,
            "profile_aware": bool(profile),
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
