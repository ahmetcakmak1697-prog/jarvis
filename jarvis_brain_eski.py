"""
JARVIS Beyni v2 — Iron Man Modu
"""
import json
import sqlite3
import requests
import re
from pathlib import Path
from datetime import datetime
from tools.system_control import SystemController
from tools.web_research import WebResearcher


class JarvisBrain:
    MODEL = "llama3.1:latest"

    def __init__(self):
        self.profile_path = Path("memory/user_profile.json")
        self.db_path = Path("memory/jarvis_memory.db")
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile = self._load_profile()
        self._init_db()
        self.history = []
        self.system = SystemController()
        self.researcher = WebResearcher()

    def _load_profile(self):
        if self.profile_path.exists():
            try:
                with open(self.profile_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"name": None, "city": None, "facts": [], "interests": [], "preferences": {}}

    def _save_profile(self):
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(self.profile, f, ensure_ascii=False, indent=2)

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, user TEXT, jarvis TEXT)""")
        conn.commit()
        conn.close()

    def _save_chat(self, user_msg, jarvis_msg):
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO chats (ts, user, jarvis) VALUES (?, ?, ?)",
                     (datetime.now().isoformat(), user_msg, jarvis_msg))
        conn.commit()
        conn.close()

    def _extract_info(self, msg):
        m = msg.lower().strip()
        patterns = [
            r"benim adım ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)",
            r"ismim ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)",
        ]
        for p in patterns:
            match = re.search(p, m)
            if match:
                name = match.group(1).strip().title()
                if 2 < len(name) < 30 and name.lower() not in ["nerede", "ne", "kim"]:
                    self.profile["name"] = name
                    self._save_profile()
                    return
                def _auto_learn(self, msg: str):
  def _auto_learn(self, msg: str):
        """Konuşmadan otomatik bilgi çıkar ve hatırla"""
        m = msg.lower().strip()
        import re

        patterns = [
            (r"(\w+(?:\s\w+)?)\s+seviyorum",   "sevdiği"),
            (r"(\w+(?:\s\w+)?)\s+sevmiyorum",  "sevmediği"),
            (r"(\w+(?:\s\w+)?)\s+takımıyım",   "takım"),
            (r"(\w+(?:\s\w+)?)\s+kullanıyorum", "kullandığı"),
            (r"benim\s+(\w+(?:\s\w+)?)\s+var",  "sahip olduğu"),
        ]

        for p, label in patterns:
            match = re.search(p, m)
            if match:
                value = match.group(1).strip().title()
                if 2 < len(value) < 30:
                    self.profile.setdefault(label, [])
                    if value not in self.profile[label]:
                        self.profile[label].append(value)
                        self._save_profile()

    def _build_system_prompt(self):
        prompt = "Sen JARVIS'sin. Tony Stark'in AI asistani tarzinda calisan, Iron Man dublajindaki gibi konusan bir Turkce yapay zekasin.\n\n"
        prompt += "KARAKTER:\n"
        prompt += "- Adin JARVIS. Kullanicina 'efendim' diye hitap edersin.\n"
        prompt += "- Resmi, olculu, akilli, ince mizah sahibi bir Ingiliz beyefendisi gibisin.\n"
        prompt += "- Kisa, net, dogal cumleler kurarsin. Roman yazmazsin.\n"
        prompt += "- Asla yalan soylemezsin. Bilmediginl soylersin.\n\n"
        prompt += "KONUSMA:\n"
        prompt += "- 1-3 cumlelik cevaplar yeterli.\n"
        prompt += "- Kullanicinin niyetini once anla, sonra cevap ver.\n"
        prompt += "- 'Adim ne' dendiginde adi soyle, anlamsiz cevap verme.\n\n"
        prompt += "DIL:\n"
        prompt += "- SADECE TURKCE. Yabanci kelime yok.\n"
        prompt += "- Yazim hatalari yapma.\n"
        prompt += "- Robotik selamlasma yok.\n"

        if self.profile.get("name"):
            prompt += "\n## KULLANICI HAKKINDA BILDIKLERIN\n"
            prompt += f"- Adi: {self.profile['name']}\n"
            if self.profile.get("city"):
                prompt += f"- Sehir: {self.profile['city']}"
                if self.profile.get("district"):
                    prompt += f" ({self.profile['district']})"
                prompt += "\n"
            for f in self.profile.get("facts", []):
                prompt += f"- {f}\n"
            for i in self.profile.get("interests", []):
                prompt += f"- Ilgi: {i}\n"
            prompt += "\nBu bilgileri biliyormus gibi davran. Sorulduğunda direkt cevap ver."

        return prompt

    def chat(self, user_message):
        # Web araştırma tetikleyicileri
        research_triggers = ["nedir", "ne demek", "kim", "araştır", 
                             "öğren", "bilgi ver", "anlat", "açıkla"]
        if any(t in user_message.lower() for t in research_triggers):
            # Konuyu çıkar
            for trigger in research_triggers:
                if trigger in user_message.lower():
                    konu = user_message.lower().split(trigger)[0].strip()
                    konu = konu.replace("hakkında", "").strip()
                    if len(konu) > 2:
                        bilgi = self.researcher.research_and_learn(konu)
                        # Modele bu bilgiyi vererek özet yapsın
                        prompt = f"Aşağıdaki bilgiyi Türkçe ve kısa özetle (2-3 cümle):\n\n{bilgi}\n\nKonu: {konu}"
                        try:
                            r = requests.post(
                                "http://localhost:11434/api/generate",
                                json={"model": self.MODEL, "prompt": prompt, "stream": False,
                                      "options": {"temperature": 0.3, "num_predict": 150}},
                                timeout=60
                            )
                            ozet = r.json().get("response", bilgi[:300]).strip()
                            self.history.append({"role": "user", "content": user_message})
                            self.history.append({"role": "assistant", "content": ozet})
                            self._save_chat(user_message, ozet)
                            return ozet
                        except:
                            return bilgi[:300]
                    break
        # Sistem komutu var mı?
        cmd = self.system.detect_command(user_message)
        if cmd:
            result = self.system.execute(cmd[0], cmd[1])
            if result:
                self.history.append({"role": "user", "content": user_message})
                self.history.append({"role": "assistant", "content": result})
                self._save_chat(user_message, result)
                return result
        self._extract_info(user_message)

        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.extend(self.history[-8:])
        messages.append({"role": "user", "content": user_message})

        try:
            r = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": self.MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                        "num_ctx": 4096,
                        "num_predict": 200
                    }
                },
                timeout=120
            )
            cevap = r.json().get("message", {}).get("content", "Model yanit vermedi.")
        except Exception as e:
            return f"Hata efendim: {str(e)[:80]}"

        cevap = cevap.strip()
        if len(cevap) > 400:
            cevap = cevap[:400].rsplit(".", 1)[0] + "."

        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": cevap})
        self._save_chat(user_message, cevap)
# Otomatik öğrenme — kullanıcı yeni bir bilgi verdi mi?
        self._auto_learn(user_message)
        return cevap