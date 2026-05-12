"""JARVIS BRAIN v5 — Multi-step reasoning + memory + research."""
import json
import sqlite3
import requests
import re
from pathlib import Path
from datetime import datetime
from tools.system_control import SystemController
from tools.web_research import WebResearcher
from tools.document_reader import DocumentReader
from rich.console import Console
console = Console()

# Faz 1 — Yeni modüller (opsiyonel, hata olursa devre dışı)
try:
    from agents.semantic_router import SemanticRouter
    ROUTER_OK = True
except ImportError:
    ROUTER_OK = False

try:
    from agents.memory_scorer import MemoryScorer
    SCORER_OK = True
except ImportError:
    SCORER_OK = False

try:
    from agents.orchestrator import LLMOrchestrator
    ORCH_OK = True
except ImportError:
    ORCH_OK = False

try:
    from tools.vector_memory import VectorMemory
    VM_OK = True
except ImportError:
    VM_OK = False
    print("⚠️  ChromaDB yok — vector memory devre dışı (pip install chromadb)")


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
       # System control (opsiyonel)
        try:
            self.system = SystemController()
        except Exception:
            self.system = None

        # Faz 1 modülleri
        self.router = SemanticRouter() if ROUTER_OK else None
        self.scorer = MemoryScorer() if SCORER_OK else None
        self.orch   = LLMOrchestrator(self.MODEL) if ORCH_OK else None
        
        if self.router: console.print("[green]✓ Semantic Router aktif[/]")
        if self.scorer: console.print("[green]✓ Memory Scorer aktif[/]")
        if self.orch:   console.print("[green]✓ Multi-LLM Orchestrator aktif[/]")

        # Skill auto-discovery için sayaç
        self._recent_patterns = {}  # {pattern: count}
        self.researcher = WebResearcher()
        self.memory = None
        if VM_OK:
            try:
                self.memory = VectorMemory()
                print(f"✅ VM: {self.memory.stats()['total']} hafıza")
            except Exception as e:
                print(f"⚠️  VM err: {e}")

    def _load_profile(self):
        if self.profile_path.exists():
            try:
                return json.loads(self.profile_path.read_text(encoding='utf-8'))
            except:
                pass
        return {"name": None, "city": None, "facts": [], "interests": [],
                "preferences": {}, "sevdiği": [], "sevmediği": [],
                "takım": [], "kullandığı": [], "sahip olduğu": []}

    def _save_profile(self):
        self.profile_path.write_text(
            json.dumps(self.profile, ensure_ascii=False, indent=2),
            encoding='utf-8')

    def _init_db(self):
        c = sqlite3.connect(self.db_path)
        c.execute("""CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, user TEXT, jarvis TEXT,
            quality INTEGER DEFAULT 5,
            researched INTEGER DEFAULT 0)""")
        c.commit(); c.close()

    def _save_chat(self, u, j, q=5, r=False):
        c = sqlite3.connect(self.db_path)
        c.execute("INSERT INTO chats (ts, user, jarvis, quality, researched) "
                  "VALUES (?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), u, j, q, int(r)))
        c.commit(); c.close()
        self._save_train(u, j, q, r)

    def _save_train(self, u, j, q, r):
        cs = []
        if self.conv_path.exists():
            try:
                cs = json.loads(self.conv_path.read_text(encoding='utf-8'))
            except:
                pass
        cs.append({
            "messages": [
                {"role": "user", "content": u},
                {"role": "assistant", "content": j}
            ],
            "metadata": {"ts": datetime.now().isoformat(),
                         "quality_score": q, "researched": r}
        })
        self.conv_path.write_text(
            json.dumps(cs, ensure_ascii=False, indent=2), encoding='utf-8')

    def _extract_info(self, msg):
        m = msg.lower().strip()
        for p in [r"benim adım ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)",
                  r"ismim ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)",
                  r"adım ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)"]:
            mt = re.search(p, m)
            if mt:
                n = mt.group(1).strip().title()
                if 2 < len(n) < 30 and n.lower() not in ["nerede", "ne", "kim", "var"]:
                    self.profile["name"] = n
                    self._save_profile()
                    return

    def _auto_learn(self, msg):
        m = msg.lower().strip()
        for p, lb in [
            (r"(\w+(?:\s\w+)?)\s+seviyorum", "sevdiği"),
            (r"(\w+(?:\s\w+)?)\s+sevmiyorum", "sevmediği"),
            (r"(\w+(?:\s\w+)?)\s+takımıyım", "takım"),
            (r"(\w+(?:\s\w+)?)\s+kullanıyorum", "kullandığı"),
            (r"benim\s+(\w+(?:\s\w+)?)\s+var", "sahip olduğu")
        ]:
            mt = re.search(p, m)
            if mt:
                v = mt.group(1).strip().title()
                if 2 < len(v) < 40:
                    self.profile.setdefault(lb, [])
                    if v not in self.profile[lb]:
                        self.profile[lb].append(v)
                        self._save_profile()

    def _is_factual(self, msg):
        m = msg.lower()
        for p in [
            r"\b(kaç|ne zaman|hangi yıl|hangi tarih|ne kadar|kim|nerede|nedir|kimdir)\b",
            r"\b(ne demek|ne anlama|ne işe yarar|nasıl çalışır|niye|neden)\b",
            r"\b(formül|denklem|değer|oran|yüzde|sıcaklık|kütle|hız)\b"]:
            if re.search(p, m):
                return True
        sci = ["ehull", "band gap", "atomic", "molar", "ev/atom",
               "kuantum", "spin", "compound", "kristal", "alaşım"]
        if any(t in m for t in sci):
            return True
        if re.search(r'\b[A-Z][a-zA-Z]*\d+[A-Z]?\b', msg):
            return True
        return False

    def _is_uncertain(self, r):
        return any(p in r.lower() for p in
                   ["muhtemelen", "yaklaşık", "sanırım", "galiba",
                    "tam emin değilim", "olabilir", "tahmin"])

    def _build_prompt(self, research="", memory=""):
        p = ("Sen JARVIS'sin. Iron Man'in Türkçe AI asistanı.\n\n"
             "KARAKTER:\n"
             "- 'Efendim' diye hitap edersin. Resmi, ölçülü, beyefendi.\n"
             "- 1-3 cümlelik kısa cevaplar.\n"
             "- İnce mizah olabilir, saygılı.\n\n"
             "🚨 ASLA UYDURMA:\n"
             "- Kesin BİLMEDİĞİN bilgiyi söyleme.\n"
             "- Sayı/formül/tarih/isim asla uydurma.\n"
             "- 'Muhtemelen', 'sanırım' deme.\n"
             "- Bilmiyorsan: 'Kesin bilgim yok efendim, araştırayım mı?'\n\n"
             "DİL: SADECE TÜRKÇE.\n")
        if research:
            p += (f"\n\n## 🔍 ARAŞTIRMA SONUÇLARI:\n{research}\n\n"
                  "Sadece yukarıdaki kaynaklara göre cevap ver.\n")
        if memory:
            p += (f"\n\n## 🧠 GEÇMİŞ:\n{memory}\n"
                  "Bu geçmişi tanıyormuş gibi davran.\n")
        if self.profile.get("name"):
            p += f"\n## KULLANICI: {self.profile['name']}\n"
            if self.profile.get("city"):
                p += f"- Şehir: {self.profile['city']}\n"
            for lb in ["sevdiği", "sevmediği", "takım", "kullandığı"]:
                its = self.profile.get(lb, [])
                if its:
                    p += f"- {lb.title()}: {', '.join(its)}\n"
        return p

    def _think(self, msg):
        prompt = f"""Mesaj için kısa içsel analiz.

KULLANICI: {msg}

JSON:
{{
  "intent": "<soru/komut/sohbet/duygusal>",
  "knows_answer": <true/false>,
  "needs_research": <true/false>,
  "confidence": <0.0-1.0>,
  "topic": "<2-3 kelime>"
}}"""
        try:
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.MODEL, "prompt": prompt,
                      "stream": False, "format": "json",
                      "options": {"temperature": 0.2, "num_predict": 200}},
                timeout=45)
            return json.loads(r.json().get("response", "{}"))
        except:
            return {"knows_answer": True, "needs_research": False, "confidence": 0.5}
        
    def _cross_check(self, msg: str, answer: str) -> str:
        """C) Cross-Check: Cevabı araştırma sonucu ile karşılaştırır."""
        if not self._is_factual(msg) or not self.researcher:
            return answer
        low = answer.lower()
        if "bilmiyorum" in low or "araştır" in low or "emin değilim" in low:
            return answer

        research = self.researcher.research_and_learn(msg)
        if not research:
            return answer

        check_prompt = f"""SORU: {msg}\nCEVAP-1: {answer[:500]}\nCEVAP-2 (Araştırma): {research[:1000]}\nJSON döndür: {{"uyumlu_mu": <true/false>, "düzeltme": "<doğru cevap>"}}"""
        try:
            r = requests.post("http://localhost:11434/api/generate",
                json={"model": self.MODEL, "prompt": check_prompt, "stream": False, "format": "json"},
                timeout=60)
            check = json.loads(r.json().get("response", "{}"))
            if not check.get("uyumlu_mu", True) and check.get("düzeltme"):
                console.print("[yellow]🛡️ Cross-Check: cevap düzeltildi[/]")
                return check["düzeltme"]
        except: pass
        return answer

    def _detect_skill_pattern(self, msg: str):
        """E) Skill Auto-Discovery: 3+ kez tekrarlanan kalıpları skill yapar."""
        key_words = re.findall(r'\b\w{4,}\b', msg.lower())[:3]
        if not key_words: return
        pattern = " ".join(sorted(key_words))
        self._recent_patterns[pattern] = self._recent_patterns.get(pattern, 0) + 1

        if self._recent_patterns[pattern] == 3:
            try:
                from agents.skill_library import SkillLibrary
                lib = SkillLibrary()
                name = f"auto_{pattern.replace(' ', '_')[:30]}"
                lib.add(name, [pattern], f"Otomatik tespit: '{msg}'", tags=["auto-learned"])
                console.print(f"[cyan]📚 Yeni skill tespiti: {name}[/]")
            except: pass

    def chat(self, msg):
        self._extract_info(msg)
        self._auto_learn(msg)
# ✨ Faz 1: Router ve Skill
        if getattr(self, 'router', None):
            route_info = self.router.explain(msg)
            console.print(f"[dim]🧭 Route: {route_info['route']}[/]")
        self._detect_skill_pattern(msg)

        # 1) Sistem komutu
        cmd = self.system.detect_command(msg)
        if cmd:
            res = self.system.execute(cmd[0], cmd[1])
            if res:
                self._add_history(msg, res)
                self._save_chat(msg, res, q=6)
                if self.memory:
                    self.memory.remember(msg, res, {"type": "command"})
                return res

        # 2) Vector recall
        mem_ctx = ""
        if self.memory:
            sim = self.memory.find_similar(msg, n=3, threshold=0.7)
            if sim:
                mem_ctx = "\n".join(
                    f"- (Geçmiş) {s['user_msg']} → {s['jarvis_msg'][:120]}..."
                    for s in sim[:2])

        # 3) Düşün
        thinking = self._think(msg)
        conf = thinking.get("confidence", 0.5)
        nr = thinking.get("needs_research", False)
        knows = thinking.get("knows_answer", True)

        # 4) Araştırma
        research = ""
        should_r = nr or self._is_factual(msg) or (not knows and conf < 0.6)
        if should_r:
            print(f"🔍 Araştır (conf:{conf:.1f}): {msg[:50]}")
            research = self.researcher.research_and_learn(msg)
            print(f"{'✅' if research else '❌'} {len(research)} char")

        # 5) Cevap üret
        messages = [{"role": "system", "content": self._build_prompt(research, mem_ctx)}]
        messages.extend(self.history[-6:])
        messages.append({"role": "user", "content": msg})

        try:
            r = requests.post(
                "http://localhost:11434/api/chat",
                json={"model": self.MODEL, "messages": messages,
                      "stream": False,
                      "options": {"temperature": 0.4, "num_ctx": 4096,
                                  "num_predict": 300}},
                timeout=120)
            cevap = r.json().get("message", {}).get("content", "Yanıt yok").strip()
        except Exception as e:
            return f"Hata efendim: {str(e)[:80]}"

        # 6) Belirsizlik → ek araştırma
        if self._is_uncertain(cevap) and not research:
            print("⚠️  Belirsiz, araştır...")
            research = self.researcher.research_and_learn(msg)
            if research:
                messages[0] = {"role": "system",
                               "content": self._build_prompt(research, mem_ctx)}
                try:
                    r = requests.post(
                        "http://localhost:11434/api/chat",
                        json={"model": self.MODEL, "messages": messages,
                              "stream": False,
                              "options": {"temperature": 0.3, "num_predict": 300}},
                        timeout=120)
                    cevap = r.json().get("message", {}).get("content", cevap).strip()
                except:
                    pass

# ✨ Faz 1: Cross-Check
        cevap = self._cross_check(msg, cevap)
        if len(cevap) > 600:
            cevap = cevap[:600].rsplit(".", 1)[0] + "."

        self._add_history(msg, cevap)
        if self.memory:
            self.memory.remember(msg, cevap, {
                "researched": bool(research), "confidence": conf,
                "topic": thinking.get("topic", "")
            })

        q = 5
        if research: q = 7
        if "bilmiyorum" in cevap.lower() or "araştır" in cevap.lower():
            q = max(q, 6)
            # ✨ Faz 1: Memory Scorer ile gerçek puan
        if getattr(self, 'scorer', None):
            q = self.scorer.score(msg, cevap)
        self._save_chat(msg, cevap, q, bool(research))
        return cevap

    def _add_history(self, u, j):
        self.history.append({"role": "user", "content": u})
        self.history.append({"role": "assistant", "content": j})
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def analyze_document(self, file_path, question=None):
        """Dokümanı oku ve analiz et"""
        summary = DocumentReader.summary(file_path, max_chars=4000)
        if "error" in str(summary).lower():
            return summary
        q = question or "Bu dokümanı özetle ve ana noktaları çıkar."
        prompt = f"""Aşağıdaki doküman içeriğini analiz et.

DOKÜMAN:
{summary}

GÖREV: {q}

Türkçe, net, kısa cevap ver."""
        try:
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.MODEL, "prompt": prompt,
                      "stream": False,
                      "options": {"temperature": 0.4, "num_predict": 500}},
                timeout=180)
            return r.json().get("response", "").strip()
        except Exception as e:
            return f"Analiz hatası: {e}"
