from pathlib import Path
import tempfile
import json
import sys
import types
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.proactive_core import ProactiveCore


def check(cond, label, detail=""):
    if cond:
        print(f"[PASS] {label}" + (f" ({detail})" if detail else ""))
        return 0
    print(f"[FAIL] {label}" + (f" ({detail})" if detail else ""))
    return 1


def profile():
    return {
        "identity": {"full_name": "Ahmet Fırat Çakmak", "preferred_names": ["Efendim"]},
        "location_context": {"city": "İzmir", "district": "Buca"},
        "motorcycle": {"uses": True, "current_bike": {"model": "Kawasaki Vulcan S"}},
        "e1_meta": {"version": "E1.1"}
    }


class FakeWebResearcher:
    calls = 0
    last_query = None

    def __init__(self):
        self.last_source_scores = [{"url": "https://example.com/weather", "trust": "mock"}]

    def research(self, query, deep=False):
        FakeWebResearcher.calls += 1
        FakeWebResearcher.last_query = query
        return (
            "İzmir Buca hava durumu: sıcaklık 18°C. "
            "Yağmur ihtimali %70. Rüzgar 42 km/s. "
            "Motosiklet sürüşü için dikkat gerektirir."
        )


def install_fake_web_module():
    fake_mod = types.ModuleType("tools.web_research")
    fake_mod.WebResearcher = FakeWebResearcher
    sys.modules["tools.web_research"] = fake_mod


def main():
    fails = 0

    with tempfile.TemporaryDirectory(prefix="jarvis_e14b_", ignore_cleanup_errors=True) as tmp:
        base = Path(tmp)
        profile_path = base / "profile.json"
        state_path = base / "state.json"

        profile_path.write_text(json.dumps(profile(), ensure_ascii=False, indent=2), encoding="utf-8")

        # Default: live_weather False, web'e cikmamali.
        core = ProactiveCore(state_path=str(state_path), profile_path=str(profile_path))
        state = core.build_state()

        fails += check(state["weather"]["status"] == "pending", "default live_weather kapali")
        fails += check(state["weather"].get("source") == "stub", "default weather source stub")
        fails += check(state["ride_risk"]["source"] == "decision_schema_only", "ride_risk decision schema")
        fails += check(state["ride_risk"]["status"] == "pending", "default ride_risk pending")

        # Parser testi.
        parsed = core._parse_weather_report(
            "Bugün sıcaklık 18°C, yağmur ihtimali %70, rüzgar 42 km/s. Sağanak bekleniyor."
        )
        fails += check(parsed["condition"] == "yağmur", "parser condition yağmur")
        fails += check(parsed["temp_c"] == 18, "parser temp 18")
        fails += check(parsed["wind_kph"] == 42, "parser wind 42")
        fails += check(parsed["precip_prob"] == 70, "parser precip 70")

        query = core._weather_query_from_profile(core._load_profile())
        fails += check("İzmir" in query and "Buca" in query, "query profile konumunu kullanir", query)
        fails += check("motosiklet" in query.lower(), "query motosiklet riskini ister")

        # Live weather mock.
        install_fake_web_module()
        FakeWebResearcher.calls = 0
        FakeWebResearcher.last_query = None

        live_core = ProactiveCore(state_path=str(base / "live_state.json"), profile_path=str(profile_path), live_weather=True)
        live_state = live_core.build_state()

        fails += check(FakeWebResearcher.calls == 1, "live weather WebResearcher cagirir")
        fails += check(live_state["weather"]["status"] == "live", "live weather status live")
        fails += check(live_state["weather"]["source"] == "web_research_d2_4", "live weather source web_research_d2_4")
        fails += check(live_state["weather"]["city"] == "İzmir", "live weather city İzmir")
        fails += check(live_state["weather"]["district"] == "Buca", "live weather district Buca")
        fails += check(live_state["weather"]["source_scores"], "source_scores tasinir")
        fails += check(live_state["ride_risk"]["level"] in ("medium", "high", "critical"), "live weather ride_risk uretir", str(live_state["ride_risk"]))
        fails += check(live_state["ride_risk"]["should_warn"] is True, "live ride_risk should_warn true")

        # Env flag testi.
        old_env = os.environ.get("JARVIS_LIVE_WEATHER")
        os.environ["JARVIS_LIVE_WEATHER"] = "1"
        try:
            env_core = ProactiveCore(state_path=str(base / "env_state.json"), profile_path=str(profile_path))
            fails += check(env_core.live_weather is True, "env flag live_weather acar")
        finally:
            if old_env is None:
                os.environ.pop("JARVIS_LIVE_WEATHER", None)
            else:
                os.environ["JARVIS_LIVE_WEATHER"] = old_env

        # Fallback: WebResearcher hata verirse crash yok.
        class BrokenWebResearcher:
            def __init__(self):
                self.last_source_scores = []

            def research(self, query, deep=False):
                raise RuntimeError("mock web down")

        fake_mod = types.ModuleType("tools.web_research")
        fake_mod.WebResearcher = BrokenWebResearcher
        sys.modules["tools.web_research"] = fake_mod

        fallback_core = ProactiveCore(state_path=str(base / "fallback_state.json"), profile_path=str(profile_path), live_weather=True)
        fallback = fallback_core.build_state()
        fails += check(fallback["weather"]["status"] == "fallback", "web hata fallback")
        fails += check(fallback["ok"] is True, "fallback state ok")

    total = 22
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("✓ E1.4B GECTI — Live weather bridge opt-in ve mock test dogru calisiyor.")


if __name__ == "__main__":
    main()
