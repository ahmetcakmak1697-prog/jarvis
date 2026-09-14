"""Conversation Summarizer - daily summaries."""
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta


MODEL = "mistral-nemo:latest"
CONV = Path("memory/conversations.json")
SUMMARIES = Path("memory/daily_summaries.json")


def summarize_day(date_str=None):
    """date_str: YYYY-MM-DD (default: bugün)"""
    if date_str is None:
        date_str = datetime.now().date().isoformat()
    if not CONV.exists():
        return None
    convs = json.loads(CONV.read_text(encoding='utf-8'))
    day = [c for c in convs
           if c.get("metadata", {}).get("ts", "")[:10] == date_str]
    if not day:
        return {"date": date_str, "summary": "Konuşma yok", "count": 0}
    msgs = []
    for c in day:
        for m in c.get("messages", []):
            r = "Kullanıcı" if m["role"] == "user" else "JARVIS"
            msgs.append(f"{r}: {m['content']}")
    text = "\n".join(msgs)[:8000]
    prompt = f"""Aşağıdaki günlük konuşmaları Türkçe özetle.

{text}

ÖZET:
- Ana konular (2-3 madde)
- Öğrenilen şeyler
- Sonraki adım önerileri

Kısa, net, JARVIS karakterinde."""
    try:
        r = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.4, "num_predict": 400}},
            timeout=120)
        summary = r.json().get("response", "").strip()
    except Exception as e:
        summary = f"Özet hatası: {e}"
    result = {"date": date_str, "summary": summary,
              "count": len(day),
              "generated": datetime.now().isoformat()}
    _save(result)
    return result


def _save(s):
    SUMMARIES.parent.mkdir(parents=True, exist_ok=True)
    items = []
    if SUMMARIES.exists():
        try:
            items = json.loads(SUMMARIES.read_text(encoding='utf-8'))
        except:
            pass
    items = [i for i in items if i.get("date") != s["date"]]
    items.append(s)
    items = items[-100:]
    SUMMARIES.write_text(json.dumps(items, ensure_ascii=False, indent=2),
                         encoding='utf-8')


def get_recent(n=7):
    if not SUMMARIES.exists():
        return []
    try:
        items = json.loads(SUMMARIES.read_text(encoding='utf-8'))
        return sorted(items, key=lambda x: x.get("date", ""))[-n:]
    except:
        return []


if __name__ == "__main__":
    print(json.dumps(summarize_day(), ensure_ascii=False, indent=2))
