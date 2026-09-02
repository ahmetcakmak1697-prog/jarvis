"""
jarvis/agent/local_agent_memory.py
Lokal ajan için basit ama akıllı hafıza sistemi.
JSON dosyasında saklar, keyword + semantic search ile arar.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

MEMORY_FILE = Path(__file__).parent.parent / "data" / "memory" / "local_memory.json"


class LocalMemory:
    def __init__(self):
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._data: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if MEMORY_FILE.exists():
            try:
                return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self):
        MEMORY_FILE.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def add(self, user_msg: str, assistant_msg: str):
        """Konuşmayı hafızaya ekle."""
        # Çok kısa veya çok basit mesajları kaydetme
        if len(user_msg) < 10:
            return

        entry = {
            "ts": time.time(),
            "user": user_msg[:400],
            "assistant": assistant_msg[:600],
            "keywords": self._extract_keywords(user_msg + " " + assistant_msg),
        }
        self._data.append(entry)

        # Son 200 kaydı tut
        if len(self._data) > 200:
            self._data = self._data[-200:]

        self._save()

    def get_context(self, query: str, top_k: int = 4) -> str:
        """Sorguyla ilgili hafıza kayıtlarını döndür."""
        if not self._data:
            return ""

        q_words = set(query.lower().split())
        scored = []

        for entry in self._data:
            # Keyword overlap skoru
            keywords = set(entry.get("keywords", []))
            overlap = len(q_words & keywords)

            # İçerik benzerliği
            content = (entry.get("user", "") + " " + entry.get("assistant", "")).lower()
            content_score = sum(1 for w in q_words if w in content and len(w) > 3)

            score = overlap * 2 + content_score
            if score > 0:
                scored.append((score, entry))

        if not scored:
            return ""

        scored.sort(reverse=True)
        top = scored[:top_k]

        lines = []
        for _, entry in top:
            ts = time.strftime("%d.%m.%Y", time.localtime(entry["ts"]))
            lines.append(f"[{ts}] Kullanıcı: {entry['user'][:120]}")
            lines.append(f"  Jarvis: {entry['assistant'][:200]}")

        return "\n".join(lines)

    def _extract_keywords(self, text: str) -> list[str]:
        """Basit keyword çıkarma."""
        # Stop words
        stop = {
            "ve", "bir", "bu", "de", "da", "ile", "için", "ben", "sen",
            "o", "biz", "siz", "onlar", "var", "yok", "mi", "mu", "mı",
            "the", "a", "an", "is", "are", "was", "be", "to", "of", "in",
        }
        words = re.findall(r'\b[a-züğışöçA-ZÜĞİŞÖÇ]{3,}\b', text.lower())
        return list({w for w in words if w not in stop})[:20]

    def count(self) -> int:
        return len(self._data)

    def clear(self):
        self._data = []
        self._save()


# re import
import re
