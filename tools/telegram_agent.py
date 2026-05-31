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
        "/memory - memory klasoru ozeti\n"
        "/project - proje/git/roadmap ozeti\n"
        "/report - proje raporu uretir\n"
        "/mem_candidates - hafiza adaylarini listeler\n"
        "/mem_approve <id> - hafiza adayini onaylar\n"
        "/mem_reject <id> - hafiza adayini reddeder\n"
        "/mem_defer <id> - hafiza adayini erteler\n"
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
            summary = str(item.get("summary", "")).strip()
            if len(summary) > 280:
                summary = summary[:280].rstrip() + "..."

            lines.extend([
                f"ID: {item.get('id')}",
                f"Tier: {item.get('tier')} | Confidence: {item.get('confidence')}",
                f"Expires: {item.get('expires_at')}",
                f"Ozet: {summary}",
                "",
            ])

        lines.append("Komutlar:")
        lines.append("/mem_approve <id>")
        lines.append("/mem_reject <id>")
        lines.append("/mem_defer <id>")

        return "\n".join(lines)
    except Exception as exc:
        return f"Hafiza adaylari alinamadi: {exc}"


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
    elif text.startswith("/memory"):
        send_message(chat_id, cmd_memory())
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
    elif text.startswith("/mem_reject"):
        send_message(chat_id, cmd_memory_candidate_decide(text, "reject"))
    elif text.startswith("/mem_defer"):
        send_message(chat_id, cmd_memory_candidate_decide(text, "defer"))
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
