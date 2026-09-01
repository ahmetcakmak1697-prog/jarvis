
from pathlib import Path
import tempfile
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.proactive_core import ProactiveCore
from tools.telegram_agent import cmd_brief_live


def check(cond, label, detail=""):
    if cond:
        print(f"[PASS] {label}" + (f" ({detail})" if detail else ""))
        return 0
    print(f"[FAIL] {label}" + (f" ({detail})" if detail else ""))
    return 1


def profile():
    return {
        "identity": {"full_name": "Ahmet Firat Cakmak", "preferred_names": ["Efendim"]},
        "location_context": {"city": "Izmir", "district": "Buca"},
        "motorcycle": {"uses": True, "current_bike": {"model": "Kawasaki Vulcan S"}},
        "e1_meta": {"version": "E1.1"}
    }


def fake_state():
    return {
        "ok": True,
        "profile": {"name": "Ahmet Firat Cakmak", "city": "Izmir", "district": "Buca"},
        "briefing": {"title": "Canli brifing", "text": "Canli hava destekli brifing hazir."},
        "proactive": {"level": "none", "alert_count": 0, "should_interrupt": False, "alerts": []},
        "weather": {"status": "live", "default_location": "Izmir/Buca", "summary": "Mock hava."},
        "ride_risk": {
            "level": "high",
            "status": "evaluated",
            "score": 90,
            "factors": ["heavy_precip_probability", "rain", "strong_wind"],
            "reason": "Motosiklet icin yuksek risk var.",
            "recommendation": "Alternatif ulasimi ciddi sekilde degerlendir."
        },
        "suggestion": {"title": "Surus onerisi", "text": "Temkinli olmak iyi olur.", "action": "Hava/Rota Kontrolu"},
    }


def main():
    fails = 0

    with tempfile.TemporaryDirectory(prefix="jarvis_e15b1_", ignore_cleanup_errors=True) as tmp:
        base = Path(tmp)
        profile_path = base / "profile.json"
        state_path = base / "state.json"
        profile_path.write_text(json.dumps(profile(), ensure_ascii=False, indent=2), encoding="utf-8")

        core = ProactiveCore(state_path=str(state_path), profile_path=str(profile_path))
        p = core._load_profile()

        rain_wind = core._score_ride_weather_risk({
            "condition": "rain",
            "temp_c": 12,
            "wind_kph": 45,
            "precip_prob": 80,
            "visibility": "good",
            "alerts": []
        }, p)

        fails += check(rain_wind["score"] >= 75, "rain+strong_wind skor yuksek", str(rain_wind))
        fails += check(rain_wind["level"] == "high", "rain+strong_wind critical degil high", str(rain_wind))
        fails += check(rain_wind["should_interrupt"] is False, "high should_interrupt false")
        fails += check("score" in rain_wind and "factors" in rain_wind, "state icinde skor/faktor korunuyor")

        storm = core._score_ride_weather_risk({
            "condition": "storm",
            "temp_c": 10,
            "wind_kph": 45,
            "precip_prob": 80,
            "visibility": "low",
            "alerts": ["storm"]
        }, p)

        fails += check(storm["level"] == "critical", "storm critical kalir", str(storm))
        fails += check(storm["should_interrupt"] is True, "storm interrupt true")

        ice = core._score_ride_weather_risk({
            "condition": "ice risk",
            "temp_c": -1,
            "wind_kph": 10,
            "precip_prob": 20,
            "visibility": "medium",
            "alerts": ["ice"]
        }, p)

        fails += check(ice["level"] == "critical", "ice critical kalir", str(ice))

    msg = cmd_brief_live(fake_state())
    fails += check("motosiklet" in msg.lower() and ("risk" in msg.lower() or "dikkat" in msg.lower()), "brief_live dogal risk cumlesi")
    fails += check("Risk skoru:" not in msg, "telegram risk skoru gizli")
    fails += check("Faktörler:" not in msg and "Faktorler:" not in msg, "telegram faktor basligi yok"),
    fails += check("heavy_precip_probability" not in msg, "telegram teknik faktor gizli")
    fails += check("strong_wind" not in msg, "telegram teknik wind gizli")

    source_core = Path("agents/proactive_core.py").read_text(encoding="utf-8", errors="ignore")
    source_tg = Path("tools/telegram_agent.py").read_text(encoding="utf-8", errors="ignore")

    fails += check("has_critical_factor" in source_core, "core critical factor guard var")
    fails += check("def _brief_ride_sentence(" in source_tg, "telegram dogal risk helper var")

    total = 14
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("? E1.5B.1 GECTI ? state teknik kalir, Telegram JARVIS tonunda kalir.")


if __name__ == "__main__":
    main()
