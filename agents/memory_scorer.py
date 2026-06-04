"""
Memory Importance Scoring
Her hafızanın 0-10 puanı:
  ≥8 = ölümsüz (asla silinmez)
  <3 = 30 gün sonra silinir
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class MemoryScorer:
    KEEP_FOREVER = 8
    DELETE_BELOW = 3

    HIGH_VALUE = [
        r"benim adım", r"ismim", r"yaşıyorum", r"çalışıyorum",
        r"projem", r"hedefim", r"sevdiğim", r"sevmediğim",
        r"alerjim", r"hastalığım", r"ailem", r"doğum",
        r"şirket", r"firma", r"okul", r"üniversite",
        r"telefonum", r"emaillerim", r"adresim",
    ]

    LOW_VALUE = [
        r"^(merhaba|selam|hi|hello|teşekkür|tamam|evet|hayır|ok)[\s\.\!]*$",
        r"^saat kaç", r"^hava nasıl",
    ]

    def policy_decision(self, user_msg: str, jarvis_msg: str = "") -> dict[str, Any]:
        """Return MemoryPolicy decision as a plain dict.

        This keeps MemoryScorer backward-compatible while allowing C1 policy
        decisions to guide scoring and future memory routing.
        """
        try:
            from agents.memory_policy import MemoryPolicy

            return MemoryPolicy().decide(user_msg, jarvis_msg).to_dict()
        except Exception as exc:
            return {
                "action": "temporary",
                "importance": self._legacy_score(user_msg, jarvis_msg),
                "reason": f"MemoryPolicy unavailable: {exc}",
                "tags": ["policy_fallback"],
                "retention_days": 14,
                "allow_vector": False,
                "allow_daily_summary": False,
                "requires_review": False,
            }

    def score(self, user_msg: str, jarvis_msg: str = "") -> int:
        """Return a safe 0-10 importance score guided by MemoryPolicy."""
        decision = self.policy_decision(user_msg, jarvis_msg)
        action = decision.get("action", "temporary")
        importance = int(decision.get("importance", 5) or 5)

        if action == "ignore":
            return 1

        if action == "sensitive_review":
            # Important enough to review, but intentionally low for automatic
            # long-term/vector memory writes.
            return 2

        if action == "keep_long_term":
            return max(8, min(10, importance))

        if action == "daily_summary":
            return max(5, min(7, importance))

        if action == "temporary":
            return max(3, min(5, importance))

        return max(0, min(10, importance))

    def _legacy_score(self, user_msg: str, jarvis_msg: str = "") -> int:
        msg = (user_msg + " " + jarvis_msg).lower()
        s = 5

        for p in self.HIGH_VALUE:
            if re.search(p, msg):
                s += 2

        for p in self.LOW_VALUE:
            if re.match(p, user_msg.lower().strip()):
                s -= 3

        if len(user_msg) > 100:
            s += 1
        if len(user_msg) > 300:
            s += 1
        if "?" in user_msg:
            s += 1

        if any(p in user_msg.lower() for p in ["benim", "bana", "bende"]):
            s += 1

        return max(0, min(10, s))

    def cleanup_old(self, days: int = 30) -> int:
        """Eski + düşük puanlıları sil. Silinen sayıyı döner."""
        p = Path("memory/conversations.json")
        if not p.exists():
            return 0
        try:
            convs = json.loads(p.read_text(encoding='utf-8'))
        except:
            return 0

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        before = len(convs)

        def keep(c):
            meta = c.get("metadata", {})
            imp = meta.get("importance", meta.get("quality_score", 5))
            ts = meta.get("ts", "")
            if imp >= self.KEEP_FOREVER:
                return True
            if ts < cutoff and imp < self.DELETE_BELOW:
                return False
            return True

        convs = [c for c in convs if keep(c)]
        deleted = before - len(convs)
        if deleted > 0:
            p.write_text(json.dumps(convs, ensure_ascii=False, indent=2),
                         encoding='utf-8')
        return deleted


if __name__ == "__main__":
    s = MemoryScorer()

    samples = [
        "Merhaba",
        "Bunu hatırla: C1 sonrası C2 proje zekasına geçeceğiz.",
        "Telefon numaram 555 ile başlıyor.",
        "Bugün Telegram bot ve Tailscale testini tamamladık.",
        "Bu konuşma geçici bir deneme.",
    ]

    for sample in samples:
        print("---")
        print(sample)
        print("score:", s.score(sample))
        print("policy:", s.policy_decision(sample))
