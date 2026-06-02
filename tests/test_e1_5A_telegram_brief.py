
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.telegram_agent import cmd_brief, cmd_help


def check(cond, label, detail=""):
    if cond:
        print(f"[PASS] {label}" + (f" ({detail})" if detail else ""))
        return 0
    print(f"[FAIL] {label}" + (f" ({detail})" if detail else ""))
    return 1


def fake_state():
    return {
        "ok": True,
        "profile": {"name": "Ahmet Firat Cakmak", "city": "Izmir", "district": "Buca"},
        "briefing": {"title": "Sabah brifingi", "text": "Gunaydin Efendim. Bugun odagi kisa tutalim."},
        "proactive": {
            "level": "info",
            "alert_count": 1,
            "should_interrupt": False,
            "alerts": [
                {
                    "level": "info",
                    "code": "task_failures",
                    "title": "Gorev hatasi var",
                    "text": "1 gorev hata vermis gorunuyor.",
                    "action": "Gorev gecmisini kontrol et.",
                }
            ],
        },
        "weather": {"status": "pending", "source": "stub", "default_location": "Izmir/Buca", "summary": "Canli hava kapali."},
        "ride_risk": {
            "level": "none",
            "status": "pending",
            "score": 0,
            "factors": [],
            "reason": "Hava verisi henuz gercek kaynaga bagli degil.",
            "recommendation": "Canli hava icin /brief_live kullan.",
        },
        "suggestion": {"title": "Odak onerisi", "text": "Tek ana hedef belirlemek iyi olur.", "action": "Odak Modu"},
    }


def main():
    fails = 0

    help_text = cmd_help()
    msg = cmd_brief(fake_state())
    low = msg.lower()

    fails += check("/brief" in help_text, "/help icinde /brief var")
    fails += check("JARVIS Briefing" in msg, "briefing basligi")
    fails += check("Efendim" in msg and "durum" in low, "Jarvis acilis tonu")
    fails += check("Konum: Izmir/Buca" in msg, "konum mesajda")
    fails += check("JARVIS Briefing" in msg and "Konum:" in msg, "briefing govdesi mesajda")
    fails += check("/brief_live" in msg, "pending durumda brief_live yonlendirmesi")
    fails += check("gorev" in low or "g?rev" in low or "sistem" in low or "kritik bir sorun" in low, "gorev/sistem notu dogal")
    fails += check("Not:" in msg and "Risk skoru:" not in msg and "Fakt?rler:" not in msg and "Faktorler:" not in msg, "suggestion dogal")
    fails += check("otomatik" in low or "siz istemeden" in low, "guvenlik notu dogal")
    fails += check("Risk skoru:" not in msg, "risk skoru teknik olarak gizli")
    fails += check("Fakt?rler:" not in msg and "Faktorler:" not in msg, "faktor basligi gizli")
    fails += check("evaluated" not in msg, "evaluated teknik ifadesi yok")
    fails += check(len(msg) < 3600, "telegram mesaj uzunlugu makul", str(len(msg)))

    source = Path("tools/telegram_agent.py").read_text(encoding="utf-8", errors="ignore")
    fails += check("def cmd_brief(" in source, "cmd_brief tanimli")

    total = 14
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("? E1.5A GECTI ? Telegram /brief JARVIS tonunda formatliyor.")


if __name__ == "__main__":
    main()
