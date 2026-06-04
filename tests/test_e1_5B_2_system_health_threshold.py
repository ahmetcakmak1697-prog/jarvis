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
    def __init__(self, *args, fake_health=100, **kwargs):
        super().__init__(*args, **kwargs)
        self.fake_health = fake_health

    def _system_stub(self):
        return {
            "health_score": self.fake_health,
            "disk_percent": 10,
            "ram_percent": 10,
            "line": "fake system",
        }

    def _security_stub(self):
        return {"level": "normal", "failed_login_24h": 0, "line": "fake security"}

    def _tasks_stub(self):
        return {"failed": 0, "line": "fake tasks"}


def profile():
    return {
        "identity": {"full_name": "Ahmet Fırat Çakmak", "preferred_names": ["Efendim"]},
        "proactive_rules": {
            "critical_thresholds": {
                "system_health_below": 75,
                "system_health_critical_below": 50,
                "disk_percent_above": 85,
                "ram_percent_above": 90,
                "weekday_late_night_after": "01:00",
                "weekend_late_night_after": "02:30"
            },
            "do_not_disturb": {"enabled": True}
        },
        "night_warnings": {
            "workday_final_warning": "23:30",
            "holiday_late_threshold": "02:30"
        }
    }


def build(core):
    p = core._load_profile()
    state = {
        "system": core._system_stub(),
        "security": core._security_stub(),
        "tasks": core._tasks_stub(),
    }
    return core._proactive_stub(datetime(2026, 6, 1, 12, 0), p, state)


def main():
    fails = 0

    with tempfile.TemporaryDirectory(prefix="jarvis_e15b2_", ignore_cleanup_errors=True) as tmp:
        base = Path(tmp)
        profile_path = base / "profile.json"
        profile_path.write_text(json.dumps(profile(), ensure_ascii=False, indent=2), encoding="utf-8")

        health_75 = build(TestCore(state_path=str(base / "s75.json"), profile_path=str(profile_path), fake_health=75))
        fails += check(health_75["level"] == "none", "health 75 warning degil", str(health_75))
        fails += check(not any(a.get("code") == "system_health_warning" for a in health_75["alerts"]), "health 75 warning alert yok")

        health_74 = build(TestCore(state_path=str(base / "s74.json"), profile_path=str(profile_path), fake_health=74))
        fails += check(health_74["level"] == "warning", "health 74 warning", str(health_74))
        fails += check(any(a.get("code") == "system_health_warning" for a in health_74["alerts"]), "health 74 warning alert var")

        health_50 = build(TestCore(state_path=str(base / "s50.json"), profile_path=str(profile_path), fake_health=50))
        fails += check(health_50["level"] == "warning", "health 50 critical degil warning", str(health_50))

        health_49 = build(TestCore(state_path=str(base / "s49.json"), profile_path=str(profile_path), fake_health=49))
        fails += check(health_49["level"] == "critical", "health 49 critical", str(health_49))
        fails += check(health_49["should_interrupt"] is True, "health 49 interrupt true")

    total = 7
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("✓ E1.5B.2 GECTI — system health threshold daha dogru calisiyor.")


if __name__ == "__main__":
    main()
