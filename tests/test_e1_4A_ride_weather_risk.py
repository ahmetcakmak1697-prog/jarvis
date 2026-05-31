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


def profile(uses=True):
    return {
        "identity": {"full_name": "Ahmet Fırat Çakmak", "preferred_names": ["Efendim"]},
        "location_context": {"city": "İzmir", "district": "Buca"},
        "motorcycle": {
            "uses": uses,
            "current_bike": {"model": "Kawasaki Vulcan S"},
            "weather_alerts": ["yağmur", "fırtına", "don/buz", "aşırı sıcak", "kuvvetli rüzgar", "sis"]
        },
        "e1_meta": {"version": "E1.1"}
    }


def main():
    fails = 0

    with tempfile.TemporaryDirectory(prefix="jarvis_e14a_", ignore_cleanup_errors=True) as tmp:
        base = Path(tmp)
        state_path = base / "state.json"
        profile_path = base / "profile.json"

        profile_path.write_text(json.dumps(profile(True), ensure_ascii=False, indent=2), encoding="utf-8")
        core = ProactiveCore(state_path=str(state_path), profile_path=str(profile_path))
        p = core._load_profile()

        normal = core._score_ride_weather_risk({
            "condition": "clear",
            "temp_c": 22,
            "wind_kph": 8,
            "precip_prob": 0,
            "visibility": "good",
            "alerts": []
        }, p)
        fails += check(normal["level"] == "none", "normal hava none", str(normal))
        fails += check(normal["should_warn"] is False, "normal should_warn false")

        low = core._score_ride_weather_risk({
            "condition": "clear",
            "temp_c": 35,
            "wind_kph": 10,
            "precip_prob": 0,
            "visibility": "good",
            "alerts": []
        }, p)
        fails += check(low["level"] == "low", "35C low risk", str(low))

        medium = core._score_ride_weather_risk({
            "condition": "hafif yağmur",
            "temp_c": 16,
            "wind_kph": 12,
            "precip_prob": 40,
            "visibility": "good",
            "alerts": []
        }, p)
        fails += check(medium["level"] == "medium", "hafif yağmur medium", str(medium))
        fails += check(medium["should_warn"] is True, "medium should_warn true")
        fails += check("rain" in medium["factors"], "medium rain factor")

        high = core._score_ride_weather_risk({
            "condition": "rain",
            "temp_c": 12,
            "wind_kph": 45,
            "precip_prob": 80,
            "visibility": "good",
            "alerts": []
        }, p)
        fails += check(high["level"] in ("high", "critical"), "kuvvetli yağmur/rüzgar high veya critical", str(high))
        fails += check("strong_wind" in high["factors"] or "dangerous_wind" in high["factors"], "wind factor var")

        critical = core._score_ride_weather_risk({
            "condition": "fırtına",
            "temp_c": 3,
            "wind_kph": 65,
            "precip_prob": 90,
            "visibility": "low",
            "alerts": ["storm"]
        }, p)
        fails += check(critical["level"] == "critical", "fırtına critical", str(critical))
        fails += check(critical["should_interrupt"] is True, "critical should_interrupt true")
        fails += check("critical_alert" in critical["factors"], "critical alert factor")

        ice = core._score_ride_weather_risk({
            "condition": "don ve buz riski",
            "temp_c": -1,
            "wind_kph": 15,
            "precip_prob": 20,
            "visibility": "medium",
            "alerts": ["ice"]
        }, p)
        fails += check(ice["level"] == "critical", "don/buz critical", str(ice))
        fails += check("freezing_temperature" in ice["factors"], "freezing factor")

        disabled = core._score_ride_weather_risk({
            "condition": "rain",
            "temp_c": 12,
            "wind_kph": 30,
            "precip_prob": 80,
        }, profile(False))
        fails += check(disabled["enabled"] is False, "motosiklet yoksa disabled")
        fails += check(disabled["level"] == "none", "disabled level none")

        pending = core._ride_weather_risk_stub(p, {
            "status": "pending",
            "summary": "",
            "temperature_c": None,
            "alerts": []
        })
        fails += check(pending["status"] == "pending", "pending weather pending kalir")
        fails += check(pending["should_warn"] is False, "pending should_warn false")
        fails += check(pending["source"] == "decision_schema_only", "source decision_schema_only")

        live = core.build_state()
        fails += check("ride_risk" in live, "build_state ride_risk alanini yazar")
        fails += check(live["ride_risk"]["profile_aware"] is True, "live ride_risk profile-aware")
        fails += check(live["ride_risk"]["source"] == "decision_schema_only", "live ride_risk web kullanmaz")

    total = 19
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("✓ E1.4A GECTI — Ride weather risk decision schema dogru calisiyor.")


if __name__ == "__main__":
    main()
