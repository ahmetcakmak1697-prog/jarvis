
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
        "title": "G?n ba?lang?c?",
        "opening": "Efendim, g?n ba?lang?c? i?in k?sa durum haz?r.",
        "suggestion": "Bug?n tek ana hedef se?ersek g?n? daha temiz y?netiriz.",
    },
    "day": {
        "mode": "day",
        "title": "Durum kontrol?",
        "opening": "Efendim, k?sa durum kontrol? haz?r.",
        "suggestion": "G?n?n ortas?nda rota iyi g?r?n?yor; tek sapmay? yakalamak yeterli.",
    },
    "evening": {
        "mode": "evening",
        "title": "Ak?am de?erlendirmesi",
        "opening": "Efendim, ak?am i?in k?sa durum haz?r.",
        "suggestion": "G?n?n k?sa ?zetini almak ve yar?na tek not b?rakmak iyi olur.",
    },
    "night": {
        "mode": "night",
        "title": "Gece ?al??ma modu",
        "opening": "Efendim, gece modu i?in k?sa durum haz?r.",
        "suggestion": "Yeni ?zellik a?mak yerine checkpoint almak daha ak?ll?ca olur.",
    },
}


def state():
    return {
        "ok": True,
        "profile": {"name": "Ahmet Firat Cakmak", "city": "Izmir", "district": "Buca"},
        "briefing": {
            "title": "Kapan?? de?erlendirmesi",
            "text": "Kapan?? i?in k?sa kontrol iyi olur. Detay isterseniz ba?l?klar? a?ar?m.",
        },
        "proactive": {"level": "none", "alert_count": 0, "should_interrupt": False, "alerts": []},
        "weather": {"status": "pending", "default_location": "Izmir/Buca", "summary": "Canli hava kapali."},
        "ride_risk": {"level": "none", "status": "pending", "score": 0, "factors": []},
        "suggestion": {"title": "Kapan?? rutini", "text": "G?n?n k?sa ?zetini ve bir sonraki ad?m? kaydetmek iyi olur."},
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

    fails += check("g?n ba?lang?c?" in morning.lower() or "gun baslangici" in morning.lower(), "sabah gun baslangici")
    fails += check("durum kontrol" in day.lower(), "ogle/gunduz durum kontrolu")
    fails += check("ak?am" in evening.lower() or "aksam" in evening.lower(), "aksam degerlendirmesi")
    fails += check("gece" in night.lower(), "gece modu")

    fails += check("G?n?n k?sa ?zetini almak" in evening or "yar?na tek not" in evening, "aksam onerisi")
    fails += check("checkpoint" in night.lower(), "gece checkpoint onerisi")
    fails += check("tek ana hedef" in morning.lower(), "sabah tek hedef onerisi")

    fails += check("/brief_live" in day and "D2.4" not in day, "brief guvenli kalir web yok")
    fails += check("Risk skoru:" not in day, "teknik skor yok")
    fails += check("Fakt?rler:" not in day and "Faktorler:" not in day, "teknik faktor yok")

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
