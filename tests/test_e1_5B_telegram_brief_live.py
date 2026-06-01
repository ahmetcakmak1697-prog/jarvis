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
        "profile": {
            "name": "Ahmet Fırat Çakmak",
            "city": "İzmir",
            "district": "Buca",
        },
        "briefing": {
            "title": "Canlı brifing",
            "text": "Efendim, canlı hava destekli brifing hazır.",
        },
        "proactive": {
            "level": "warning",
            "alert_count": 1,
            "should_interrupt": False,
            "alerts": [
                {
                    "level": "warning",
                    "title": "Hava uyarısı",
                    "text": "Rüzgar motosiklet için dikkat gerektiriyor.",
                    "action": "Rotayı ve ekipmanı kontrol et.",
                }
            ],
        },
        "weather": {
            "status": "live",
            "source": "web_research_d2_4",
            "default_location": "İzmir/Buca",
            "summary": "Canlı hava bilgisi D2.4 cache/rate-limit korumasıyla alındı.",
        },
        "ride_risk": {
            "level": "high",
            "status": "evaluated",
            "reason": "Yağmur ve rüzgar motosiklet için risk oluşturuyor.",
            "recommendation": "Alternatif ulaşımı ciddi şekilde değerlendir.",
        },
        "suggestion": {
            "title": "Sürüş önerisi",
            "text": "Bugün motosiklet için temkinli olmak daha mantıklı.",
            "action": "Hava/Rota Kontrolü",
        },
    }


def main():
    fails = 0

    # Import burada yapılır; patch apply edilmeden önce test çalıştırılırsa doğal olarak fail eder.
    from tools.telegram_agent import cmd_brief_live

    help_text = cmd_help()
    fails += check("/brief_live" in help_text, "/help icinde /brief_live var")

    msg = cmd_brief_live(fake_live_state())

    fails += check("JARVIS Briefing" in msg, "briefing basligi")
    fails += check("Ahmet Fırat Çakmak" in msg, "profil adi mesajda")
    fails += check("İzmir/Buca" in msg, "konum mesajda")
    fails += check("Canlı brifing" in msg, "live briefing title mesajda")
    fails += check("Hava: live" in msg, "live weather mesajda")
    fails += check("Motosiklet/hava riski: high" in msg, "ride risk high mesajda")
    fails += check("D2.4 cache/rate-limit" in msg, "D2.4 notu mesajda")
    fails += check("otomatik push yapmaz" in msg, "push yok notu mesajda")
    fails += check(len(msg) < 3600, "telegram mesaj uzunlugu makul", str(len(msg)))

    safe_msg = cmd_brief(fake_live_state())
    fails += check("sadece mevcut state" in safe_msg, "/brief guvenli notu korunuyor")

    source = Path("tools/telegram_agent.py").read_text(encoding="utf-8", errors="ignore")
    fails += check("def cmd_brief_live(" in source, "cmd_brief_live tanimli")
    fails += check('text.startswith("/brief_live")' in source, "route icinde /brief_live var")
    fails += check(source.find('text.startswith("/brief_live")') < source.find('text.startswith("/brief")'), "/brief_live route /brief'ten once")

    total = 14
    print("")
    print(f"Toplam: {total} PASS: {total - fails} FAIL: {fails}")

    if fails:
        raise SystemExit(1)

    print("✓ E1.5B GECTI — Telegram /brief_live komutu dogru formatliyor.")


if __name__ == "__main__":
    main()
