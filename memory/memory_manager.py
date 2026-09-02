"""
JARVIS Hafıza Sistemi
- Konuşma geçmişi (SQLite)
- Kullanıcı profili (JSON)
- Önemli olaylar
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class JarvisMemory:
    def __init__(self, db_path: str = "memory/jarvis_memory.db",
                 profile_path: str = "memory/user_profile.json"):
        self.db_path = Path(db_path)
        self.profile_path = Path(profile_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        self.profile = self._load_profile()
    
    def _init_db(self):
        """Veritabanı tablolarını oluştur"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Konuşmalar tablosu
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_message TEXT,
                jarvis_response TEXT,
                model_used TEXT
            )
        """)
        
        # Önemli olaylar tablosu
        c.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                category TEXT,
                description TEXT,
                importance INTEGER DEFAULT 5
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_profile(self) -> dict:
        """Kullanıcı profilini yükle"""
        if self.profile_path.exists():
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "name": None,
            "interests": [],
            "preferences": {},
            "facts": [],
            "current_projects": []
        }
    
    def save_profile(self):
        """Profili dosyaya yaz"""
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(self.profile, f, ensure_ascii=False, indent=2)
    
    def add_conversation(self, user_msg: str, jarvis_resp: str, model: str = "?"):
        """Konuşmayı kaydet"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO conversations (timestamp, user_message, jarvis_response, model_used) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), user_msg, jarvis_resp, model)
        )
        conn.commit()
        conn.close()
    
    def get_recent_conversations(self, n: int = 5) -> List[Dict]:
        """Son n konuşmayı getir"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT timestamp, user_message, jarvis_response FROM conversations ORDER BY id DESC LIMIT ?",
            (n,)
        )
        rows = c.fetchall()
        conn.close()
        return [
            {"time": r[0], "user": r[1], "jarvis": r[2]}
            for r in reversed(rows)
        ]
    
    def search_conversations(self, keyword: str, limit: int = 5) -> List[Dict]:
        """Geçmişte arama yap"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """SELECT timestamp, user_message, jarvis_response 
               FROM conversations 
               WHERE user_message LIKE ? OR jarvis_response LIKE ?
               ORDER BY id DESC LIMIT ?""",
            (f"%{keyword}%", f"%{keyword}%", limit)
        )
        rows = c.fetchall()
        conn.close()
        return [
            {"time": r[0], "user": r[1], "jarvis": r[2]}
            for r in rows
        ]
    
    def add_event(self, category: str, description: str, importance: int = 5):
        """Önemli olay ekle"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO events (timestamp, category, description, importance) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), category, description, importance)
        )
        conn.commit()
        conn.close()
    
    def update_profile(self, key: str, value):
        """Profile bilgi ekle"""
        if key in ["interests", "facts", "current_projects"]:
            if value not in self.profile[key]:
                self.profile[key].append(value)
        else:
            self.profile[key] = value
        self.save_profile()
    
    def get_context_for_prompt(self) -> str:
        """Ollama'ya gönderilecek hafıza özeti"""
        ctx = []
        
        if self.profile.get("name"):
            ctx.append(f"Kullanıcının adı: {self.profile['name']}")
        
        if self.profile.get("interests"):
            ctx.append(f"İlgi alanları: {', '.join(self.profile['interests'])}")
        
        if self.profile.get("current_projects"):
            ctx.append(f"Aktif projeler: {', '.join(self.profile['current_projects'])}")
        
        recent = self.get_recent_conversations(3)
        if recent:
            ctx.append("Son konuşmalar:")
            for r in recent:
                ctx.append(f"  - Sen: {r['user'][:80]}")
                ctx.append(f"    Ben: {r['jarvis'][:80]}")
        
        return "\n".join(ctx) if ctx else ""
    
    def stats(self) -> Dict:
        """İstatistikler"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM conversations")
        conv_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM events")
        event_count = c.fetchone()[0]
        conn.close()
        
        return {
            "total_conversations": conv_count,
            "total_events": event_count,
            "profile_name": self.profile.get("name", "Bilinmiyor"),
            "interests_count": len(self.profile.get("interests", [])),
            "projects_count": len(self.profile.get("current_projects", []))
        }
    def auto_extract_info(self, user_message: str, jarvis_response: str = ""):
        """Konuşmadan otomatik bilgi çıkar ve profile kaydet."""
        msg = user_message.lower()
        
        # İsim çıkarma
        for trigger in ["benim adım", "ben ", "ismim "]:
            if trigger in msg:
                idx = msg.index(trigger) + len(trigger)
                possible_name = user_message[idx:idx+30].split()[0].strip(".,!?")
                if possible_name and len(possible_name) > 2 and not self.profile.get("name"):
                    self.update_profile("name", possible_name.capitalize())
                    return f"İsim öğrenildi: {possible_name}"
        
        # Şehir çıkarma
        sehirler = ["izmir", "istanbul", "ankara", "bursa", "antalya", "adana",
                    "konya", "gaziantep", "kayseri", "mersin", "eskişehir", "diyarbakır"]
        for sehir in sehirler:
            if sehir in msg and any(t in msg for t in ["yaşıyorum", "şehirdeyim", "lıyım", "liyim"]):
                self.update_profile("city", sehir.capitalize())
                return f"Şehir: {sehir.capitalize()}"
        
        # Meslek çıkarma
        meslekler = ["mühendis", "doktor", "öğretmen", "yazılımcı", "tekniker",
                     "uzman", "müdür", "asistan", "araştırmacı", "polimer"]
        for m in meslekler:
            if m in msg and any(t in msg for t in [" im", " yim", "olarak", "çalışıyorum"]):
                if m not in str(self.profile.get("facts", [])):
                    self.update_profile("facts", f"meslek: {m}")
                    return f"Meslek öğrenildi: {m}"
        
        return None
    def get_context(self, query: str = None) -> str:
        return self.get_context_for_prompt()