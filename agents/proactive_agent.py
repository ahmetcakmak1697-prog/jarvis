"""Proactive Agent - briefings + reminders."""
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path


class ProactiveAgent:
    def __init__(self, model="mistral-nemo:latest"):
        self.briefings = Path("memory/briefings.json")
        self.reminders = Path("memory/reminders.json")
        self.profile = Path("memory/user_profile.json")
        self.conv = Path("memory/conversations.json")
        self.briefings.parent.mkdir(parents=True, exist_ok=True)
        self.model = model

    def morning_briefing(self):
        name = self._name()
        yesterday = self._yesterday()
        weak = self._weak_areas()
        prompt = f"""Sen JARVIS'sin. {name}'e sabah brifingi.

DÜNDEN ÖZET:
{yesterday}

GELİŞTİRİLECEK:
{weak}

KISA brifing (2-3 paragraf):
1. "Günaydın {name}" ile başla
2. Dünden 1-2 önemli şey hatırlat
3. Bugün için 1 motive edici öneri

Resmi, JARVIS karakterinde."""
        return self._gen(prompt, "morning")

    def evening_summary(self):
        name = self._name()
        today = self._today()
        prompt = f"""Sen JARVIS'sin. {name}'e akşam özeti.

BUGÜNKÜ:
{today}

KISA özet (2 paragraf):
1. "İyi akşamlar {name}"
2. Bugün öğrenilen, vurgula
3. Yarın için 1 düşünce

JARVIS karakteri."""
        return self._gen(prompt, "evening")

    def add_reminder(self, text, when):
        rs = self._load_rem()
        rs.append({
            "text": text, "when": when,
            "created": datetime.now().isoformat(), "done": False,
            "id": f"r_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        })
        self._save_rem(rs)

    def get_due(self):
        rs = self._load_rem()
        now = datetime.now().isoformat()
        return [r for r in rs if not r["done"] and r["when"] <= now]

    def mark_done(self, rid):
        rs = self._load_rem()
        for r in rs:
            if r.get("id") == rid:
                r["done"] = True
        self._save_rem(rs)

    def _gen(self, prompt, kind):
        try:
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.model, "prompt": prompt,
                      "stream": False,
                      "options": {"temperature": 0.6, "num_predict": 350}},
                timeout=90)
            content = r.json().get("response", "").strip()
            self._save_brief(content, kind)
            return content
        except Exception as e:
            return f"Brifing hatası: {str(e)[:80]}"

    def _name(self):
        if self.profile.exists():
            try:
                return json.loads(self.profile.read_text(encoding='utf-8')).get(
                    "name") or "efendim"
            except:
                pass
        return "efendim"

    def _yesterday(self):
        if not self.conv.exists():
            return "Veri yok"
        try:
            cs = json.loads(self.conv.read_text(encoding='utf-8'))
            cut = (datetime.now() - timedelta(days=1)).isoformat()
            recent = [c for c in cs
                      if c.get("metadata", {}).get("ts", "") > cut][-5:]
            return "\n".join(
                f"- {next((m['content'][:100] for m in c.get('messages', []) if m['role']=='user'), '')}"
                for c in recent) or "Yeni konuşma yok"
        except:
            return "Hata"

    def _today(self):
        if not self.conv.exists():
            return "Veri yok"
        try:
            cs = json.loads(self.conv.read_text(encoding='utf-8'))
            t = datetime.now().date().isoformat()
            today = [c for c in cs
                     if c.get("metadata", {}).get("ts", "")[:10] == t]
            if not today:
                return "Bugün konuşma yok"
            return "\n".join(
                f"- {next((m['content'][:80] for m in c.get('messages', []) if m['role']=='user'), '')}"
                for c in today[-10:])
        except:
            return "Hata"

    def _weak_areas(self):
        p = Path("memory/improvements.json")
        if not p.exists():
            return "Henüz veri yok"
        try:
            ins = json.loads(p.read_text(encoding='utf-8'))
            if not ins:
                return "Henüz veri yok"
            return ins[-1].get("analysis", {}).get("ana_zayıflık", "Tespit yok")
        except:
            return "Hata"

    def _load_rem(self):
        if self.reminders.exists():
            try:
                return json.loads(self.reminders.read_text(encoding='utf-8'))
            except:
                pass
        return []

    def _save_rem(self, rs):
        self.reminders.write_text(
            json.dumps(rs, ensure_ascii=False, indent=2), encoding='utf-8')

    def _save_brief(self, content, kind):
        bs = []
        if self.briefings.exists():
            try:
                bs = json.loads(self.briefings.read_text(encoding='utf-8'))
            except:
                pass
        bs.append({"ts": datetime.now().isoformat(),
                   "kind": kind, "content": content})
        bs = bs[-100:]
        self.briefings.write_text(
            json.dumps(bs, ensure_ascii=False, indent=2), encoding='utf-8')

    def get_latest(self, kind=None):
        if not self.briefings.exists():
            return None
        try:
            bs = json.loads(self.briefings.read_text(encoding='utf-8'))
            if kind:
                f = [b for b in bs if b["kind"] == kind]
                return f[-1] if f else None
            return bs[-1] if bs else None
        except:
            return None
