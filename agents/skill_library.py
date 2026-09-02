"""Skill Library - learn and reuse repeated tasks."""
import json
import re
from pathlib import Path
from datetime import datetime


class SkillLibrary:
    def __init__(self):
        self.path = Path("memory/skills.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.skills = self._load()

    def _load(self):
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding='utf-8'))
            except:
                pass
        return {}

    def _save(self):
        self.path.write_text(
            json.dumps(self.skills, ensure_ascii=False, indent=2),
            encoding='utf-8')

    def add(self, name, trigger_patterns, instructions, tags=None):
        self.skills[name] = {
            "trigger_patterns": trigger_patterns,
            "instructions": instructions,
            "tags": tags or [],
            "use_count": 0,
            "created": datetime.now().isoformat(),
            "last_used": None
        }
        self._save()

    def remove(self, name):
        if name in self.skills:
            del self.skills[name]
            self._save()
            return True
        return False

    def find(self, message):
        m = message.lower()
        matched = []
        for name, sk in self.skills.items():
            for p in sk.get("trigger_patterns", []):
                try:
                    if re.search(p.lower(), m):
                        matched.append((name, sk))
                        break
                except:
                    if p.lower() in m:
                        matched.append((name, sk))
                        break
        return matched

    def use(self, name):
        if name in self.skills:
            self.skills[name]["use_count"] += 1
            self.skills[name]["last_used"] = datetime.now().isoformat()
            self._save()
            return self.skills[name].get("instructions", "")
        return ""

    def list_all(self):
        return [
            {"name": n,
             "use_count": s.get("use_count", 0),
             "tags": s.get("tags", []),
             "last_used": s.get("last_used")}
            for n, s in self.skills.items()
        ]

    def auto_learn_from_history(self, conversations, min_count=3):
        """Tekrarlanan kalıpları bul, otomatik skill öner"""
        from collections import Counter
        pattern_counter = Counter()
        for c in conversations:
            msgs = c.get("messages", [])
            user = next((m["content"] for m in msgs if m["role"] == "user"), "")
            words = re.findall(r'\b\w{4,}\b', user.lower())
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                pattern_counter[bigram] += 1
        suggestions = []
        for pat, cnt in pattern_counter.most_common(20):
            if cnt >= min_count:
                suggestions.append({"pattern": pat, "count": cnt})
        return suggestions
