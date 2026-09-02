
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.telegram_agent import cmd_brief, cmd_brief_live


def check(cond, label, detail=""):
    if cond:
        print(f"[PASS] {label}" + (f" ({detail})" if detail else ""))
        return 0
    print(f"[FAIL] {label}" + (f" ({detail})" if detail else ""))
    return 1


def state_high():
    return {
        "ok": True,
        "profile": {"name": "Ahmet Firat Cakmak", "city": "Izmir", "district": "Buca"},
        "briefing": {
            "title": "Kapanis degerlendirmesi",
            "text": "Kapanis icin kisa kontrol iyi olur. Detay isterseniz basliklari acarim.",
        },
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
            "default_location": "Izmir/Buca",
            "summary": "Canli hava bilgisi D2.4 cache/rate-limit korumasiyla alindi.",
        },
        "ride_risk": {
            "level": "high",
            "status": "evaluated",
            "score": 75,
            "factors": ["precip_probability", "rain", "strong_wind"],
            "reason": "Motosiklet icin yuksek risk var.",
            "recommendation": "Alternatif ulasimi ciddi sekilde degerlendir.",
        },
        "suggestion": {
            "title": "Kapanis rutini",
            "text": "Gunun kisa ozetini ve bir sonraki adimi kaydetmek iyi olur.",
            "action": "Gun Ozeti",
        },
    }


def state_pending():
    s = state_high()
    s["weather"] = {
        "status": "pending",
        "default_location": "Izmir/Buca",
        "summary": "Canli hava kapali.",
    }
    s["ride_risk"] = {
        "level": "none",
        "status": "pending",
        "score": 0,
        "factors": [],
        "reason": "Hava verisi henuz gercek kaynaga bagli degil.",
        "recommendation": "Canli hava icin /brief_live kullan.",
    }
    return s


def state_critical():
    s = state_high()
    s["ride_risk"] = {
        "level": "critical",
        "status": "evaluated",
        "score": 125,
        "factors": ["critical_alert", "strong_wind"],
        "reason": "Motosiklet icin kritik hava/yol riski var.",
        "recommendation": "Motosiklet surusunu ertele veya alternatif ulasimi kullan.",
    }
    return s


def main():
    fails = 0

    msg = cmd_brief(state_high())
    live_msg = cmd_brief_live(state_high())
    pending_msg = cmd_brief(state_pending())
    critical_msg = cmd_brief_live(state_critical())
    low_msg = msg.lower()

    fails += check("JARVIS Briefing" in msg, "briefing basligi var")
    fails += check("Efendim" in msg and "durum" in low_msg, "Jarvis acilis tonu var")
    fails += check("Konum: Izmir/Buca" in msg, "konum var")
    fails += check("motosiklet" in low_msg and ("risk" in low_msg or "dikkat" in low_msg), "high risk dogal cumle")
    fails += check("Sistem taraf" in msg or "kritik bir sorun" in low_msg, "sistem cumlesi dogal")
    fails += check("gorev" in low_msg or "görev" in low_msg or "sistem" in low_msg, "gorev/sistem ifadesi"),
    fails += check("Not:" in msg and "Risk skoru:" not in msg and "Faktörler:" not in msg and "Faktorler:" not in msg, "not baslik var ama risk/faktor yok"),

    fails += check("Risk skoru:" not in msg, "risk skoru gizli")
    fails += check("Faktörler:" not in msg and "Faktorler:" not in msg, "faktor basligi gibi alan yok"),
    fails += check("precip_probability" not in msg, "teknik faktor gizli")
    fails += check("evaluated" not in msg, "evaluated gizli")
    fails += check("kesinti" not in low_msg, "kesinti gizli")

    fails += check("/brief_live" in pending_msg, "pending durumda /brief_live yonlendirmesi")
    fails += check("Bu sürücüyü önermiyorum" in critical_msg or "Bu surusu onermiyorum" in critical_msg, "surucu oneri mesaji"),
    fails += check("D2.4 cache/rate-limit" in live_msg, "brief_live notu korunuyor")

    source = Path("tools/telegram_agent.py").read_text(encoding="utf-8", errors="ignore")
    fails += check("def _brief_ride_sentence(" in source, "ride sentence helper var")
    fails += check("def _brief_alert_sentence(" in source, "alert sentence helper var")

    total = 17
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("? E1.5B.3 GECTI ? Telegram brifingi teknik log degil, JARVIS tonuna yakin.")


if __name__ == "__main__":
    main()
