from pathlib import Path
import tempfile
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.proactive_core import ProactiveCore


def check(cond, label, detail=""):
    if cond:
        print(f"[PASS] {label}" + (f" ({detail})" if detail else ""))
        return 0
    print(f"[FAIL] {label}" + (f" ({detail})" if detail else ""))
    return 1


def main():
    fails = 0

    with tempfile.TemporaryDirectory(prefix="jarvis_e12_", ignore_cleanup_errors=True) as tmp:
        base = Path(tmp)
        profile_path = base / "user_profile.json"
        state_path = base / "proactive_state.json"

        profile = {
            "name": "Ahmet Fırat",
            "city": "İzmir",
            "district": "Buca",
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
            "briefing": {
                "mode": "automatic_morning",
                "time": "08:30"
            },
            "music": {
                "artists_groups": ["AC/DC", "Metallica"]
            },
            "proactive_rules": {
                "briefing_format": "sadece başlıklar; kullanıcı detay isterse başlıkları aç"
            },
            "e1_meta": {
                "version": "E1.1"
            }
        }

        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

        core = ProactiveCore(state_path=str(state_path), profile_path=str(profile_path))
        state = core.build_state()

        fails += check(state.get("ok") is True, "state ok")
        fails += check(state_path.exists(), "state dosyasi yazildi")
        fails += check(state.get("profile", {}).get("name") == "Ahmet Fırat Çakmak", "profile full_name state'e geldi")
        fails += check(state.get("profile", {}).get("city") == "İzmir", "profile city state'e geldi")
        fails += check(state.get("profile", {}).get("district") == "Buca", "profile district state'e geldi")
        fails += check(state.get("profile", {}).get("profile_version") == "E1.1", "profile version state'e geldi")
        fails += check(state.get("briefing", {}).get("profile_aware") is True, "briefing profile-aware")
        fails += check("JARVIS" in state.get("briefing", {}).get("project", ""), "briefing proje bilgisi")
        fails += check(state.get("weather", {}).get("city") == "İzmir", "weather city profile'dan")
        fails += check(state.get("weather", {}).get("district") == "Buca", "weather district profile'dan")
        fails += check(state.get("music", {}).get("suggestion", {}).get("artist") == "AC/DC", "music AC/DC profile'dan")
        fails += check(state.get("suggestion", {}).get("profile_aware") is True, "suggestion profile-aware")
        fails += check("briefing_format" in state.get("suggestion", {}), "suggestion briefing_format tasiyor")

        latest = core.latest()
        fails += check(latest.get("profile", {}).get("name") == "Ahmet Fırat Çakmak", "latest state profile korundu")

        fallback_core = ProactiveCore(
            state_path=str(base / "fallback_state.json"),
            profile_path=str(base / "missing_profile.json")
        )
        fallback = fallback_core.build_state()
        fails += check(fallback.get("ok") is True, "missing profile fallback crash yok")
        fails += check(fallback.get("briefing", {}).get("ready") is True, "fallback briefing ready")

    total = 16
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("✓ E1.2 GECTI — ProactiveCore profile-aware state dogru calisiyor.")


if __name__ == "__main__":
    main()
