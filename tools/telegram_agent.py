"""JARVIS Telegram Agent - B2.7B.

Safe polling bot for remote status checks.
No shell execution. No arbitrary task execution.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENV_PATH = ROOT / ".env"
MEMORY_DIR = ROOT / "memory"
TASK_QUEUE = MEMORY_DIR / "task_queue.json"
TASK_HISTORY = MEMORY_DIR / "task_history.json"


def load_env_file(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def env_list(name: str) -> set[str]:
    value = os.environ.get(name, "")
    return {item.strip() for item in value.split(",") if item.strip()}


def bot_token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN .env icinde yok.")
    return token


def api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{bot_token()}/{method}"


def telegram_get(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = api_url(method)
    if params:
        url += "?" + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url, timeout=35) as response:
        data = response.read().decode("utf-8", errors="replace")
        return json.loads(data)


def telegram_post(method: str, params: dict[str, Any]) -> dict[str, Any]:
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(api_url(method), data=data, method="POST")

    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def send_message(chat_id: int | str, text: str) -> None:
    telegram_post("sendMessage", {
        "chat_id": str(chat_id),
        "text": text[:3900],
        "disable_web_page_preview": "true",
    })


def safe_load_json(path: Path, fallback: Any) -> Any:
    try:
        if not path.exists():
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def is_allowed(user_id: int | str, text: str) -> bool:
    allowed = env_list("TELEGRAM_ALLOWED_USER_IDS")

    # Bootstrap mode: allow only /whoami and /help until allowlist is set.
    if not allowed:
        return text.startswith("/whoami") or text.startswith("/help")

    return str(user_id) in allowed


def cmd_help() -> str:
    return (
        "JARVIS Telegram Agent B2.7B\n\n"
        "Komutlar:\n"
        "/whoami - Telegram user ID gosterir\n"
        "/status - ajan ve proje durumu\n"
        "/health - lokal healthz kontrolu\n"
        "/tasks - gorev kuyrugu/gecmisi\n"
        "/brief - kisa JARVIS brifingi\n"
        "/brief_live - canli hava destekli JARVIS brifingi\n"
        "/memory - memory klasoru ozeti\n"
        "/project - proje/git/roadmap ozeti\n"
        "/project_state - C2 proje durum modelini gosterir\n"
        "/project_intel - C2 proje zekasi ve sonraki aksiyonu gosterir\n"
        "/report - proje raporu uretir\n"
        "/mem_status - C1 hafiza sistem durumunu gosterir\n"
        "/mem_candidates - hafiza adaylarini listeler\n"
        "/mem_approve <id> - hafiza adayini onaylar\n"
        "/mem_store <id> - onayli hafiza adayini uzun hafizaya yazar\n"
        "/mem_promote <id> - onayli sentez hafiza adayini uzun hafizaya yazar\n"
        "/mem_reject <id> - hafiza adayini reddeder\n"
        "/mem_defer <id> - hafiza adayini erteler\n"
        "/mem_expire - suresi gecen hafiza adaylarini expired yapar\n"
        "/audit - son audit olaylarini gosterir\n"
        "/audit_stats - audit olay sayilarini gosterir\n"
        "/web <soru> - guvenli web arastirmasi yapar\n"
        "/help - bu yardim\n\n"
        "Guvenlik: shell/cmd calistirma yok, sadece izinli user_id."
    )


def cmd_status() -> str:
    return (
        "JARVIS status\n"
        f"Zaman: {datetime.now().isoformat(timespec='seconds')}\n"
        f"Root: {ROOT}\n"
        f"Memory: {'var' if MEMORY_DIR.exists() else 'yok'}\n"
        f"Queue: {'var' if TASK_QUEUE.exists() else 'yok'}\n"
        f"History: {'var' if TASK_HISTORY.exists() else 'yok'}"
    )


def cmd_health() -> str:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/healthz", timeout=5) as response:
            body = response.read().decode("utf-8", errors="replace")
            return "Healthz:\n" + body[:1500]
    except Exception as exc:
        return f"Healthz alinamadi: {exc}"


def cmd_tasks() -> str:
    queue_items = safe_load_json(TASK_QUEUE, [])
    history_items = safe_load_json(TASK_HISTORY, [])

    if not isinstance(queue_items, list):
        queue_items = []
    if not isinstance(history_items, list):
        history_items = []

    done = sum(1 for item in history_items if item.get("status") == "done")
    failed = sum(1 for item in history_items if item.get("status") == "failed")

    recent_lines = []
    for item in history_items[-5:]:
        recent_lines.append(
            f"- {item.get('type', 'task')} | {item.get('status', '-')} | {item.get('finished', '-')}"
        )

    recent = "\n".join(recent_lines) if recent_lines else "son kayit yok"

    return (
        "Task ozeti\n"
        f"Bekleyen: {len(queue_items)}\n"
        f"Tamamlanan: {done}\n"
        f"Hata: {failed}\n\n"
        f"Son 5:\n{recent}"
    )





def _brief_time_context(now=None) -> dict:
    try:
        from datetime import datetime
        now = now or datetime.now()
        hour = int(getattr(now, "hour", 0))
    except Exception:
        hour = 12

    if 5 <= hour < 11:
        return {
            "mode": "morning",
            "title": "Gün başlangıcı",
            "opening": "Efendim, gün başlangıcı için kısa durum hazır.",
            "suggestion": "Bugün tek ana hedef seçersek günü daha temiz yönetiriz.",
        }

    if 11 <= hour < 17:
        return {
            "mode": "day",
            "title": "Durum kontrolü",
            "opening": "Efendim, kısa durum kontrolü hazır.",
            "suggestion": "Günün ortasında rota iyi görünüyor; tek sapmayı yakalamak yeterli.",
        }

    if 17 <= hour < 23:
        return {
            "mode": "evening",
            "title": "Akşam değerlendirmesi",
            "opening": "Efendim, akşam için kısa durum hazır.",
            "suggestion": "Günün kısa özetini almak ve yarına tek not bırakmak iyi olur.",
        }

    return {
        "mode": "night",
        "title": "Gece çalışma modu",
        "opening": "Efendim, gece modu için kısa durum hazır.",
        "suggestion": "Yeni özellik açmak yerine checkpoint almak daha akıllıca olur.",
    }


def _brief_should_replace_generic_title(title: str) -> bool:
    low = str(title or "").lower()
    if not low.strip():
        return True

    # Turkish mojibake/ASCII-safe generic title detection.
    generic = [
        "kapanış değerlendirmesi",
        "kapanis degerlendirmesi",
        "kapan",
        "değerlendirmesi",
        "degerlendirmesi",
        "değerlendirmesi",
        "sabah brifingi",
        "canl? brifing",
        "canli brifing",
        "canl? brifing",
        "brifing",
    ]
    return any(x in low for x in generic)

def _brief_should_replace_generic_suggestion(suggestion: dict) -> bool:
    title = str((suggestion or {}).get("title") or "").lower()
    body = str((suggestion or {}).get("text") or "").lower()
    joined = title + " " + body

    # Turkish mojibake/ASCII-safe generic suggestion detection.
    generic = [
        "kapanış",
        "kapanis",
        "kapan",
        "gün özeti",
        "gun ozeti",
        "gün",
        "özet",
        "ozet",
        "özet",
        "adım",
        "adim",
        "adım",
        "odak",
        "tek ana hedef",
        "kaydetmek",
    ]
    return any(x in joined for x in generic) or not joined.strip()

def _brief_loc(profile: dict, weather: dict | None = None) -> str:
    weather = weather or {}
    loc = weather.get("default_location")
    if loc:
        return str(loc)
    city = profile.get("city")
    district = profile.get("district")
    return "/".join([x for x in [city, district] if x])


def _brief_factor_words(factors) -> list[str]:
    if not isinstance(factors, list):
        return []

    mapping = {
        "precip_probability": "yağış ihtimali",
        "heavy_precip_probability": "yüksek yağış ihtimali",
        "light_precip_probability": "hafif yağış ihtimali",
        "rain": "yağmur",
        "strong_wind": "kuvvetli rüzgâr",
        "moderate_wind": "rüzgâr",
        "dangerous_wind": "tehlikeli rüzgâr",
        "critical_alert": "kritik hava uyarısı",
        "snow": "kar",
        "freezing_temperature": "don riski",
        "very_cold": "çok soğuk",
        "high_heat": "yüksek sıcaklık",
        "extreme_heat": "aşırı sıcak",
        "low_visibility": "düşük görüş",
    }
    return [mapping.get(str(x), str(x)) for x in factors]


def _brief_ride_sentence(ride_risk: dict, weather: dict, loc: str) -> str:
    level = str(ride_risk.get("level", "none")).lower()
    status = str(ride_risk.get("status", "")).lower()
    factors = _brief_factor_words(ride_risk.get("factors") or [])

    if status == "pending":
        return "Canlı hava şu an kapalı. Güncel hava ve motosiklet riski için /brief_live kullanabilirsiniz."

    if level == "critical":
        return f"{loc} için hava motosiklet adına iyi görünmüyor. Bu sürüşü önermiyorum; alternatif ulaşım daha doğru olur."

    if level == "high":
        if "yağış ihtimali" in factors and "kuvvetli rüzgâr" in factors:
            return f"{loc} için güncel hava alındı. Yağış ihtimali ve kuvvetli rüzgâr birlikte motosiklet için gereksiz risk oluşturuyor. Bugün motor yerine alternatif ulaşım daha akıllıca olur."
        if "yağmur" in factors:
            return f"{loc} için güncel hava alındı. Yağmur motosiklet tarafında riski yükseltiyor; çıkmadan önce rota ve ekipmanı kontrol etmek iyi olur."
        return f"{loc} için motosiklet riski yüksek görünüyor. Alternatif ulaşımı ciddi şekilde değerlendirmek mantıklı."

    if level == "medium":
        return f"{loc} için motosiklet kullanılabilir, ama dikkat istiyor. Çıkmadan önce rüzgârı, yağışı ve ekipmanı kontrol edin."

    if level == "low":
        return f"{loc} için belirgin bir sorun yok. Yine de ekipmanı ihmal etmeyin."

    return f"{loc} için motosiklet adına özel bir risk görünmüyor."


def _brief_alert_sentence(proactive: dict) -> str:
    alerts = proactive.get("alerts") or []
    if not isinstance(alerts, list) or not alerts:
        return "Sistem tarafında kritik bir sorun görünmüyor."

    task_count = 0
    security = False
    critical = False
    other = []

    for item in alerts:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", ""))
        level = str(item.get("level", "")).lower()
        title = str(item.get("title", "")).strip()
        text = str(item.get("text", "")).strip()

        if code == "task_failures":
            task_count += 1
        elif "security" in code:
            security = True
        elif level == "critical":
            critical = True
            other.append(text or title)
        else:
            other.append(text or title)

    if critical:
        return "Dikkat isteyen kritik bir sistem uyarısı var. Ağır işlem başlatmadan önce kontrol etmek daha güvenli olur."

    if security:
        return "Güvenlik tarafında dikkat isteyen bir sinyal var. Uygun olduğunuzda güvenlik durumunu kontrol edelim."

    if task_count and len(alerts) == task_count:
        return "Sistem tarafında kritik bir sorun görünmüyor. Yalnız görev geçmişinde bir hata var; uygun olduğunuzda bakarız."

    if other:
        return "Sistem tarafında küçük bir uyarı var. Acil görünmüyor, ama gözden kaçırmayalım."

    return "Sistem tarafında kritik bir sorun görünmüyor."


def _brief_suggestion_sentence(suggestion: dict) -> str:
    title = str(suggestion.get("title") or "").lower()
    text = str(suggestion.get("text") or "").strip()
    time_ctx = _brief_time_context()

    if _brief_should_replace_generic_suggestion(suggestion):
        return time_ctx.get("suggestion", "Tek bir ana hedef seçersek daha temiz ilerleriz.")

    if text:
        return text

    return time_ctx.get("suggestion", "Tek bir ana hedef seçersek daha temiz ilerleriz.")


def _brief_safe(value, default="-") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _brief_clip(text: str, limit: int = 3600) -> str:
    text = str(text or "")
    if len(text) <= limit:
        return text
    return text[:limit - 80].rstrip() + "\n\n[Kesildi: Telegram mesaj limiti icin kisaltildi.]"


def cmd_brief(state: dict | None = None) -> str:
    """E1.5B.3 — ProactiveCore state'ini JARVIS tonunda kısa Telegram brifingine cevirir.

    İçeride teknik state korunur; kullanıcıya teknik log değil, kısa karar özeti gösterilir.
    /brief web'e çıkmaz. /brief_live ayrı komuttur.
    """
    try:
        if state is None:
            from agents.proactive_core import ProactiveCore
            state = ProactiveCore().build_state()

        if not isinstance(state, dict):
            return "Briefing alınamadı: state formatı geçersiz."

        profile = state.get("profile", {}) if isinstance(state.get("profile"), dict) else {}
        briefing = state.get("briefing", {}) if isinstance(state.get("briefing"), dict) else {}
        proactive = state.get("proactive", {}) if isinstance(state.get("proactive"), dict) else {}
        weather = state.get("weather", {}) if isinstance(state.get("weather"), dict) else {}
        ride_risk = state.get("ride_risk", {}) if isinstance(state.get("ride_risk"), dict) else {}
        suggestion = state.get("suggestion", {}) if isinstance(state.get("suggestion"), dict) else {}

        loc = _brief_loc(profile, weather)
        time_ctx = _brief_time_context()
        title = str(briefing.get("title") or "").strip()
        brief_text = str(briefing.get("text") or "").strip()

        if _brief_should_replace_generic_title(title):
            original_title = title
            title = time_ctx.get("title", title)
            if brief_text and _brief_should_replace_generic_suggestion({"title": original_title, "text": brief_text}):
                brief_text = ""

        lines = [
            "JARVIS Briefing",
            "",
            time_ctx.get("opening", "Efendim, kısa durum hazır."),
            "",
        ]

        if loc:
            lines.append(f"Konum: {loc}")
            lines.append("")

        if title or brief_text:
            if title:
                lines.append(title)
            if brief_text:
                lines.append(brief_text)
            lines.append("")

        ride_sentence = _brief_ride_sentence(ride_risk, weather, loc or "Konum")
        if ride_sentence:
            lines.append(ride_sentence)
            lines.append("")

        alert_sentence = _brief_alert_sentence(proactive)
        if alert_sentence:
            lines.append(alert_sentence)
            lines.append("")

        suggestion_sentence = _brief_suggestion_sentence(suggestion)
        if suggestion_sentence:
            lines.append(suggestion_sentence)
            lines.append("")

        lines.append("Not: Bu brifing sadece durumu özetler; siz istemeden otomatik işlem yapmaz.")

        return _brief_clip("\n".join(lines))

    except Exception as e:
        return f"Briefing alınamadı: {type(e).__name__}: {str(e)[:500]}"


def cmd_brief_live(state: dict | None = None) -> str:
    """E1.5B — Canlı hava destekli Telegram brifingi.

    /brief güvenli kalır ve web'e çıkmaz.
    /brief_live ise kullanıcı açıkça istediği için live_weather=True kullanır.
    WebResearcher D2.4 cache/rate-limit korumasından geçer.
    """
    try:
        if state is None:
            from agents.proactive_core import ProactiveCore
            state = ProactiveCore(live_weather=True).build_state()

        msg = cmd_brief(state)
        return msg.replace(
            "Not: Bu brifing sadece durumu özetler; siz istemeden otomatik işlem yapmaz.",
            "Not: Canlı hava D2.4 cache/rate-limit korumasıyla alındı; otomatik push yapılmadı."
        )

    except Exception as e:
        return f"Canlı briefing alınamadı: {type(e).__name__}: {str(e)[:500]}"


def cmd_audit(limit: int = 6) -> str:
    try:
        from agents.audit_logger import AuditLogger

        a = AuditLogger()
        items = a.tail(limit)

        if not items:
            return "Audit kaydi yok."

        lines = ["Son audit olaylari:", ""]

        for item in items:
            payload = item.get("payload", {}) or {}
            lines.extend([
                f"Time: {item.get('timestamp')}",
                f"Event: {item.get('event')}",
                f"Action: {item.get('action')}",
                f"Candidate: {item.get('candidate_id') or '-'}",
                f"QueryHash: {item.get('query_hash')}",
            ])

            status = payload.get("status")
            tier = payload.get("tier")
            confidence = payload.get("confidence")

            if status or tier or confidence is not None:
                lines.append(f"Meta: status={status} tier={tier} confidence={confidence}")

            urls = payload.get("source_urls") or []
            if urls:
                lines.append(f"Source: {urls[0]}")

            reason = payload.get("reason")
            if reason:
                lines.append(f"Reason: {reason}")

            lines.append("")

        return "\n".join(lines).strip()
    except Exception as exc:
        return f"Audit okunamadi: {exc}"


def cmd_audit_stats() -> str:
    try:
        from agents.audit_logger import AuditLogger

        a = AuditLogger()
        stats = a.stats()
        events = stats.get("events", {}) or {}

        lines = [
            "Audit istatistikleri:",
            f"Toplam: {stats.get('total', 0)}",
            "",
        ]

        if not events:
            lines.append("Event yok.")
        else:
            for name, count in sorted(events.items()):
                lines.append(f"- {name}: {count}")

        return "\n".join(lines)
    except Exception as exc:
        return f"Audit istatistikleri okunamadi: {exc}"


def _format_memory_candidate_item(item: dict) -> list[str]:
    """Format one memory candidate for Telegram display.

    C1.2C: shows conversation-derived memory route fields when present.
    """
    summary = str(item.get("summary", "")).strip()
    if len(summary) > 280:
        summary = summary[:280].rstrip() + "..."

    route = item.get("route") if isinstance(item.get("route"), dict) else {}

    source_type = item.get("source_type") or route.get("source") or "-"
    memory_type = item.get("memory_type") or route.get("memory_type") or "-"
    storage_target = item.get("storage_target") or route.get("storage_target") or "-"
    sensitivity = item.get("sensitivity") or route.get("sensitivity") or "-"
    action = route.get("action") or "-"
    tags = item.get("tags") or []
    if isinstance(tags, list):
        tag_text = ", ".join(str(t) for t in tags[:6])
    else:
        tag_text = str(tags)

    lines = [
        f"ID: {item.get('id')}",
        f"Source: {source_type} | Type: {memory_type} -> {storage_target}",
        f"Sensitivity: {sensitivity} | Action: {action}",
        f"Tier: {item.get('tier')} | Confidence: {item.get('confidence')}",
        f"Expires: {item.get('expires_at')}",
    ]

    status = item.get("status")
    user_decision = item.get("user_decision")
    if status or user_decision:
        lines.append(f"Status: {status or '-'} | Decision: {user_decision or '-'}")

    proposal_type = item.get("proposal_type")
    theme = item.get("theme")
    source_count = item.get("source_count")
    if proposal_type or theme or source_count is not None:
        lines.append(f"Proposal: {proposal_type or '-'} | Theme: {theme or '-'} | Sources: {source_count if source_count is not None else '-'}")

    source_ids = item.get("source_ids")
    if isinstance(source_ids, list) and source_ids:
        source_id_text = ", ".join(str(source_id) for source_id in source_ids[:8])
        if len(source_ids) > 8:
            source_id_text += ", ..."
        lines.append(f"Source IDs: {source_id_text}")

    if tag_text:
        lines.append(f"Tags: {tag_text}")

    lines.extend([
        f"Ozet: {summary}",
        "",
    ])

    return lines


def cmd_memory_status() -> str:
    """Show C1 memory system status."""
    try:
        from agents.memory_candidate_queue import MemoryCandidateQueue

        q = MemoryCandidateQueue()
        stats = q.stats()
        counts = stats.get("counts", {}) if isinstance(stats.get("counts"), dict) else {}
        pending = q.list_pending(limit=3)

        vector_total = "unavailable"
        try:
            from tools.vector_memory import VectorMemory

            vector_total = VectorMemory().stats().get("total", 0)
        except Exception as exc:
            vector_total = f"unavailable ({str(exc)[:60]})"

        modules = {
            "MemoryPolicy": False,
            "MemorySchemaMapper": False,
            "MemoryRetrievalPolicy": False,
            "MemoryCandidateQueue": True,
        }

        try:
            from agents.memory_policy import MemoryPolicy
            modules["MemoryPolicy"] = MemoryPolicy is not None
        except Exception:
            pass

        try:
            from agents.memory_schema import MemorySchemaMapper
            modules["MemorySchemaMapper"] = MemorySchemaMapper is not None
        except Exception:
            pass

        try:
            from agents.memory_retrieval_policy import MemoryRetrievalPolicy
            modules["MemoryRetrievalPolicy"] = MemoryRetrievalPolicy is not None
        except Exception:
            pass

        lines = [
            "C1 Hafiza Sistem Durumu",
            "",
            f"Vector memory: {vector_total}",
            f"Candidate total: {stats.get('total', 0)}",
            f"Pending: {stats.get('pending', 0)}",
            f"Stored: {counts.get('stored', 0)}",
            f"Rejected: {counts.get('rejected', 0)}",
            f"Deferred: {counts.get('deferred', 0)}",
            f"Expired: {counts.get('expired', 0)}",
            "",
            "Moduller:",
        ]

        for name, ok in modules.items():
            lines.append(f"- {name}: {'OK' if ok else 'YOK'}")

        if pending:
            lines.extend(["", "Son pending adaylar:"])
            for item in pending:
                route = item.get("route") if isinstance(item.get("route"), dict) else {}
                memory_type = item.get("memory_type") or route.get("memory_type") or "-"
                storage_target = item.get("storage_target") or route.get("storage_target") or "-"
                sensitivity = item.get("sensitivity") or route.get("sensitivity") or "-"
                summary = str(item.get("summary") or "").strip()
                if len(summary) > 120:
                    summary = summary[:120].rstrip() + "..."

                lines.extend([
                    f"- ID: {item.get('id')}",
                    f"  Source: {item.get('source_type')} | Type: {memory_type}->{storage_target} | Sens: {sensitivity}",
                    f"  Ozet: {summary}",
                ])

        lines.extend([
            "",
            "Komutlar: /mem_candidates | /mem_expire | /mem_approve <id> | /mem_store <id> | /mem_promote <id>",
        ])

        return "\n".join(lines)
    except Exception as exc:
        return f"Hafiza sistem durumu alinamadi: {exc}"


def cmd_memory_candidates() -> str:
    try:
        from agents.memory_candidate_queue import MemoryCandidateQueue

        q = MemoryCandidateQueue()
        pending = q.list_pending(limit=5)
        stats = q.stats()

        if not pending:
            return (
                "Bekleyen hafiza adayi yok.\n"
                f"Toplam: {stats.get('total', 0)} | Pending: {stats.get('pending', 0)}"
            )

        lines = [
            "Bekleyen hafiza adaylari:",
            f"Toplam: {stats.get('total', 0)} | Pending: {stats.get('pending', 0)}",
            "",
        ]

        for item in pending:
            lines.extend(_format_memory_candidate_item(item))

        lines.append("Komutlar:")
        lines.append("/mem_approve <id>")
        lines.append("/mem_store <id>")
        lines.append("/mem_promote <id>")
        lines.append("/mem_reject <id>")
        lines.append("/mem_defer <id>")

        return "\n".join(lines)
    except Exception as exc:
        return f"Hafiza adaylari alinamadi: {exc}"


def cmd_memory_candidate_store(text: str) -> str:
    """Store an already-approved memory candidate into long-term memory.

    C1.6E-2B: /mem_store is a separate write gate. It does not approve pending
    candidates by itself; the candidate must already be approved.
    """
    try:
        from agents.memory_candidate_queue import MemoryCandidateQueue
        from agents.memory_candidate_writer import MemoryCandidateWriter

        parts = text.split()
        if len(parts) < 2:
            return "Kullanim: /mem_store <candidate_id>"

        candidate_id = parts[1].strip()
        q = MemoryCandidateQueue()
        candidate = q.get(candidate_id)

        if not candidate:
            return (
                "Islem basarisiz: candidate bulunamadi.\n"
                f"ID: {candidate_id}"
            )

        status = candidate.get("status")
        if status != "approved":
            return (
                "Hafiza adayi henuz uzun hafizaya yazilamaz.\n"
                f"ID: {candidate_id}\n"
                f"Status: {status}\n"
                "Once /mem_approve <id> ile onaylayin."
            )

        writer = MemoryCandidateWriter()
        result = writer.approve_and_store(candidate_id)

        if result.get("stored"):
            return (
                "Hafiza adayi uzun hafizaya yazildi.\n"
                f"ID: {candidate_id}\n"
                "Status: stored\n"
                f"Policy: {(result.get('policy') or {}).get('action')}"
            )

        return (
            "Hafiza adayi uzun hafizaya yazilmadi.\n"
            f"ID: {candidate_id}\n"
            f"Neden: {result.get('error')}"
        )
    except Exception as exc:
        return f"Hafiza adayi store islemi basarisiz: {exc}"


def cmd_memory_expire() -> str:
    """Expire old memory candidates without deleting data."""
    try:
        from agents.memory_candidate_queue import MemoryCandidateQueue

        q = MemoryCandidateQueue()
        before = q.stats()
        result = q.expire_old()
        after = q.stats()

        expired_ids = result.get("expired_ids", [])
        lines = [
            "Hafiza aday TTL temizligi tamamlandi.",
            f"Degisen: {result.get('changed', 0)}",
            f"Once pending: {before.get('pending', 0)}",
            f"Sonra pending: {after.get('pending', 0)}",
        ]

        if expired_ids:
            lines.append("Expired ID:")
            lines.extend(f"- {cid}" for cid in expired_ids[:10])
            if len(expired_ids) > 10:
                lines.append(f"... +{len(expired_ids) - 10} daha")

        lines.append("Not: Kayitlar silinmedi; sadece expired durumuna alindi.")
        return "\n".join(lines)
    except Exception as exc:
        return f"Hafiza aday TTL temizligi basarisiz: {exc}"


def cmd_memory_candidate_promote(text: str) -> str:
    """Promote an approved synthesized memory candidate into long-term memory.

    C1.6E-3D: /mem_promote is separate from /mem_store.
    It uses MemorySynthesisPromoter and is intended for synthesized_memory
    candidates that already passed review/approval.
    """
    try:
        parts = text.split()
        if len(parts) < 2:
            return "Kullanim: /mem_promote <candidate_id>"

        candidate_id = parts[1].strip()

        promoter_cls = globals().get("MemorySynthesisPromoter")
        if promoter_cls is None:
            from agents.memory_synthesis_promoter import MemorySynthesisPromoter as promoter_cls

        promoter = promoter_cls()
        result = promoter.promote(candidate_id)

        if result.get("promoted"):
            return (
                "Sentez hafiza adayi uzun hafizaya yazildi.\n"
                f"ID: {candidate_id}\n"
                "Status: stored\n"
                f"Vector ID: {result.get('vector_doc_id')}"
            )

        return (
            "Sentez hafiza adayi uzun hafizaya yazilmadi.\n"
            f"ID: {candidate_id}\n"
            f"Sebep: {result.get('reason', 'unknown')}"
        )

    except Exception as exc:
        return f"Sentez hafiza promote islemi basarisiz: {exc}"


def cmd_memory_candidate_decide(text: str, decision: str) -> str:
    try:
        from agents.memory_candidate_queue import MemoryCandidateQueue

        parts = text.split()
        if len(parts) < 2:
            return f"Kullanim: /mem_{decision} <candidate_id>"

        candidate_id = parts[1].strip()

        if decision == "approve":
            from agents.memory_candidate_writer import MemoryCandidateWriter

            writer = MemoryCandidateWriter()
            result = writer.approve_and_store(candidate_id)

            if result.get("stored"):
                return (
                    "Hafiza adayi onaylandi ve uzun hafizaya yazildi.\n"
                    f"ID: {candidate_id}\n"
                    "Status: stored\n"
                    f"Policy: {(result.get('policy') or {}).get('action')}"
                )

            return (
                "Hafiza adayi onaylandi fakat uzun hafizaya yazilmadi.\n"
                f"ID: {candidate_id}\n"
                f"Neden: {result.get('error')}\n"
                "Not: Guvenlik/policy nedeniyle otomatik yazim engellenmis olabilir."
            )

        q = MemoryCandidateQueue()

        result = q.decide(candidate_id, {
            "reject": "rejected",
            "defer": "deferred",
        }[decision])

        if not result.get("ok"):
            return f"Islem basarisiz: {result.get('error')}"

        candidate = result.get("candidate", {})
        return (
            f"Hafiza adayi guncellendi.\n"
            f"ID: {candidate.get('id')}\n"
            f"Status: {candidate.get('status')}\n"
            f"Not: Uzun hafizaya yazilmadi."
        )
    except Exception as exc:
        return f"Hafiza adayi guncellenemedi: {exc}"


def cmd_web(text: str) -> str:
    """D2.1 — Guvenli web arastirmasi.

    WebResearchPolicy ile karar verir.
    Hassas / yerel sorgular bloklanir.
    Araştırma sonucu MemoryCandidateQueue'ya pending_review olarak duser.
    Uzun hafizaya otomatik yazilmaz.
    """
    # Sorguyu ayikla
    parts = text.strip().split(None, 1)
    query = parts[1].strip() if len(parts) > 1 else ""

    if not query:
        return (
            "Kullanim: /web <soru>\n"
            "Ornek: /web Izmir hava durumu bugun\n\n"
            "Not: Yerel dosya sorgusu, hassas veri veya .env "
            "iceren sorgular guvenlik politikasi ile bloklanir."
        )

    try:
        from agents.web_research_policy import WebResearchPolicy
        from tools.web_research import WebResearcher
        from agents.memory_candidate_queue import MemoryCandidateQueue
        from agents.audit_logger import AuditLogger
    except ImportError as exc:
        return f"Modul hatasi: {exc}\nBu modul yuklu degil."

    policy = WebResearchPolicy()
    audit  = AuditLogger()
    queue  = MemoryCandidateQueue()

    # Policy karar
    try:
        decision = policy.decide(query)

        if hasattr(decision, "to_dict"):
            decision = decision.to_dict()
    except Exception as exc:
        return f"Policy hatasi: {exc}"

    if not decision.get("allow"):
        reason = decision.get("reason", "bilinmiyor")
        audit.log(
            event="web_policy_blocked",
            action="blocked",
            payload={"query": query[:200], "reason": reason},
        )
        return (
            f"Bu sorgu web arastirmasina izin vermiyor efendim.\n"
            f"Neden: {reason}\n\n"
            "Yerel dosya, kod ve hassas veri sorguları bloklanır."
        )

    # Arastirma
    researcher = WebResearcher()
    try:
        research = researcher.research_and_learn(query)
    except Exception as exc:
        audit.log(
            event="web_research_error",
            action="error",
            payload={"query": query[:200], "error": str(exc)[:200]},
        )
        return f"Arastirma sirasinda hata olustu efendim: {exc}"

    if not research or len(research.strip()) < 20:
        audit.log(
            event="web_research_empty",
            action="empty",
            payload={"query": query[:200]},
        )
        return "Efendim, bu sorgu icin güvenilir kaynak bulunamadi."

    # Source scores (varsa)
    source_scores = getattr(researcher, "last_source_scores", []) or []

    # Candidate queue'ya ekle (pending_review)
    try:
        candidate = queue.add_web_candidate(
            query=query,
            research_text=research,
            source_scores=source_scores,
            mode="sync",
            ttl_days=60,
            tags=["web_research", "telegram", "needs_user_review"],
        )
        candidate_id = candidate.get("id") if isinstance(candidate, dict) else None
    except Exception as exc:
        candidate_id = None
        audit.log(
            event="web_candidate_queue_error",
            action="error",
            payload={"query": query[:200], "error": str(exc)[:200]},
        )

    # Audit log
    audit.log(
        event="web_candidate_queued",
        action="queued",
        candidate_id=candidate_id,
        payload={
            "query": query[:200],
            "research_len": len(research),
            "source_count": len(source_scores),
            "tier": decision.get("tier"),
            "confidence": decision.get("confidence"),
        },
    )

    # Telegram cevabi: kisa ve kaynakli
    import re
    blocks = re.split(r"\n\s*\[\d+\]\s+", research)
    lines  = ["Efendim, web arastirmasi tamamlandi:\n"]

    for block in blocks[:3]:
        block = block.strip()
        if not block:
            continue
        title_m  = re.search(r"Baslik:\s*(.+)",  block)
        source_m = re.search(r"Kaynak:\s*(.+)",  block)
        summary_m= re.search(r"Ozet:\s*(.+)",    block, re.DOTALL)

        title  = title_m.group(1).strip()[:120]  if title_m  else ""
        source = source_m.group(1).strip()[:100] if source_m else ""
        summary= summary_m.group(1).strip()      if summary_m else ""
        summary= re.sub(r"\s+", " ", summary)[:260]

        if not title and not summary:
            continue

        entry = []
        if title:
            entry.append(f"• {title}")
        if summary:
            entry.append(f"  {summary}")
        if source:
            entry.append(f"  Kaynak: {source}")

        lines.append("\n".join(entry))

    if len(lines) == 1:
        lines.append("Kaynak bölümü cözümlenemedi; ham sonuc ekte.")
        lines.append(research[:600])

    footer = "\n\nNot: Sonuc uzun hafizaya yazilmadi."
    if candidate_id:
        footer += f"\nMemory aday ID: {candidate_id}"
        footer += "\n/mem_approve ile onaylayabilirsiniz."

    return "\n".join(lines) + footer


def cmd_project_state() -> str:
    """Show C2 project state summary."""
    try:
        from agents.project_state import ProjectStateStore

        store = ProjectStateStore()
        state = store.refresh()
        summary = store.summary()

        lines = [
            "C2 Proje Durumu",
            "",
            summary,
            "",
            f"Updated: {state.get('updated_at')}",
            "",
            "Komutlar: /project | /report | /mem_status",
        ]

        return "\n".join(lines)
    except Exception as exc:
        return f"Proje durum modeli alinamadi: {exc}"


def cmd_project_intel() -> str:
    """Show C2 project intelligence summary and next action."""
    try:
        from agents.project_summarizer import ProjectSummarizer
        from agents.roadmap_detector import RoadmapDetector
        from agents.next_action_planner import NextActionPlanner

        summary = ProjectSummarizer().summarize()
        roadmap = RoadmapDetector().detect()
        plan = NextActionPlanner().plan()

        lines = [
            "C2 Proje Zekasi",
            "",
            f"Project: {summary.project}",
            f"Current phase: {summary.current_phase}",
            f"Last completed: {summary.last_completed_phase}",
            f"Branch: {summary.branch}",
            f"Git clean: {'yes' if summary.git_clean else 'no'}",
            f"Roadmap confidence: {roadmap.confidence}/100",
            "",
            f"Next phase: {roadmap.next_phase}",
            f"Recommended action: {plan.recommended_action}",
            f"Reason: {plan.reason}",
            "",
            "Acceptance criteria:",
        ]

        for item in plan.acceptance_criteria[:6]:
            lines.append(f"- {item}")

        risks = list(dict.fromkeys((roadmap.risks or []) + (plan.risks or []) + (summary.risks or [])))
        if risks:
            lines.extend(["", "Risks:"])
            for risk in risks[:6]:
                lines.append(f"- {risk}")

        if roadmap.evidence:
            lines.extend(["", "Evidence:"])
            for item in roadmap.evidence[:5]:
                lines.append(f"- {item}")

        lines.extend([
            "",
            "Komutlar: /project_state | /project | /report | /mem_status",
        ])

        return "\n".join(lines)
    except Exception as exc:
        return f"Proje zekasi alinamadi: {exc}"


def cmd_report() -> str:
    try:
        from agents.project_reporter import ProjectReporter

        reporter = ProjectReporter()
        out = reporter.save_report()
        report = reporter.build_report()

        summary_lines = []
        capture = False
        for line in report.splitlines():
            if line.startswith("## 1. Executive Summary"):
                capture = True
                continue
            if capture and line.startswith("## 2. "):
                break
            if capture and line.strip():
                summary_lines.append(line)

        summary = "\n".join(summary_lines[:8]).strip() or "Ozet alinamadi."

        return (
            "Project report uretildi.\n"
            f"Dosya: {out}\n\n"
            "Kisa ozet:\n"
            f"{summary}"
        )
    except Exception as exc:
        return f"Project report uretilemedi: {exc}"


def cmd_project() -> str:
    try:
        from agents.project_intelligence import ProjectIntelligence

        return ProjectIntelligence().brief()
    except Exception as exc:
        return f"Project intelligence alinamadi: {exc}"


def cmd_memory() -> str:
    if not MEMORY_DIR.exists():
        return "Memory klasoru yok."

    files = []
    for path in sorted(MEMORY_DIR.glob("*.json"))[:50]:
        try:
            size = path.stat().st_size
        except Exception:
            size = 0
        files.append(f"- {path.name}: {size} byte")

    return "Memory dosyalari:\n" + ("\n".join(files) if files else "json dosya yok")


def handle_message(message: dict[str, Any]) -> None:
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    user_id = sender.get("id")
    text = str(message.get("text") or "").strip()

    if not chat_id or not user_id or not text:
        return

    if not is_allowed(user_id, text):
        send_message(chat_id, "Yetkisiz kullanici. /whoami ile ID al, sonra allowlist'e ekle.")
        return

    if text.startswith("/whoami"):
        username = sender.get("username") or "-"
        name = " ".join(str(sender.get(k) or "") for k in ("first_name", "last_name")).strip()
        send_message(chat_id, f"Telegram user_id: {user_id}\nusername: @{username}\nname: {name}")
    elif text.startswith("/help"):
        send_message(chat_id, cmd_help())
    elif text.startswith("/status"):
        send_message(chat_id, cmd_status())
    elif text.startswith("/health"):
        send_message(chat_id, cmd_health())
    elif text.startswith("/tasks"):
        send_message(chat_id, cmd_tasks())
    elif text.startswith("/brief_live"):
        send_message(chat_id, cmd_brief_live())
    elif text.startswith("/brief"):
        send_message(chat_id, cmd_brief())
    elif text.startswith("/memory"):
        send_message(chat_id, cmd_memory())
    elif text.startswith("/mem_status"):
        send_message(chat_id, cmd_memory_status())
    elif text.startswith("/project_intel"):
        send_message(chat_id, cmd_project_intel())
    elif text.startswith("/project_state"):
        send_message(chat_id, cmd_project_state())
    elif text.startswith("/project"):
        send_message(chat_id, cmd_project())
    elif text.startswith("/report"):
        send_message(chat_id, cmd_report())
    elif text == "/web" or text.startswith("/web "):
        send_message(chat_id, cmd_web(text))
    elif text.startswith("/mem_candidates"):
        send_message(chat_id, cmd_memory_candidates())
    elif text.startswith("/mem_approve"):
        send_message(chat_id, cmd_memory_candidate_decide(text, "approve"))
    elif text.startswith("/mem_store"):
        send_message(chat_id, cmd_memory_candidate_store(text))
    elif text.startswith("/mem_promote"):
        send_message(chat_id, cmd_memory_candidate_promote(text))
    elif text.startswith("/mem_reject"):
        send_message(chat_id, cmd_memory_candidate_decide(text, "reject"))
    elif text.startswith("/mem_defer"):
        send_message(chat_id, cmd_memory_candidate_decide(text, "defer"))
    elif text.startswith("/mem_expire"):
        send_message(chat_id, cmd_memory_expire())
    elif text.startswith("/audit_stats"):
        send_message(chat_id, cmd_audit_stats())
    elif text.startswith("/audit"):
        send_message(chat_id, cmd_audit())
    else:
        send_message(chat_id, "Bilinmeyen komut. /help yaz.")


def main() -> None:
    load_env_file()
    offset = 0

    print("JARVIS Telegram Agent basladi.")
    print("Allowlist:", ",".join(sorted(env_list("TELEGRAM_ALLOWED_USER_IDS"))) or "BOOTSTRAP")

    while True:
        try:
            payload = telegram_get("getUpdates", {
                "offset": offset,
                "timeout": 25,
                "allowed_updates": json.dumps(["message"]),
            })

            for update in payload.get("result", []):
                offset = max(offset, int(update.get("update_id", 0)) + 1)
                message = update.get("message")
                if isinstance(message, dict):
                    handle_message(message)

        except KeyboardInterrupt:
            print("Telegram agent durduruldu.")
            return
        except Exception as exc:
            print("Telegram agent hata:", exc)
            time.sleep(5)


if __name__ == "__main__":
    main()
