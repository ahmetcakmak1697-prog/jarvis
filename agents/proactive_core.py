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

        state["proactive"] = self._proactive_stub(now, profile, state)

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


    def _time_to_minutes(self, value: str) -> int | None:
        try:
            if not isinstance(value, str) or ":" not in value:
                return None
            hh, mm = value.split(":", 1)
            return int(hh) * 60 + int(mm)
        except Exception:
            return None

    def _is_weekend(self, now: datetime) -> bool:
        return now.weekday() >= 5

    def _is_late_clock_time(self, now_minutes: int, threshold_minutes: int | None) -> bool:
        if threshold_minutes is None:
            return False

        # 00:00-06:00 aral???ndaki e?ikler gece yar?s?ndan sonraki pencereyi ifade eder.
        # ?rn. 01:00 e?i?i ??len 12:00'de de?il, sadece 01:00-06:00 aras?nda tetiklenmelidir.
        if threshold_minutes < 6 * 60:
            return threshold_minutes <= now_minutes < 6 * 60

        return now_minutes >= threshold_minutes

    def _is_late_warning_window(self, now_minutes: int, final_warning: int | None, hard_after: int | None) -> bool:
        if final_warning is None:
            return False

        # 23:30 sonras? uyar?.
        if now_minutes >= final_warning:
            return True

        # 00:00-01:00 aras? h?l? ?nceki gecenin final uyar? penceresi say?l?r.
        if hard_after is not None and hard_after < 6 * 60 and now_minutes < hard_after:
            return True

        return False

    def _alert(self, level: str, code: str, title: str, text: str, action: str | None = None, interrupt: bool = False) -> dict:
        item = {
            "level": level,
            "code": code,
            "title": title,
            "text": text,
            "interrupt": bool(interrupt),
        }
        if action:
            item["action"] = action
        return item

    def _proactive_stub(self, now: datetime, profile: dict, state: dict) -> dict:
        alerts = []

        proactive_rules = profile.get("proactive_rules", {}) if isinstance(profile.get("proactive_rules"), dict) else {}
        night = profile.get("night_warnings", {}) if isinstance(profile.get("night_warnings"), dict) else {}

        dnd = proactive_rules.get("do_not_disturb", {}) if isinstance(proactive_rules.get("do_not_disturb"), dict) else {}
        critical = proactive_rules.get("critical_thresholds", {}) if isinstance(proactive_rules.get("critical_thresholds"), dict) else {}

        now_minutes = now.hour * 60 + now.minute
        weekend = self._is_weekend(now)

        # 1) Gece çalışma uyarısı — sessiz, sadece state kararı.
        if weekend:
            late_after = self._time_to_minutes(critical.get("weekend_late_night_after", "02:30"))
            if self._is_late_clock_time(now_minutes, late_after):
                alerts.append(self._alert(
                    "warning",
                    "late_night_weekend",
                    "Gece çalışma uyarısı",
                    "Saat ilerledi. Tatil esnekliği var ama uyku borcu yine borçtur.",
                    "Checkpoint alıp kısa devam et veya kapat.",
                    interrupt=False,
                ))
        else:
            final_warning = self._time_to_minutes(night.get("workday_final_warning", "23:30"))
            hard_after = self._time_to_minutes(critical.get("weekday_late_night_after", "01:00"))

            if self._is_late_clock_time(now_minutes, hard_after):
                alerts.append(self._alert(
                    "critical",
                    "late_night_workday_critical",
                    "Kritik gece uyarısı",
                    "Yarın mesai varsa bu saatten sonra hata riski ciddi artar.",
                    "İşi durdur, checkpoint al ve kapat.",
                    interrupt=True,
                ))
            elif self._is_late_warning_window(now_minutes, final_warning, hard_after):
                alerts.append(self._alert(
                    "warning",
                    "late_night_workday",
                    "Gece çalışma uyarısı",
                    "Mesai gününde geç saate girdik. Hata yapmadan kapatmak daha akıllıca olabilir.",
                    "Checkpoint alıp sonlandırmayı değerlendir.",
                    interrupt=False,
                ))

        # 2) Sistem sağlığı eşikleri.
        system = state.get("system", {}) if isinstance(state.get("system"), dict) else {}
        health_score = system.get("health_score")

        try:
            health_score_num = float(health_score)
        except Exception:
            health_score_num = None

        if health_score_num is not None:
            if health_score_num <= float(critical.get("system_health_critical_below", 50)):
                alerts.append(self._alert(
                    "critical",
                    "system_health_critical",
                    "Sistem sağlığı kritik",
                    f"Sistem sağlık skoru {health_score_num:.0f}. Yükü azaltmak gerekebilir.",
                    "Ağır işlemleri durdur ve sistem durumunu kontrol et.",
                    interrupt=True,
                ))
            elif health_score_num <= float(critical.get("system_health_below", 75)):
                alerts.append(self._alert(
                    "warning",
                    "system_health_warning",
                    "Sistem sağlığı düşüyor",
                    f"Sistem sağlık skoru {health_score_num:.0f}. İzlemeye almak iyi olur.",
                    "CPU/RAM/GPU kullanımını kontrol et.",
                    interrupt=False,
                ))

        disk_percent = system.get("disk_percent")
        ram_percent = system.get("ram_percent")

        try:
            if disk_percent is not None and float(disk_percent) >= float(critical.get("disk_percent_above", 85)):
                alerts.append(self._alert(
                    "warning",
                    "disk_usage_high",
                    "Disk kullanımı yüksek",
                    f"Disk kullanımı %{float(disk_percent):.0f}.",
                    "Gereksiz snapshot/cache dosyalarını kontrol et.",
                    interrupt=False,
                ))
        except Exception:
            pass

        try:
            if ram_percent is not None and float(ram_percent) >= float(critical.get("ram_percent_above", 90)):
                alerts.append(self._alert(
                    "warning",
                    "ram_usage_high",
                    "RAM kullanımı yüksek",
                    f"RAM kullanımı %{float(ram_percent):.0f}.",
                    "Açık işlemleri ve model yükünü kontrol et.",
                    interrupt=False,
                ))
        except Exception:
            pass

        # 3) Güvenlik sinyali.
        security = state.get("security", {}) if isinstance(state.get("security"), dict) else {}
        if security.get("level") in ("warning", "critical") or security.get("failed_login_24h", 0):
            alerts.append(self._alert(
                "critical" if security.get("level") == "critical" else "warning",
                "security_attention",
                "Güvenlik uyarısı",
                security.get("line") or "Güvenlik tarafında dikkat gerektiren bir sinyal var.",
                "Güvenlik snapshot kontrolü yap.",
                interrupt=security.get("level") == "critical",
            ))

        # 4) Görev hataları.
        tasks = state.get("tasks", {}) if isinstance(state.get("tasks"), dict) else {}
        try:
            failed = int(tasks.get("failed", 0))
            if failed > 0:
                alerts.append(self._alert(
                    "info",
                    "task_failures",
                    "Görev hatası var",
                    f"{failed} görev hata vermiş görünüyor.",
                    "Görev geçmişini kontrol et.",
                    interrupt=False,
                ))
        except Exception:
            pass

        priority = {"none": 0, "info": 1, "warning": 2, "critical": 3}
        level = "none"
        for item in alerts:
            if priority.get(item.get("level", "none"), 0) > priority.get(level, 0):
                level = item.get("level", "none")

        return {
            "level": level,
            "alerts": alerts,
            "alert_count": len(alerts),
            "should_interrupt": any(bool(a.get("interrupt")) for a in alerts),
            "dnd": {
                "enabled": bool(dnd.get("enabled", False)),
                "behavior": dnd.get("behavior", ""),
                "note": "E1.3 sadece karar/state üretir; bildirim göndermez.",
            },
            "repeat_warning_interval": proactive_rules.get("repeat_warning_interval"),
            "message_format": proactive_rules.get("message_format"),
            "ask_question_at_end": proactive_rules.get("ask_question_at_end"),
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
