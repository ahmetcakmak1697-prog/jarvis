
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


def fake_live_state():
    return {
        "ok": True,
        "profile": {"name": "Ahmet Firat Cakmak", "city": "Izmir", "district": "Buca"},
        "briefing": {"title": "Canli brifing", "text": "Efendim, canli hava destekli brifing hazir."},
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
        "weather": {
            "status": "live",
            "source": "web_research_d2_4",
            "default_location": "Izmir/Buca",
            "summary": "Canli hava bilgisi D2.4 cache/rate-limit korumasiyla alindi.",
        },
        "ride_risk": {
            "level": "high",
            "status": "evaluated",
            "score": 75,
            "factors": ["precip_probability", "rain", "strong_wind"],
            "reason": "Yagmur ve ruzgar motosiklet icin risk olusturuyor.",
            "recommendation": "Alternatif ulasimi ciddi sekilde degerlendir.",
        },
        "suggestion": {
            "title": "Surus onerisi",
            "text": "Bugun motosiklet icin temkinli olmak daha mantikli.",
            "action": "Hava/Rota Kontrolu",
        },
    }


def main():
    fails = 0

    from tools.telegram_agent import cmd_brief_live

    help_text = cmd_help()
    msg = cmd_brief_live(fake_live_state())
    safe_msg = cmd_brief(fake_live_state())

    fails += check("/brief_live" in help_text, "/help icinde /brief_live var")
    fails += check("JARVIS Briefing" in msg, "briefing basligi")
    fails += check("Efendim" in msg and "durum" in msg, "Jarvis acilis tonu")
    fails += check("Konum: Izmir/Buca" in msg, "konum mesajda")
    fails += check("Canli brifing" in msg, "live briefing title mesajda")
    fails += check("motosiklet" in msg.lower() and ("risk" in msg.lower() or "dikkat" in msg.lower()), "ride risk dogal cumle")
    fails += check("D2.4 cache/rate-limit" in msg, "D2.4 notu mesajda")
    fails += check("otomatik push" in msg.lower(), "push yok notu mesajda")
    fails += check("Risk skoru:" not in msg, "risk skoru gizli")
    fails += check("Fakt?rler:" not in msg and "Faktorler:" not in msg, "faktorler gizli")
    fails += check(len(msg) < 3600, "telegram mesaj uzunlugu makul", str(len(msg)))
    fails += check("Bu brifing sadece durumu" in safe_msg or "siz istemeden" in safe_msg, "/brief guvenli notu korunuyor")

    source = Path("tools/telegram_agent.py").read_text(encoding="utf-8", errors="ignore")
    fails += check("def cmd_brief_live(" in source, "cmd_brief_live tanimli")
    fails += check(source.find('text.startswith("/brief_live")') < source.find('text.startswith("/brief")'), "/brief_live route /brief'ten once")

    total = 14
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("? E1.5B GECTI ? Telegram /brief_live JARVIS tonunda formatliyor.")


if __name__ == "__main__":
    main()
