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
        "profile": {
            "name": "Ahmet Fırat Çakmak",
            "city": "İzmir",
            "district": "Buca",
        },
        "briefing": {
            "title": "Sabah brifingi",
            "text": "Günaydın Efendim. Bugün odağı kısa tutalım.",
        },
        "proactive": {
            "level": "warning",
            "alert_count": 1,
            "should_interrupt": False,
            "alerts": [
                {
                    "level": "warning",
                    "title": "Gece çalışma uyarısı",
                    "text": "Geç saate girdik.",
                    "action": "Checkpoint al.",
                }
            ],
        },
        "weather": {
            "status": "pending",
            "source": "stub",
            "default_location": "İzmir/Buca",
            "summary": "Canlı hava kapalı.",
        },
        "ride_risk": {
            "level": "medium",
            "status": "evaluated",
            "reason": "Yağmur ihtimali var.",
            "recommendation": "Sürüş öncesi rotayı kontrol et.",
        },
        "suggestion": {
            "title": "Odak önerisi",
            "text": "Tek ana hedef belirlemek iyi olur.",
            "action": "Odak Modu",
        },
    }


def main():
    fails = 0

    help_text = cmd_help()
    fails += check("/brief" in help_text, "/help icinde /brief var")

    msg = cmd_brief(fake_state())

    fails += check("JARVIS Briefing" in msg, "briefing basligi")
    fails += check("Ahmet Fırat Çakmak" in msg, "profil adi mesajda")
    fails += check("İzmir/Buca" in msg, "konum mesajda")
    fails += check("Sabah brifingi" in msg, "briefing title mesajda")
    fails += check("Proaktif durum: warning" in msg, "proactive level mesajda")
    fails += check("Gece çalışma uyarısı" in msg, "alert mesajda")
    fails += check("Hava: pending" in msg, "weather status mesajda")
    fails += check("Motosiklet/hava riski: medium" in msg, "ride risk mesajda")
    fails += check("Odak önerisi" in msg, "suggestion mesajda")
    fails += check("otomatik web veya push yapmaz" in msg, "guvenlik notu mesajda")
    fails += check(len(msg) < 3600, "telegram mesaj uzunlugu makul", str(len(msg)))

    source = Path("tools/telegram_agent.py").read_text(encoding="utf-8", errors="ignore")
    fails += check('text.startswith("/brief")' in source, "route icinde /brief var")
    fails += check("def cmd_brief(" in source, "cmd_brief tanimli")

    total = 14
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("✓ E1.5A GECTI — Telegram /brief komutu dogru formatliyor.")


if __name__ == "__main__":
    main()
