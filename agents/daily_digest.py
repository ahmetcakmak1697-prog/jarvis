"""
Daily Digest - Stanford OpenJarvis tarzı sabah brifingi
Her sabah 08:00'de otomatik üretilir.

İçerik:
- Hava durumu (lokasyona göre)
- Dünden 3 önemli şey
- Bugün için 3 öneri
- Bekleyen görevler
- JARVIS'in fark ettiği şeyler
"""
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta


class DailyDigest:
    MODEL = "mistral-nemo:latest"

    def __init__(self):
        self.path = Path("memory/digests.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def generate(self) -> dict:
        """Tam sabah brifingi üret"""
        ctx = self._collect_context()
        prompt = self._build_prompt(ctx)

        try:
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.MODEL, "prompt": prompt, "stream": False,
                      "options": {"temperature": 0.6, "num_predict": 600}},
                timeout=120)
            text = r.json().get("response", "").strip()
        except Exception as e:
            text = f"Brifing üretilemedi: {e}"

        digest = {
            "ts":      datetime.now().isoformat(),
            "date":    datetime.now().date().isoformat(),
            "content": text,
            "context": ctx,
        }
        self._save(digest)
        return digest

    def _collect_context(self) -> dict:
        ctx = {
            "name":     self._name(),
            "city":     self._city(),
            "weather":  self._weather(),
            "yesterday": self._yesterday(),
            "pending":  self._pending_tasks(),
            "weak":     self._weak_areas(),
            "calendar": self._calendar_events(),
        }
        return ctx

    def _name(self) -> str:
        p = Path("memory/user_profile.json")
        if p.exists():
            try:
                return json.loads(p.read_text(encoding='utf-8')).get("name", "efendim")
            except:
                pass
        return "efendim"

    def _city(self) -> str:
        p = Path("memory/user_profile.json")
        if p.exists():
            try:
                return json.loads(p.read_text(encoding='utf-8')).get("city", "")
            except:
                pass
        return ""

    def _weather(self) -> str:
        city = self._city()
        if not city:
            return ""
        try:
            r = requests.get(f"https://wttr.in/{city}?format=%C+%t&lang=tr",
                             timeout=10)
            if r.status_code == 200:
                return r.text.strip()
        except:
            pass
        return ""

    def _memory_allowed_for_digest(self, meta: dict) -> bool:
        """C1.6: Only safe/useful memory entries should enter daily digest."""
        meta = meta or {}

        if meta.get("requires_review") is True:
            return False

        action = str(meta.get("memory_action", "") or "")

        if action in ("ignore", "temporary", "sensitive_review"):
            return False

        if action in ("daily_summary", "keep_long_term"):
            return bool(meta.get("allow_daily_summary", True))

        # Backward compatibility for old records without C1 metadata.
        # Keep only decent quality, non-researched items.
        if meta.get("researched") is True:
            return False

        return int(meta.get("quality_score", 0) or 0) >= 6

    def _yesterday(self) -> list:
        p = Path("memory/conversations.json")
        if not p.exists():
            return []
        try:
            cs = json.loads(p.read_text(encoding='utf-8'))
            y = (datetime.now() - timedelta(days=1)).date().isoformat()
            yesterday = [
                c for c in cs
                if c.get("metadata", {}).get("ts", "")[:10] == y
                and self._memory_allowed_for_digest(c.get("metadata", {}))
            ]

            topics = []
            for c in yesterday[-10:]:
                u = next((m["content"] for m in c.get("messages", [])
                          if m["role"] == "user"), "")
                if u and len(u) > 20:
                    topics.append(u[:100])
            return topics
        except:
            return []

    def _pending_tasks(self) -> list:
        p = Path("memory/reminders.json")
        if not p.exists():
            return []
        try:
            rs = json.loads(p.read_text(encoding='utf-8'))
            return [r["text"] for r in rs if not r.get("done")][:5]
        except:
            return []

    def _weak_areas(self) -> str:
        p = Path("memory/improvements.json")
        if not p.exists():
            return ""
        try:
            ins = json.loads(p.read_text(encoding='utf-8'))
            if ins:
                return ins[-1].get("analysis", {}).get("ana_zayıflık", "")
        except:
            pass
        return ""

    def _calendar_events(self) -> list:
        """Şimdilik manuel — ileride Google Calendar"""
        return []

    def _build_prompt(self, ctx: dict) -> str:
        return f"""Sen JARVIS'sin. {ctx['name']}'e sabah brifingi.

📍 Lokasyon: {ctx['city'] or 'bilinmiyor'}
🌤️ Hava: {ctx['weather'] or 'bilgi yok'}

📋 DÜN KONUŞULAN KONULAR:
{chr(10).join('- ' + t for t in ctx['yesterday'][:5]) or '(dün konuşma yok)'}

⏰ BEKLEYEN GÖREVLER:
{chr(10).join('- ' + t for t in ctx['pending']) or '(görev yok)'}

🔍 GELİŞTİRİLEBİLİR ALAN:
{ctx['weak'] or '(tespit yok)'}

GÖREV: Sabah brifingi hazırla. 3 bölüm:

1. "Günaydın {ctx['name']}" + hava + tarih
2. Dünden önemli olanların özeti (1-2 cümle)
3. Bugün için 2-3 somut öneri

JARVIS karakterinde, sıcak ama profesyonel. Türkçe. Maksimum 200 kelime."""

    def _save(self, digest: dict):
        items = []
        if self.path.exists():
            try:
                items = json.loads(self.path.read_text(encoding='utf-8'))
            except:
                pass
        items = [i for i in items if i.get("date") != digest["date"]]
        items.append(digest)
        items = items[-30:]
        self.path.write_text(json.dumps(items, ensure_ascii=False, indent=2),
                             encoding='utf-8')

    def get_latest(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            items = json.loads(self.path.read_text(encoding='utf-8'))
            return items[-1] if items else {}
        except:
            return {}


if __name__ == "__main__":
    d = DailyDigest()
    result = d.generate()
    print(result.get("content", ""))
