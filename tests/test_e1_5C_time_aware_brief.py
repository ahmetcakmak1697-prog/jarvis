
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tools.telegram_agent as tg


def check(cond, label, detail=""):
    if cond:
        print(f"[PASS] {label}" + (f" ({detail})" if detail else ""))
        return 0
    print(f"[FAIL] {label}" + (f" ({detail})" if detail else ""))
    return 1


TIME_CONTEXTS = {
    "morning": {
        "mode": "morning",
        "title": "Gün başlangıcı",
        "opening": "Efendim, gün başlangıcı için kısa durum hazır.",
        "suggestion": "Bugün tek ana hedef seçersek günü daha temiz yönetiriz.",
    },
    "day": {
        "mode": "day",
        "title": "Durum kontrol?",
        "opening": "Efendim, kısa durum kontrolü hazır.",
        "suggestion": "Günün ortasında rota iyi görünüyor; tek sapmayı yakalamak yeterli.",
    },
    "evening": {
        "mode": "evening",
        "title": "Akşam değerlendirmesi",
        "opening": "Efendim, akşam için kısa durum hazır.",
        "suggestion": "Günün kısa özetini almak ve yarına tek not bırakmak iyi olur.",
    },
    "night": {
        "mode": "night",
        "title": "Gece çalışma modu",
        "opening": "Efendim, gece modu için kısa durum hazır.",
        "suggestion": "Yeni özellik açmak yerine checkpoint almak daha akıllıca olur.",
    },
}


def state():
    return {
        "ok": True,
        "profile": {"name": "Ahmet Firat Cakmak", "city": "Izmir", "district": "Buca"},
        "briefing": {
            "title": "Kapanış değerlendirmesi",
            "text": "Kapanış için kısa kontrol iyi olur. Detay isterseniz başlıkları açarım.",
        },
        "proactive": {"level": "none", "alert_count": 0, "should_interrupt": False, "alerts": []},
        "weather": {"status": "pending", "default_location": "Izmir/Buca", "summary": "Canli hava kapali."},
        "ride_risk": {"level": "none", "status": "pending", "score": 0, "factors": []},
        "suggestion": {"title": "Kapanış rutini", "text": "Günün kısa özetini ve bir sonraki günü planlamak için idealdir."},
    }


def render_with(mode):
    with patch("tools.telegram_agent._brief_time_context", return_value=TIME_CONTEXTS[mode]):
        return tg.cmd_brief(state())


def main():
    fails = 0

    morning = render_with("morning")
    day = render_with("day")
    evening = render_with("evening")
    night = render_with("night")

    fails += check("gün başlangıcı" in morning.lower() or "gun baslangici" in morning.lower(), "sabah basligi"),
    fails += check("durum kontrol" in day.lower(), "ogle/gunduz durum kontrolu")
    fails += check("akşam" in evening.lower() or "aksam" in evening.lower(), "aksam degerlendirmesi"),
    fails += check("gece" in night.lower(), "gece modu")

    fails += check("Günün kısa özetini almak" in evening or "yarına tek not" in evening, "aksam oneri"),
    fails += check("checkpoint" in night.lower(), "gece checkpoint onerisi")
    fails += check("tek ana hedef" in morning.lower(), "sabah tek hedef onerisi")

    fails += check("/brief_live" in day and "D2.4" not in day, "brief guvenli kalir web yok")
    fails += check("Risk skoru:" not in day, "teknik skor yok")
    fails += check("Faktörler:" not in day and "Faktorler:" not in day, "teknik faktor yok"),

    source = Path("tools/telegram_agent.py").read_text(encoding="utf-8", errors="ignore")
    fails += check("def _brief_time_context(" in source, "time context helper var")
    fails += check("def _brief_should_replace_generic_title(" in source, "generic title helper var")

    total = 12
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("? E1.5C GECTI ? Telegram briefing saat baglamina gore dogal ton seciyor.")


if __name__ == "__main__":
    main()
