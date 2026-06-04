from pathlib import Path
import tempfile
import json
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.proactive_core import ProactiveCore


def check(cond, label, detail=""):
    if cond:
        print(f"[PASS] {label}" + (f" ({detail})" if detail else ""))
        return 0
    print(f"[FAIL] {label}" + (f" ({detail})" if detail else ""))
    return 1


class TestCore(ProactiveCore):
    def __init__(self, *args, fake_system=None, fake_security=None, fake_tasks=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fake_system = fake_system or {}
        self.fake_security = fake_security or {}
        self.fake_tasks = fake_tasks or {}

    def _system_stub(self):
        return {
            "health_score": self.fake_system.get("health_score", 100),
            "disk_percent": self.fake_system.get("disk_percent", 10),
            "ram_percent": self.fake_system.get("ram_percent", 10),
            "line": "fake system",
        }

    def _security_stub(self):
        return {
            "level": self.fake_security.get("level", "normal"),
            "failed_login_24h": self.fake_security.get("failed_login_24h", 0),
            "line": self.fake_security.get("line", "fake security"),
        }

    def _tasks_stub(self):
        return {
            "failed": self.fake_tasks.get("failed", 0),
            "line": "fake tasks",
        }


def profile():
    return {
        "identity": {
            "full_name": "Ahmet Fırat Çakmak",
            "preferred_names": ["Efendim", "Ahmet"]
        },
        "location_context": {
            "city": "İzmir",
            "district": "Buca",
            "neighborhood": "Mustafa Kemal Mahallesi"
        },
        "current_projects": ["JARVIS yerel AI asistanı"],
        "night_warnings": {
            "workday_light_warning_times": ["22:00", "22:45"],
            "workday_final_warning": "23:30",
            "holiday_flexible": True,
            "holiday_late_threshold": "02:30"
        },
        "proactive_rules": {
            "briefing_format": "sadece başlıklar; kullanıcı detay isterse başlıkları aç",
            "repeat_warning_interval": "aynı gün içinde 3 saat; durum kötüleşirse kritik uyarı",
            "message_format": ["öneri + aksiyon", "3 maddelik özet"],
            "ask_question_at_end": "hayır; sadece kritikse soru sor",
            "critical_thresholds": {
                "system_health_below": 75,
                "system_health_critical_below": 50,
                "disk_percent_above": 85,
                "ram_percent_above": 90,
                "weekday_late_night_after": "01:00",
                "weekend_late_night_after": "02:30"
            },
            "do_not_disturb": {
                "enabled": True,
                "behavior": "her şey çalışmaya devam etsin; moddan çıkınca önemli olayları sırala"
            }
        },
        "e1_meta": {"version": "E1.1"}
    }


def build(core, dt):
    p = core._load_profile()
    state = {
        "system": core._system_stub(),
        "security": core._security_stub(),
        "tasks": core._tasks_stub(),
    }
    return core._proactive_stub(dt, p, state)


def main():
    fails = 0

    with tempfile.TemporaryDirectory(prefix="jarvis_e13_", ignore_cleanup_errors=True) as tmp:
        base = Path(tmp)
        profile_path = base / "user_profile.json"
        state_path = base / "state.json"
        profile_path.write_text(json.dumps(profile(), ensure_ascii=False, indent=2), encoding="utf-8")

        core = TestCore(state_path=str(state_path), profile_path=str(profile_path))

        normal = build(core, datetime(2026, 6, 1, 12, 0))
        fails += check(normal["level"] == "none", "normal durumda alert yok", str(normal))
        fails += check(normal["alert_count"] == 0, "normal alert_count 0")
        fails += check(normal["profile_aware"] is True, "profile aware true")
        fails += check(normal["dnd"]["enabled"] is True, "DND config state'e geldi")

        late = build(core, datetime(2026, 6, 1, 23, 45))  # Monday
        fails += check(late["level"] == "warning", "hafta ici 23:45 warning")
        fails += check(any(a["code"] == "late_night_workday" for a in late["alerts"]), "late_night_workday alert var")

        critical_late = build(core, datetime(2026, 6, 2, 1, 10))  # Tuesday
        fails += check(critical_late["level"] == "critical", "hafta ici 01:10 critical")
        fails += check(critical_late["should_interrupt"] is True, "critical gece should_interrupt true")

        weekend_late = build(core, datetime(2026, 6, 7, 2, 45))  # Sunday
        fails += check(weekend_late["level"] == "warning", "hafta sonu 02:45 warning")
        fails += check(any(a["code"] == "late_night_weekend" for a in weekend_late["alerts"]), "weekend late alert var")

        warn_core = TestCore(
            state_path=str(base / "warn.json"),
            profile_path=str(profile_path),
            fake_system={"health_score": 70, "disk_percent": 10, "ram_percent": 10}
        )
        sys_warn = build(warn_core, datetime(2026, 6, 1, 12, 0))
        fails += check(sys_warn["level"] == "warning", "system health 70 warning")
        fails += check(any(a["code"] == "system_health_warning" for a in sys_warn["alerts"]), "system health warning code")

        crit_core = TestCore(
            state_path=str(base / "crit.json"),
            profile_path=str(profile_path),
            fake_system={"health_score": 45, "disk_percent": 90, "ram_percent": 95}
        )
        sys_crit = build(crit_core, datetime(2026, 6, 1, 12, 0))
        fails += check(sys_crit["level"] == "critical", "system health 45 critical")
        fails += check(sys_crit["should_interrupt"] is True, "system critical interrupt")
        fails += check(any(a["code"] == "disk_usage_high" for a in sys_crit["alerts"]), "disk usage alert")
        fails += check(any(a["code"] == "ram_usage_high" for a in sys_crit["alerts"]), "ram usage alert")

        sec_core = TestCore(
            state_path=str(base / "sec.json"),
            profile_path=str(profile_path),
            fake_security={"level": "critical", "failed_login_24h": 3, "line": "Yetkisiz deneme"}
        )
        sec = build(sec_core, datetime(2026, 6, 1, 12, 0))
        fails += check(sec["level"] == "critical", "security critical")
        fails += check(any(a["code"] == "security_attention" for a in sec["alerts"]), "security alert code")

        task_core = TestCore(
            state_path=str(base / "task.json"),
            profile_path=str(profile_path),
            fake_tasks={"failed": 2}
        )
        task = build(task_core, datetime(2026, 6, 1, 12, 0))
        fails += check(task["level"] == "info", "task failure info")
        fails += check(any(a["code"] == "task_failures" for a in task["alerts"]), "task failure code")

        live_core = TestCore(state_path=str(base / "live_state.json"), profile_path=str(profile_path))
        live_state = live_core.build_state()
        fails += check("proactive" in live_state, "build_state proactive alanini yazar")
        fails += check(live_state["proactive"]["profile_aware"] is True, "live proactive profile-aware")

    total = 20
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("✓ E1.3 GECTI — Conditional proactive alert state dogru calisiyor.")


if __name__ == "__main__":
    main()
