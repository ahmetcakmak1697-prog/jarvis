import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.proactive_core import ProactiveCore


def main():
    core = ProactiveCore("memory/test_proactive_state.json")
    state = core.build_state()

    assert isinstance(state, dict), "state dict değil"
    assert state.get("ok") is True, "ok true değil"
    assert state.get("version") == "B1.1", "version hatalı"
    assert "briefing" in state, "briefing yok"
    assert "security" in state, "security yok"
    assert "music" in state, "music yok"
    assert "weather" in state, "weather yok"
    assert state["briefing"].get("text"), "briefing text boş"

    latest = core.latest()
    assert latest.get("ok") is True, "latest ok değil"

    print("B1 proactive core smoke OK")


if __name__ == "__main__":
    main()
