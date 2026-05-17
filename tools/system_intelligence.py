import os
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, date

try:
    import psutil
except Exception:
    psutil = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = PROJECT_ROOT / "memory"


def _read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _count_json_items(path: Path) -> int:
    data = _read_json(path, None)

    if isinstance(data, list):
        return len(data)

    if isinstance(data, dict):
        return len(data)

    return 0


def _db_chat_count() -> int:
    db_path = MEMORY_DIR / "jarvis_memory.db"

    if not db_path.exists():
        return 0

    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM chats")
        count = cur.fetchone()[0]
        con.close()
        return int(count)
    except Exception:
        return 0


def _get_cpu_percent() -> float:
    if not psutil:
        return 0.0

    try:
        return float(psutil.cpu_percent(interval=0.15))
    except Exception:
        return 0.0


def _get_ram_info() -> dict:
    if not psutil:
        return {
            "percent": 0,
            "used_gb": 0,
            "total_gb": 0,
        }

    try:
        mem = psutil.virtual_memory()
        return {
            "percent": round(float(mem.percent), 1),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "total_gb": round(mem.total / (1024 ** 3), 2),
        }
    except Exception:
        return {
            "percent": 0,
            "used_gb": 0,
            "total_gb": 0,
        }


def _get_disk_info() -> dict:
    try:
        usage = psutil.disk_usage(str(PROJECT_ROOT)) if psutil else None

        if not usage:
            return {
                "percent": 0,
                "used_gb": 0,
                "total_gb": 0,
            }

        return {
            "percent": round(float(usage.percent), 1),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "total_gb": round(usage.total / (1024 ** 3), 2),
        }
    except Exception:
        return {
            "percent": 0,
            "used_gb": 0,
            "total_gb": 0,
        }


def _get_gpu_info() -> dict:
    """
    Hafif GPU kontrolü.
    nvidia-smi varsa kullanır, yoksa sistem bozulmaz.
    """
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]

        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=2)
        first = out.strip().splitlines()[0]
        parts = [p.strip() for p in first.split(",")]

        util = float(parts[0])
        mem_used = float(parts[1])
        mem_total = float(parts[2])
        temp = float(parts[3])

        return {
            "available": True,
            "percent": round(util, 1),
            "memory_used_mb": round(mem_used, 1),
            "memory_total_mb": round(mem_total, 1),
            "memory_percent": round((mem_used / mem_total) * 100, 1) if mem_total else 0,
            "temperature": round(temp, 1),
        }

    except Exception:
        return {
            "available": False,
            "percent": 0,
            "memory_used_mb": 0,
            "memory_total_mb": 0,
            "memory_percent": 0,
            "temperature": None,
        }


def _get_tavily_status() -> dict:
    credit_path = MEMORY_DIR / "search_credits.json"
    data = _read_json(credit_path, {})

    remaining = data.get("remaining", None)
    reset_date = data.get("reset_date", None)

    return {
        "active": bool(os.getenv("TAVILY_API_KEY")),
        "remaining": remaining,
        "limit": 1000,
        "reset_date": reset_date,
        "cache_exists": (MEMORY_DIR / "research_cache.json").exists(),
    }


def _get_memory_status() -> dict:
    profile_count = _count_json_items(MEMORY_DIR / "user_profile.json")
    conversation_count = _count_json_items(MEMORY_DIR / "conversations.json")
    chat_count = _db_chat_count()

    # Vector memory sayısı için en risksiz yöntem:
    # Jarvis açılışındaki VM sayısı farklı yerde tutuluyor olabilir.
    # Şimdilik conversation + db + profile toplamını gösteriyoruz.
    total_known = profile_count + conversation_count + chat_count

    return {
        "profile_count": profile_count,
        "conversation_count": conversation_count,
        "chat_count": chat_count,
        "total_known_records": total_known,
        "confidence": "orta",
    }


def _get_file_health() -> dict:
    required_files = [
        "jarvis_brain.py",
        "jarvis_server.py",
        "tools/file_tools.py",
        "tools/web_research.py",
        "tools/diagnostics.py",
        "tools/system_intelligence.py",
        "test_jarvis_tools.py",
    ]

    missing = []

    for rel in required_files:
        if not (PROJECT_ROOT / rel).exists():
            missing.append(rel)

    return {
        "required": required_files,
        "missing": missing,
        "ok": len(missing) == 0,
    }


def get_system_status() -> dict:
    cpu = _get_cpu_percent()
    ram = _get_ram_info()
    disk = _get_disk_info()
    gpu = _get_gpu_info()

    return {
        "cpu_percent": cpu,
        "ram": ram,
        "disk": disk,
        "gpu": gpu,
    }


def get_health_score(system_status: dict | None = None) -> dict:
    """
    100 üzerinden sağlık skoru.
    İlk sürüm: hızlı, hafif, kural tabanlı.
    """
    system_status = system_status or get_system_status()

    score = 100
    reasons = []

    cpu = system_status.get("cpu_percent", 0)
    ram_percent = system_status.get("ram", {}).get("percent", 0)
    disk_percent = system_status.get("disk", {}).get("percent", 0)
    gpu = system_status.get("gpu", {})
    gpu_percent = gpu.get("percent", 0)
    gpu_temp = gpu.get("temperature", None)

    file_health = _get_file_health()
    tavily = _get_tavily_status()

    if cpu >= 90:
        score -= 20
        reasons.append("CPU kullanımı çok yüksek")
    elif cpu >= 75:
        score -= 10
        reasons.append("CPU kullanımı yükselmiş")

    if ram_percent >= 90:
        score -= 25
        reasons.append("RAM baskısı kritik seviyede")
    elif ram_percent >= 75:
        score -= 12
        reasons.append("RAM kullanımı yükseliyor")

    if disk_percent >= 95:
        score -= 20
        reasons.append("Disk doluluğu kritik seviyede")
    elif disk_percent >= 85:
        score -= 8
        reasons.append("Disk doluluğu artmış")

    if gpu.get("available") and gpu_percent >= 95:
        score -= 10
        reasons.append("GPU kullanımı çok yüksek")

    if gpu_temp is not None and gpu_temp >= 84:
        score -= 12
        reasons.append("GPU sıcaklığı yüksek")

    if not file_health["ok"]:
        score -= 25
        reasons.append("Çekirdek dosyalardan bazıları eksik")

    if not tavily["active"]:
        score -= 5
        reasons.append("Tavily pasif")

    remaining = tavily.get("remaining")
    if isinstance(remaining, int):
        if remaining <= 50:
            score -= 12
            reasons.append("Tavily kredisi kritik seviyede")
        elif remaining <= 150:
            score -= 6
            reasons.append("Tavily kredisi azalıyor")

    score = max(0, min(100, int(score)))

    if score >= 76:
        level = "normal"
        color = "blue"
        label = "Stabil"
    elif score >= 51:
        level = "warning"
        color = "yellow"
        label = "Dikkat"
    elif score >= 26:
        level = "critical"
        color = "orange"
        label = "Kritik"
    else:
        level = "danger"
        color = "red"
        label = "Acil"

    if not reasons:
        reasons.append("Sistem değerleri normal aralıkta")

    return {
        "score": score,
        "level": level,
        "color": color,
        "label": label,
        "reasons": reasons,
        "threshold_note": _health_threshold_note(score, reasons),
    }


def _health_threshold_note(score: int, reasons: list[str]) -> str:
    primary = reasons[0] if reasons else "Belirgin sorun yok"

    if score >= 76:
        return "Sistem sakin. Kritik eşiklerde uyarı verilecek."

    if score >= 51:
        return f"Sistem sağlığı dikkat seviyesinde. Ana etken: {primary}."

    if score >= 26:
        return f"Kritik eşik yaklaşıyor efendim. Öncelikli parazit: {primary}."

    return f"Acil durum seviyesi. Çekirdeği rahatlatmak gerekiyor. Ana sorun: {primary}."


def get_risk_radar(health: dict | None = None) -> dict:
    health = health or get_health_score()
    risks = []

    score = health.get("score", 100)

    # Checkpoint dosyaları
    checkpoint_files = list(PROJECT_ROOT.glob("jarvis_core_checkpoint*.zip"))
    checkpoint_files += list(PROJECT_ROOT.glob("jarvis_*checkpoint*.zip"))

    if checkpoint_files:
        latest = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
        latest_age_hours = (datetime.now().timestamp() - latest.stat().st_mtime) / 3600

        if latest_age_hours > 24:
            risks.append({
                "level": "medium",
                "title": "Checkpoint eski",
                "detail": f"Son checkpoint yaklaşık {latest_age_hours:.1f} saat önce alınmış.",
                "suggestion": "Checkpoint Al",
            })
        else:
            risks.append({
                "level": "low",
                "title": "Checkpoint mevcut",
                "detail": f"Son checkpoint: {latest.name}",
                "suggestion": "Sorun yok",
            })
    else:
        risks.append({
            "level": "high",
            "title": "Checkpoint bulunamadı",
            "detail": "Geri dönüş noktası yok.",
            "suggestion": "Checkpoint Al",
        })

    if score <= 75:
        risks.append({
            "level": "medium" if score > 50 else "high",
            "title": "Sağlık skoru düştü",
            "detail": health.get("threshold_note", ""),
            "suggestion": "Sağlık Kontrolü",
        })

    tavily = _get_tavily_status()
    remaining = tavily.get("remaining")

    if isinstance(remaining, int) and remaining < 150:
        risks.append({
            "level": "medium",
            "title": "Tavily kredisi azalıyor",
            "detail": f"Kalan kredi: {remaining}/1000",
            "suggestion": "Web cache kullan",
        })

    if len(risks) == 0:
        risks.append({
            "level": "low",
            "title": "Risk düşük",
            "detail": "Belirgin risk bulunmadı.",
            "suggestion": "Çalışmaya devam",
        })

    return {
        "risks": risks[:5],
        "summary": risks[0]["title"] if risks else "Risk düşük",
    }


def get_today_context() -> dict:
    today = date.today()
    weekday_names = {
        0: "Pazartesi",
        1: "Salı",
        2: "Çarşamba",
        3: "Perşembe",
        4: "Cuma",
        5: "Cumartesi",
        6: "Pazar",
    }

    month_day = today.strftime("%m-%d")

    # İlk sürüm: sabit yerel önemli günler.
    # Sonra bunu calendar_context.json'a taşıyacağız.
    important_days = {
        "01-01": ["Yılbaşı"],
        "04-23": ["Ulusal Egemenlik ve Çocuk Bayramı"],
        "05-01": ["Emek ve Dayanışma Günü"],
        "05-19": ["Atatürk'ü Anma, Gençlik ve Spor Bayramı"],
        "07-15": ["Demokrasi ve Milli Birlik Günü"],
        "08-30": ["Zafer Bayramı"],
        "10-29": ["Cumhuriyet Bayramı"],
        "03-08": ["Dünya Kadınlar Günü"],
        "11-10": ["Atatürk'ü Anma Günü"],
        "07-26": ["AC/DC albüm ve rock tarihi için kontrol edilebilir gün"],
    }

    items = important_days.get(month_day, [])
    is_weekend = today.weekday() >= 5
    is_special = bool(items)

    if is_special:
        jarvis_note = f"Bugün önemli bir gün: {', '.join(items)}. Bunu hafife almak medeniyete ayıp olur efendim."
    elif is_weekend:
        jarvis_note = "Hafta sonu. Çalışacaksak bari bunu stratejik bir zafer gibi planlayalım efendim."
    else:
        jarvis_note = "Sıradan bir gün gibi görünüyor. Bu genelde en tehlikeli türdür; iyi planlanırsa çok iş çıkar."

    return {
        "date": today.isoformat(),
        "weekday": weekday_names[today.weekday()],
        "is_weekend": is_weekend,
        "important_days": items,
        "jarvis_note": jarvis_note,
    }


def get_daily_recommendation(health: dict | None = None) -> dict:
    health = health or get_health_score()
    hour = datetime.now().hour
    score = health.get("score", 100)

    if hour >= 1 and hour <= 5:
        return {
            "title": "Dinlenme önerisi",
            "text": "Saat ilerledi efendim. Verim düşerken hata oranı sessizce yükselir.",
            "action": "Çıkış Planı Yap",
        }

    if score <= 50:
        return {
            "title": "Sistem rahatlatma",
            "text": "Sağlık skoru düştü. Önce parazit kaynaklarını azaltmak mantıklı.",
            "action": "Sağlık Kontrolü",
        }

    if hour >= 21:
        return {
            "title": "Kapanış rutini",
            "text": "Günün sonuna yaklaşıyoruz. Checkpoint ve kısa özet iyi fikir.",
            "action": "Checkpoint Al",
        }

    return {
        "title": "Odak önerisi",
        "text": "90 dakikalık bir odak bloğu başlatmak için sistem uygun görünüyor.",
        "action": "Odak Modu",
    }


def get_model_efficiency() -> dict:
    """
    İlk sürüm: yerel ölçüm altyapısı için placeholder + mantıklı metrik.
    Sonra gerçek response time/token loglarından hesaplayacağız.
    """
    baseline_path = MEMORY_DIR / "model_efficiency_baseline.json"
    data = _read_json(baseline_path, {})

    if not data:
        data = {
            "baseline_month": datetime.now().strftime("%Y-%m"),
            "baseline_avg_response_sec": 8.0,
            "current_avg_response_sec": 8.0,
            "internet_dependency_start": 100,
            "internet_dependency_current": 100,
        }

        try:
            baseline_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    start = float(data.get("baseline_avg_response_sec", 8.0))
    current = float(data.get("current_avg_response_sec", start))

    if start <= 0:
        improvement = 0
    else:
        improvement = round(((start - current) / start) * 100, 1)

    internet_start = float(data.get("internet_dependency_start", 100))
    internet_current = float(data.get("internet_dependency_current", internet_start))

    if internet_start <= 0:
        internet_reduction = 0
    else:
        internet_reduction = round(((internet_start - internet_current) / internet_start) * 100, 1)

    return {
        "baseline_month": data.get("baseline_month"),
        "baseline_avg_response_sec": start,
        "current_avg_response_sec": current,
        "response_improvement_percent": improvement,
        "internet_dependency_reduction_percent": internet_reduction,
        "note": "Bu metrik ilk sürümde başlangıç çizgisi oluşturuyor. Zamanla gerçek loglardan beslenecek.",
    }


def get_learning_journal() -> dict:
    """
    İlk sürüm: profil ve son konuşma sayısından öğrenme izlenimi.
    Sonra explicit_memory kayıtlarını ayrı takip edeceğiz.
    """
    profile = _read_json(MEMORY_DIR / "user_profile.json", {})
    learned = []

    if profile.get("name"):
        learned.append(f"Kullanıcı adı: {profile.get('name')}")

    for key in ["sevdiği", "sevmediği", "takım", "kullandığı", "sahip olduğu"]:
        values = profile.get(key, [])
        if isinstance(values, list) and values:
            learned.append(f"{key}: {', '.join(values[:4])}")

    if not learned:
        learned.append("Kalıcı tercih verisi sınırlı. Explicit memory ile gelişecek.")

    return {
        "items": learned[:5],
        "count": len(learned),
    }


def get_command_suggestions(health: dict | None = None, risk: dict | None = None) -> dict:
    health = health or get_health_score()
    risk = risk or get_risk_radar(health)

    suggestions = []

    if health.get("score", 100) <= 75:
        suggestions.append("Sağlık Kontrolü")

    if any(r.get("suggestion") == "Checkpoint Al" for r in risk.get("risks", [])):
        suggestions.append("Checkpoint Al")

    suggestions.append("Kendini Test Et")

    now_hour = datetime.now().hour
    if now_hour >= 21:
        suggestions.append("Akşam Özeti")

    if len(suggestions) < 3:
        suggestions.append("Güncel Ara")

    # Sıralı ve tekrarsız
    suggestions = list(dict.fromkeys(suggestions))

    return {
        "primary": suggestions[:3],
        "all": suggestions[:6],
    }


def get_jarvis_comment(health: dict, risk: dict, today: dict) -> str:
    score = health.get("score", 100)
    hour = datetime.now().hour

    if score <= 25:
        return "Efendim, sistem sağlığı kritik. Önce çekirdeği rahatlatıp parazit kaynaklarını azaltmalıyız."

    if score <= 50:
        return "Sistem çalışıyor, fakat rahat değil. Bu noktada kahramanlık değil, temizlik kazandırır."

    if score <= 75:
        return "Sistem dikkat seviyesinde. Panik yok; ama riskleri görmezden gelirsek onlar da bizi görmezden gelmez."

    if hour >= 1 and hour <= 5:
        return "Efendim, sistem sakin; fakat saat ilerledi. Hata yapma ihtimaliniz benden hızlı yükseliyor."

    if today.get("important_days"):
        return today.get("jarvis_note", "Bugün dikkat edilmeye değer bir gün efendim.")

    if risk.get("risks") and risk["risks"][0].get("title") == "Checkpoint eski":
        return "Kod tarafı stabil, fakat UI değişikliklerinden önce checkpoint mantıklı olur."

    return "Sistem sakin. Bugün arayüz tasarımı için ideal durumdayız."


def get_core_state(health: dict | None = None) -> dict:
    health = health or get_health_score()
    score = health.get("score", 100)

    if score <= 25:
        mode = "critical"
        label = "Kritik"
    elif score <= 75:
        mode = "monitoring"
        label = "İzliyor"
    else:
        mode = "idle"
        label = "Hazır"

    return {
        "mode": mode,
        "label": label,
        "available_modes": ["hazır", "dinliyor", "düşünüyor", "konuşuyor", "araştırıyor"],
    }


def get_panel_intelligence() -> dict:
    system_status = get_system_status()
    health = get_health_score(system_status)
    risk = get_risk_radar(health)
    today = get_today_context()
    recommendation = get_daily_recommendation(health)
    memory = _get_memory_status()
    tavily = _get_tavily_status()
    model = get_model_efficiency()
    learning = get_learning_journal()
    suggestions = get_command_suggestions(health, risk)
    core = get_core_state(health)
    comment = get_jarvis_comment(health, risk, today)

    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "core": core,
        "system_status": system_status,
        "health": health,
        "risk_radar": risk,
        "today_context": today,
        "daily_recommendation": recommendation,
        "memory_status": memory,
        "web_research": tavily,
        "model_efficiency": model,
        "learning_journal": learning,
        "command_suggestions": suggestions,
        "jarvis_comment": comment,
    }


def format_panel_intelligence() -> str:
    data = get_panel_intelligence()

    lines = []
    lines.append("JARVIS PANEL ZEKÂSI")
    lines.append("=" * 40)
    lines.append(f"Core: {data['core']['label']} / {data['core']['mode']}")
    lines.append(f"Sağlık: %{data['health']['score']} — {data['health']['label']}")
    lines.append(f"JARVIS Yorumu: {data['jarvis_comment']}")

    lines.append("\nSistem:")
    sys = data["system_status"]
    lines.append(f"- CPU: %{sys['cpu_percent']}")
    lines.append(f"- RAM: %{sys['ram']['percent']} ({sys['ram']['used_gb']} / {sys['ram']['total_gb']} GB)")
    lines.append(f"- Disk: %{sys['disk']['percent']} ({sys['disk']['used_gb']} / {sys['disk']['total_gb']} GB)")

    gpu = sys["gpu"]
    if gpu.get("available"):
        lines.append(f"- GPU: %{gpu['percent']} | VRAM: %{gpu['memory_percent']} | Sıcaklık: {gpu['temperature']} °C")
    else:
        lines.append("- GPU: okunamadı veya nvidia-smi yok")

    lines.append("\nRisk Radar:")
    for r in data["risk_radar"]["risks"]:
        lines.append(f"- [{r['level']}] {r['title']}: {r['detail']}")

    lines.append("\nBugünkü Kontekst:")
    ctx = data["today_context"]
    lines.append(f"- Tarih: {ctx['date']} / {ctx['weekday']}")
    lines.append(f"- Önemli günler: {', '.join(ctx['important_days']) if ctx['important_days'] else 'Yok'}")
    lines.append(f"- Not: {ctx['jarvis_note']}")

    lines.append("\nÖneri:")
    rec = data["daily_recommendation"]
    lines.append(f"- {rec['title']}: {rec['text']}")
    lines.append(f"- Eylem: {rec['action']}")

    lines.append("\nWeb / Hafıza:")
    web = data["web_research"]
    mem = data["memory_status"]
    lines.append(f"- Tavily: {'aktif' if web['active'] else 'pasif'} | Kredi: {web['remaining']}/{web['limit']}")
    lines.append(f"- Hafıza kayıtları: {mem['total_known_records']} | Güven: {mem['confidence']}")

    lines.append("\nÖnerilen Komutlar:")
    for s in data["command_suggestions"]["primary"]:
        lines.append(f"- Önerilen: {s}")

    return "\n".join(lines)