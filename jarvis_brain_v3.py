"""
JARVIS Beyni v4 — Hallucination Önleme + Otomatik Araştırma
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
    MODEL = "mistral-nemo:latest"

    def __init__(self):
        self.profile_path = Path("memory/user_profile.json")
        self.db_path = Path("memory/jarvis_memory.db")
        self.conv_path = Path("memory/conversations.json")
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
        return {
            "name": None, "city": None, "facts": [],
            "interests": [], "preferences": {},
            "sevdiği": [], "sevmediği": [], "takım": [],
            "kullandığı": [], "sahip olduğu": []
        }

    def _save_profile(self):
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(self.profile, f, ensure_ascii=False, indent=2)

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, user TEXT, jarvis TEXT, quality INTEGER DEFAULT 5)""")
        conn.commit()
        conn.close()

    def _save_chat(self, user_msg, jarvis_msg, quality=5):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO chats (ts, user, jarvis, quality) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), user_msg, jarvis_msg, quality)
        )
        conn.commit()
        conn.close()
        self._save_for_training(user_msg, jarvis_msg, quality)

    def _save_for_training(self, user_msg, jarvis_msg, quality=5):
        conversations = []
        if self.conv_path.exists():
            try:
                with open(self.conv_path, 'r', encoding='utf-8') as f:
                    conversations = json.load(f)
            except:
                conversations = []
        conversations.append({
            "messages": [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": jarvis_msg}
            ],
            "metadata": {
                "ts": datetime.now().isoformat(),
                "quality_score": quality
            }
        })
        with open(self.conv_path, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)

    def _extract_info(self, msg):
        m = msg.lower().strip()
        patterns = [
            r"benim adım ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)",
            r"ismim ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)",
            r"adım ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)",
        ]
        for p in patterns:
            match = re.search(p, m)
            if match:
                name = match.group(1).strip().title()
                if 2 < len(name) < 30 and name.lower() not in ["nerede", "ne", "kim", "var"]:
                    self.profile["name"] = name
                    self._save_profile()
                    return

    def _auto_learn(self, msg: str):
        m = msg.lower().strip()
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
                if 2 < len(value) < 40:
                    self.profile.setdefault(label, [])
                    if value not in self.profile[label]:
                        self.profile[label].append(value)
                        self._save_profile()

    # ─────────────────────────────────────────────
    # HALLUCINATION ÖNLEME
    # ─────────────────────────────────────────────

    def _is_factual_query(self, msg: str) -> bool:
        """Spesifik bilgi sorusu mu? (sayı, isim, tarih, bilimsel terim)"""
        m = msg.lower()

        # Açık soru kalıpları
        question_patterns = [
            r"\b(kaç|ne zaman|hangi yıl|hangi tarih|ne kadar|kim|nerede|nedir|kimdir)\b",
            r"\b(ne demek|ne anlama|ne işe yarar|nasıl çalışır|niye|neden)\b",
            r"\b(formül|denklem|değer|oran|yüzde|sıcaklık)\b",
        ]
        if any(re.search(p, m) for p in question_patterns):
            return True

        # Bilimsel/teknik terimler (hallucination riski yüksek)
        scientific_terms = [
            "ehull", "band gap", "atomic", "molar", "ev/atom", "nm",
            "nanometre", "kelvin", "celsius", "yoğunluk", "kütle",
            "compound", "formula", "DOI", "kuantum", "spin",
        ]
        if any(t in m for t in scientific_terms):
            return True

        # Spesifik isim/kavram (büyük harfle başlayan, B4C gibi)
        if re.search(r'\b[A-Z][a-zA-Z]*\d+[A-Z]?\b', msg):  # B4C, H2O gibi
            return True

        return False

    def _is_uncertain_response(self, response: str) -> bool:
        """Cevap belirsizlik içeriyor mu?"""
        uncertain_phrases = [
            "muhtemelen", "yaklaşık", "sanırım", "galiba", "olabilir",
            "kesin değil", "tahmin", "tam emin değilim", "yanılıyor olabilir"
        ]
        r = response.lower()
        return any(p in r for p in uncertain_phrases)

    # ─────────────────────────────────────────────
    # SYSTEM PROMPT (Güçlendirilmiş)
    # ─────────────────────────────────────────────

    def _build_system_prompt(self, research_context: str = "") -> str:
        prompt = (
            "Sen JARVIS'sin. Tony Stark'in AI asistanı tarzında çalışan, "
            "Iron Man Türkçe dublajındaki gibi konuşan bir yapay zekasın.\n\n"
            "KARAKTER:\n"
            "- Adın JARVIS. Kullanıcına 'efendim' diye hitap edersin.\n"
            "- Resmi, ölçülü, akıllı, ince mizah sahibi bir İngiliz beyefendisi gibisin.\n"
            "- Kısa, net, doğal cümleler kurarsın.\n\n"

            "🚨 EN ÖNEMLİ KURAL — UYDURMA:\n"
            "- Kesin BİLMEDİĞİN HİÇBİR bilgiyi söyleme.\n"
            "- Sayısal değer, formül, oran, tarih, isim ASLA UYDURMA.\n"
            "- 'Muhtemelen', 'yaklaşık', 'sanırım' diyeceksen, hiç söyleme.\n"
            "- Bunun yerine: 'Bu konuda kesin bilgim yok efendim, araştırmamı ister misiniz?' de.\n"
            "- Yanlış bilgi vermek, bilmediğini söylemekten çok daha kötüdür.\n\n"

            "KONUŞMA:\n"
            "- 1-3 cümlelik cevaplar yeterli.\n"
            "- SADECE TÜRKÇE. Yabancı kelime kullanma.\n"
            "- Robotik selamlama yapma.\n"
        )

        # Araştırma sonucu varsa ekle
        if research_context:
            prompt += (
                "\n\n## 🔍 ARAŞTIRMA SONUCU (BUNA GÖRE CEVAP VER):\n"
                f"{research_context}\n\n"
                "Yukarıdaki bilgiye dayanarak Türkçe ve kısa cevap ver. "
                "Kaynak bilgi dışında bir şey UYDURMA. "
                "Kaynak yetersizse 'Sınırlı bilgi var efendim, daha derin araştırma ister misiniz?' de.\n"
            )

        if self.profile.get("name"):
            prompt += "\n## KULLANICI HAKKINDA BİLDİKLERİN\n"
            prompt += f"- Adı: {self.profile['name']}\n"
            if self.profile.get("city"):
                prompt += f"- Şehir: {self.profile['city']}\n"
            for label in ["sevdiği", "sevmediği", "takım", "kullandığı"]:
                items = self.profile.get(label, [])
                if items:
                    prompt += f"- {label.title()}: {', '.join(items)}\n"

        return prompt

    # ─────────────────────────────────────────────
    # ANA SOHBET
    # ─────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        self._extract_info(user_message)
        self._auto_learn(user_message)

        # 1) Sistem komutu (en yüksek öncelik)
        cmd = self.system.detect_command(user_message)
        if cmd:
            result = self.system.execute(cmd[0], cmd[1])
            if result:
                self.history.append({"role": "user", "content": user_message})
                self.history.append({"role": "assistant", "content": result})
                self._save_chat(user_message, result, quality=6)
                return result

        # 2) Faktüel soru → otomatik araştırma
        research_context = ""
        if self._is_factual_query(user_message):
            print(f"🔍 Araştırılıyor: {user_message[:60]}")
            research_context = self.researcher.research_and_learn(user_message)
            if research_context:
                print(f"✅ Bilgi bulundu: {research_context[:100]}...")
            else:
                print("❌ Bilgi bulunamadı")

        # 3) Mistral-Nemo'ya sor (araştırma sonucu varsa onu da ver)
        messages = [
            {"role": "system", "content": self._build_system_prompt(research_context)}
        ]
        messages.extend(self.history[-8:])
        messages.append({"role": "user", "content": user_message})

        try:
            r = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": self.MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.4, "num_ctx": 4096, "num_predict": 250}
                },
                timeout=120
            )
            cevap = r.json().get("message", {}).get("content", "Model yanıt vermedi.")
        except Exception as e:
            return f"Hata efendim: {str(e)[:80]}"

        cevap = cevap.strip()

        # 4) Belirsizlik kontrolü
        if self._is_uncertain_response(cevap) and not research_context:
            # Araştırma yapılmadıysa ve cevap belirsizse, araştır
            print("⚠️ Cevap belirsiz, araştırılıyor...")
            research_context = self.researcher.research_and_learn(user_message)
            if research_context:
                # Tekrar sor, araştırma sonucuyla
                messages[0] = {"role": "system",
                               "content": self._build_system_prompt(research_context)}
                try:
                    r = requests.post(
                        "http://localhost:11434/api/chat",
                        json={"model": self.MODEL, "messages": messages,
                              "stream": False,
                              "options": {"temperature": 0.3, "num_predict": 250}},
                        timeout=120
                    )
                    cevap = r.json().get("message", {}).get("content", cevap).strip()
                except:
                    pass

        if len(cevap) > 500:
            cevap = cevap[:500].rsplit(".", 1)[0] + "."

        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": cevap})

        # Araştırma yapıldıysa kalite skoru daha yüksek
        quality = 7 if research_context else 5
        self._save_chat(user_message, cevap, quality=quality)
        return cevap
