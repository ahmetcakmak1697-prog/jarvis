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
        "profile": {"name": "Ahmet Fırat Çakmak", "city": "İzmir", "district": "Buca"},
        "briefing": {
            "title": "Kapanış değerlendirmesi",
            "text": "Kapanış için kısa kontrol iyi olur. Detay isterseniz başlıkları açarım.",
        },
        "proactive": {
            "level": "info",
            "alert_count": 1,
            "should_interrupt": False,
            "alerts": [
                {
                    "level": "info",
                    "code": "task_failures",
                    "title": "Görev hatası var",
                    "text": "1 görev hata vermiş görünüyor.",
                    "action": "Görev geçmişini kontrol et.",
                }
            ],
        },
        "weather": {
            "status": "live",
            "default_location": "İzmir/Buca",
            "summary": "Canlı hava bilgisi D2.4 cache/rate-limit korumasıyla alındı.",
        },
        "ride_risk": {
            "level": "high",
            "status": "evaluated",
            "score": 75,
            "factors": ["precip_probability", "rain", "strong_wind"],
            "reason": "Motosiklet için yüksek risk var.",
            "recommendation": "Alternatif ulaşımı ciddi şekilde değerlendir.",
        },
        "suggestion": {
            "title": "Kapanış rutini",
            "text": "Günün kısa özetini ve bir sonraki adımı kaydetmek iyi olur.",
            "action": "Gün Özeti",
        },
    }


def state_pending():
    s = state_high()
    s["weather"] = {
        "status": "pending",
        "default_location": "İzmir/Buca",
        "summary": "Canlı hava kapalı.",
    }
    s["ride_risk"] = {
        "level": "none",
        "status": "pending",
        "score": 0,
        "factors": [],
        "reason": "Hava verisi henüz gerçek kaynağa bağlı değil.",
        "recommendation": "E1.4B aşamasında gerçek hava verisi D2.4 cache ile bağlanacak.",
    }
    return s


def state_critical():
    s = state_high()
    s["ride_risk"] = {
        "level": "critical",
        "status": "evaluated",
        "score": 125,
        "factors": ["critical_alert", "strong_wind"],
        "reason": "Motosiklet için kritik hava/yol riski var.",
        "recommendation": "Motosiklet sürüşünü ertele veya alternatif ulaşımı kullan.",
    }
    return s


def main():
    fails = 0

    msg = cmd_brief(state_high())
    live_msg = cmd_brief_live(state_high())
    pending_msg = cmd_brief(state_pending())
    critical_msg = cmd_brief_live(state_critical())

    fails += check("Efendim, kısa durum hazır." in msg, "Jarvis açılışı var")
    fails += check("Konum: İzmir/Buca" in msg, "konum var")
    fails += check("Yağış ihtimali ve kuvvetli rüzgâr birlikte motosiklet için gereksiz risk oluşturuyor" in msg, "high risk doğal cümle")
    fails += check("Sistem tarafında kritik bir sorun görünmüyor" in msg, "sistem cümlesi doğal")
    fails += check("görev geçmişinde bir hata var" in msg.lower(), "görev hatası doğal")
    fails += check("Kapanış için kısa bir gün özeti iyi olur." in msg, "kapanış önerisi doğal")

    fails += check("Risk skoru:" not in msg, "risk skoru gizli")
    fails += check("Faktörler:" not in msg, "faktör başlığı gizli")
    fails += check("precip_probability" not in msg, "teknik faktor gizli")
    fails += check("evaluated" not in msg, "evaluated gizli")
    fails += check("kesinti" not in msg.lower(), "kesinti gizli")

    fails += check("Canlı hava şu an kapalı" in pending_msg, "pending durumda /brief_live yönlendirmesi")
    fails += check("Bu sürüşü önermiyorum" in critical_msg, "critical durumda net uyarı")
    fails += check("Canlı hava D2.4 cache/rate-limit korumasıyla alındı" in live_msg, "brief_live notu korunuyor")

    source = Path("tools/telegram_agent.py").read_text(encoding="utf-8", errors="ignore")
    fails += check("def _brief_ride_sentence(" in source, "ride sentence helper var")
    fails += check("def _brief_alert_sentence(" in source, "alert sentence helper var")

    total = 16
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("✓ E1.5B.3 GECTI — Telegram brifingi teknik log degil, JARVIS tonuna yaklasti.")


if __name__ == "__main__":
    main()
