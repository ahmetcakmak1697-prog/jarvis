"""JARVIS BRAIN v5 — Multi-step reasoning + memory + research."""

import json
import sqlite3
import requests
import re
from pathlib import Path
from datetime import datetime

from tools.system_control import SystemController
from tools.web_research import WebResearcher
from agents.web_research_policy import WebResearchPolicy
from agents.memory_candidate_queue import MemoryCandidateQueue
from tools.document_reader import DocumentReader
from tools.diagnostics import run_diagnostics, run_self_tests
from tools.system_intelligence import format_panel_intelligence

from tools.file_tools import (
    count_text_in_file,
    count_regex_in_file,
    search_text_in_project,
    read_file,
    list_project_files,
)

from rich.console import Console

console = Console()


# Faz 1 — Yeni modüller, hata olursa devre dışı
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

# M0 - Model Registry / runtime profile. Hata olursa hardcoded MODEL'e duser.
try:
    from agents.model_registry import ModelRegistry
    REGISTRY_OK = True
except ImportError:
    REGISTRY_OK = False

try:
    from tools.vector_memory import VectorMemory
    VM_OK = True
except ImportError:
    VM_OK = False
    print("[WARN]  ChromaDB yok — vector memory devre dışı. pip install chromadb")

try:
    from agents.memory_retrieval_policy import MemoryRetrievalPolicy
    RETRIEVAL_POLICY_OK = True
except ImportError:
    RETRIEVAL_POLICY_OK = False


class JarvisBrain:
    MODEL = "mistral-nemo:latest"

    def __init__(self):
        self.profile_path = Path("memory/user_profile.json")
        self.db_path = Path("memory/jarvis_memory.db")
        self.conv_path = Path("memory/conversations.json")

        self.profile_path.parent.mkdir(parents=True, exist_ok=True)

        # M0: Aktif runtime profilinden ana modeli coz.
        # Profil okunamazsa class-level MODEL (mistral-nemo:latest) gecerli kalir.
        # Boylece mevcut sistem hicbir kosulda kirilmaz.
        self.registry = None
        if REGISTRY_OK:
            try:
                self.registry = ModelRegistry()
                resolved = self.registry.local_main(fallback=self.MODEL)
                if isinstance(resolved, str) and resolved.strip():
                    self.MODEL = resolved
                console.print(
                    f"[green]M0 profil: {self.registry.active_profile_name()} "
                    f"-> model: {self.MODEL}[/]"
                )
            except Exception as e:
                print(f"[WARN] ModelRegistry devre disi, MODEL fallback: {e}")

        self.profile = self._load_profile()
        self._init_db()
        self.history = []

        # System control
        try:
            self.system = SystemController()
        except Exception as e:
            self.system = None
            print(f"[WARN]  SystemController devre dışı: {e}")

        # Faz 1 modülleri
        self.router = self._safe_init("SemanticRouter", SemanticRouter) if ROUTER_OK else None
        self.scorer = self._safe_init("MemoryScorer", MemoryScorer) if SCORER_OK else None
        self.orch = self._safe_init("LLMOrchestrator", lambda: LLMOrchestrator(self.MODEL)) if ORCH_OK else None

        if self.router:
            console.print("[green]Semantic Router aktif[/]")
        if self.scorer:
            console.print("[green]Memory Scorer aktif[/]")
        if self.orch:
            console.print("[green]Multi-LLM Orchestrator aktif[/]")

        # Skill auto-discovery için sayaç
        self._recent_patterns = {}

        # Web araştırma
        self.researcher = WebResearcher()
        self.web_policy = WebResearchPolicy()
        self.memory_candidates = MemoryCandidateQueue()

        # Vector memory
        self.memory = None
        if VM_OK:
            try:
                self.memory = VectorMemory()
                print(f"[OK] VM: {self.memory.stats()['total']} hafıza")
            except Exception as e:
                print(f"[WARN]  VM err: {e}")

        # C1.4: retrieval policy filters vector recall before LLM context.
        self.memory_retrieval = None
        if RETRIEVAL_POLICY_OK:
            try:
                self.memory_retrieval = MemoryRetrievalPolicy(max_items=5, min_similarity=0.70)
                print("[OK] MemoryRetrievalPolicy: aktif")
            except Exception as e:
                self.memory_retrieval = None
                print(f"[WARN] MemoryRetrievalPolicy devre disi: {e}")

    def _safe_init(self, name, factory):
        """Opsiyonel JARVIS modüllerini güvenli başlatır; hata ana çekirdeği düşürmez."""
        try:
            obj = factory()
            print(f"[OK] {name}: aktif")
            return obj
        except Exception as e:
            print(f"[WARN] {name} devre disi: {e}")
            return None

    def _load_profile(self):
        if self.profile_path.exists():
            try:
                return json.loads(self.profile_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "name": None,
            "city": None,
            "facts": [],
            "interests": [],
            "preferences": {},
            "sevdiği": [],
            "sevmediği": [],
            "takım": [],
            "kullandığı": [],
            "sahip olduğu": [],
        }

    def _save_profile(self):
        self.profile_path.write_text(
            json.dumps(self.profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _init_db(self):
        c = sqlite3.connect(self.db_path)
        c.execute(
            """CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                user TEXT,
                jarvis TEXT,
                quality INTEGER DEFAULT 5,
                researched INTEGER DEFAULT 0
            )"""
        )
        c.commit()
        c.close()

    def _save_chat(self, u, j, q=5, r=False, memory_meta: dict | None = None):
        c = sqlite3.connect(self.db_path)
        c.execute(
            "INSERT INTO chats (ts, user, jarvis, quality, researched) "
            "VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), u, j, q, int(r)),
        )
        c.commit()
        c.close()

        self._save_train(u, j, q, r, memory_meta)

    def _save_train(self, u, j, q, r, memory_meta: dict | None = None):
        cs = []

        if self.conv_path.exists():
            try:
                cs = json.loads(self.conv_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        memory_meta = memory_meta or {}

        metadata = {
            "ts": datetime.now().isoformat(),
            "quality_score": q,
            "researched": r,
            "memory_action": memory_meta.get("memory_action", "unknown"),
            "memory_importance": memory_meta.get("memory_importance", q),
            "memory_tags": memory_meta.get("memory_tags", ""),
            "allow_vector": bool(memory_meta.get("allow_vector", False)),
            "allow_daily_summary": bool(memory_meta.get("allow_daily_summary", False)),
            "requires_review": bool(memory_meta.get("requires_review", False)),
        }

        cs.append(
            {
                "messages": [
                    {"role": "user", "content": u},
                    {"role": "assistant", "content": j},
                ],
                "metadata": metadata,
            }
        )

        self.conv_path.write_text(
            json.dumps(cs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _extract_info(self, msg):
        m = msg.lower().strip()

        # Sağlık kontrolü / diagnostics
        if any(x in m for x in [
            "kendini kontrol et",
            "sağlık kontrolü",
            "sistem durumu",
            "jarvis durumu",
            "diagnostics",
            "diag",
        ]):
            return run_diagnostics()

        # Proje dosyalarını listeleme

        patterns = [
            r"benim adım ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)",
            r"ismim ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)",
            r"adım ([a-zçğıöşü]+(?:\s[a-zçğıöşü]+)?)",
        ]

        for p in patterns:
            mt = re.search(p, m)
            if mt:
                n = mt.group(1).strip().title()
                if 2 < len(n) < 30 and n.lower() not in ["nerede", "ne", "kim", "var"]:
                    self.profile["name"] = n
                    self._save_profile()
                    return

    def _auto_learn(self, msg):
        m = msg.lower().strip()

        patterns = [
            (r"(\w+(?:\s\w+)?)\s+seviyorum", "sevdiği"),
            (r"(\w+(?:\s\w+)?)\s+sevmiyorum", "sevmediği"),
            (r"(\w+(?:\s\w+)?)\s+takımıyım", "takım"),
            (r"(\w+(?:\s\w+)?)\s+kullanıyorum", "kullandığı"),
            (r"benim\s+(\w+(?:\s\w+)?)\s+var", "sahip olduğu"),
        ]

        for p, lb in patterns:
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

        patterns = [
            r"\b(kaç|ne zaman|hangi yıl|hangi tarih|ne kadar|kim|nerede|nedir|kimdir)\b",
            r"\b(ne demek|ne anlama|ne işe yarar|nasıl çalışır|niye|neden)\b",
            r"\b(formül|denklem|değer|oran|yüzde|sıcaklık|kütle|hız)\b",
        ]

        for p in patterns:
            if re.search(p, m):
                return True

        sci_terms = [
            "ehull",
            "band gap",
            "atomic",
            "molar",
            "ev/atom",
            "kuantum",
            "spin",
            "compound",
            "kristal",
            "alaşım",
        ]

        if any(t in m for t in sci_terms):
            return True

        if re.search(r"\b[A-Z][a-zA-Z]*\d+[A-Z]?\b", msg):
            return True

        return False

    def _needs_web_research(self, msg: str, thinking: dict | None = None) -> bool:
        """Decide if web research is allowed and needed.

        D1 policy:
        - local/project/code/file questions stay local
        - sensitive/private data never leaves the machine
        - explicit web/current-info requests may proceed after sanitizer
        - model uncertainty alone is not enough to go online
        """
        thinking = thinking or {}

        if getattr(self, "web_policy", None):
            try:
                decision = self.web_policy.decide(msg, {
                    "thinking": thinking,
                    "source": "jarvis_brain",
                })

                self.last_web_policy_decision = decision.to_dict()

                if not decision.allow:
                    return False

                return decision.mode in ("explicit_web", "current_info")
            except Exception:
                pass

        # Safe fallback: only explicit web/current terms.
        m = (msg or "").lower().strip()

        explicit_terms = [
            "internetten bak",
            "webden bak",
            "google\'dan bak",
            "google dan bak",
            "online bak",
            "araştır",
            "arastir",
            "web araştır",
            "web arastir",
        ]

        current_terms = [
            "g?ncel",
            "guncel",
            "son durum",
            "son haber",
            "bug?n",
            "bugun",
            "bu hafta",
            "bu ay",
            "fiyat",
            "kur",
            "d?viz",
            "doviz",
            "mevzuat",
            "api de?i?ti mi",
            "api degisti mi",
            "model s?r?m?",
            "model surumu",
            "release",
            "changelog",
        ]

        return any(t in m for t in explicit_terms + current_terms)

    def _is_uncertain(self, r):
        return any(
            p in r.lower()
            for p in [
                "muhtemelen",
                "yaklaşık",
                "sanırım",
                "galiba",
                "tam emin değilim",
                "olabilir",
                "tahmin",
            ]
        )

    def _queue_web_memory_candidate(self, query: str, research: str, mode: str = "sync") -> dict:
        """Queue web research as reviewable memory candidate.

        D1.7 rule:
        - Web research must not enter long-term memory silently.
        - It becomes pending_review candidate only.
        """
        if not research or "Araştırma sonucu bulunamadı" in research:
            return {"ok": False, "reason": "empty_or_no_result"}

        try:
            source_scores = []
            if getattr(self, "researcher", None):
                source_scores = getattr(self.researcher, "last_source_scores", []) or []

            candidate = self.memory_candidates.add_web_candidate(
                query=query,
                research_text=research,
                source_scores=source_scores,
                mode=mode,
                ttl_days=60,
                tags=["web_research", "needs_user_review"],
            )

            self.last_memory_candidate = candidate
            return {"ok": True, "candidate": candidate}
        except Exception as exc:
            return {"ok": False, "reason": str(exc)[:200]}


    def _answer_from_research(self, research: str) -> str:
        """
        Web araştırması sonucunu LLM'e uydurtmadan, kaynak bloklarından güvenli cevap üretir.
        """
        if not research or "Araştırma sonucu bulunamadı" in research:
            return "Efendim, güvenilir bir araştırma sonucu bulamadım. Daha derin arama gerekir."

        blocks = re.split(r"\n\s*\[\d+\]\s+", research)
        clean_items = []

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            title_match = re.search(r"Başlık:\s*(.+)", block)
            source_match = re.search(r"Kaynak:\s*(.+)", block)
            summary_match = re.search(r"Özet:\s*(.+)", block, re.DOTALL)

            title = title_match.group(1).strip() if title_match else ""
            source = source_match.group(1).strip() if source_match else ""
            summary = summary_match.group(1).strip() if summary_match else ""

            if not title and not summary:
                continue

            summary = re.sub(r"\s+", " ", summary)
            if len(summary) > 260:
                summary = summary[:260].rsplit(" ", 1)[0] + "..."

            clean_items.append((title, source, summary))

            if len(clean_items) >= 4:
                break

        if not clean_items:
            return "Efendim, kaynaklar geldi fakat içlerinde net ve kullanılabilir özet bulunamadı."

        lines = ["Efendim, canlı web araştırmasına göre görünen kaynaklar şunlar:"]

        for i, (title, source, summary) in enumerate(clean_items, start=1):
            lines.append(f"\n{i}. {title}")
            if summary:
                lines.append(f"   Özet: {summary}")
            if source:
                lines.append(f"   Kaynak: {source}")

        lines.append(
            "\nNot: Bu cevap yalnızca yukarıdaki kaynak özetlerine dayalıdır; kaynaklarda açıkça görünmeyen detay eklemedim."
        )

        return "\n".join(lines)

    def _build_prompt(self, research="", memory=""):
        p = (
            "Sen JARVIS'sin. Iron Man'in Türkçe AI asistanı.\n\n"
            "KARAKTER:\n"
            "- 'Efendim' diye hitap edersin. Resmi, ölçülü, beyefendi.\n"
            "- 1-3 cümlelik kısa cevaplar.\n"
            "- İnce mizah olabilir, saygılı.\n\n"
            "🚨 ASLA UYDURMA:\n"
            "- Kesin BİLMEDİĞİN bilgiyi söyleme.\n"
            "- Sayı/formül/tarih/isim asla uydurma.\n"
            "- 'Muhtemelen', 'sanırım' deme.\n"
            "- Bilmiyorsan: 'Kesin bilgim yok efendim, araştırayım mı?'\n\n"
            "DİL: SADECE TÜRKÇE.\n"
            "\n## ORNEK DIYALOGLAR (bu tonu yakala, birebir kopyalama):\n"
            "\n# Hata + sinirli kullanici\n"
            "Kullanici: yine hata verdi ya bu calismiyor offf\n"
            "JARVIS: Sakin olun efendim, cozeriz. Once tam hata mesajini gorelim; tahminle ilerlersek ayni yere iki kez carpariz. Ciktiyi gonderin, hangi adimdan kirildigini net soyleyeyim.\n"
            "\n# Gec saat calisma\n"
            "Kullanici: saat 03:40 bir ozellik daha ekleyelim\n"
            "JARVIS: Ekleyebiliriz, ama saat gec. Yorgunken yazilan kod sabah iki kati zaman aldirir. Karar sizin: kucuk bir checkpoint alip devam mi, yoksa not dusup sabaha mi birakalim?\n"
            "\n# Teknik komut\n"
            "Kullanici: chromadbdeki kayit sayisini ogren\n"
            "JARVIS: Vector memory durumunu kontrol edelim efendim. Once sayiyi gormek icin kucuk bir okuma komutu calistiririz; yazma veya silme yapmayiz. Ciktiyi gorunce sonraki adimi soylerim.\n"
            "\n# Hafiza kaydi\n"
            "Kullanici: bunu hatirla: motor yagini her 5000 kmde degistiriyorum\n"
            "JARVIS: Kaydettim efendim. Bakim notu: motor yagi degisim araligi 5000 km.\n"
            "\n# Guncel bilgi / fiyat\n"
            "Kullanici: RTX 5090 fiyati ne kadar?\n"
            "JARVIS: Canli kaynaklara bakmadan net fiyat soylemem dogru olmaz. Fiyat, stok ve kura gore hizli degisir. Web arastirmasi yaparsam resmi saticilari ve guvenilir teknoloji kaynaklarini ayirip, tek kaynakli bilgiyi kesinmis gibi sunmam.\n"
            "\n# Hayal sistem sorusu\n"
            "Kullanici: 2x3090 alinca 70B model kusursuz calisir degil mi?\n"
            "JARVIS: Calisir hale getirmek gercekci, kusursuz demek degil. 2x3090 buyuk modeller icin ciddi alan acar ama hiz; quant, context, backend ve sogutmaya baglidir. Varsayilan yapmadan once benchmark aliriz; hayal guzel, olcmeden tahta cikarmayiz.\n"
            "\n# Eksik veri / log lazim\n"
            "Kullanici: neden bu kadar yavas aciliyor?\n"
            "JARVIS: Tahmin etmek istemem efendim, yanlis yone goturur. Baslangic logunu gorelim; model yukleme mi, RAG indeksleme mi, yoksa baska bir bekleme mi hemen ayiririz.\n"
            "\n# Basari sonrasi\n"
            "Kullanici: commit aldim, testler gecti\n"
            "JARVIS: Temiz is efendim. Once working treenin bos oldugunu dogrulayalim, sonra siradaki adima geceriz.\n"
        )

        if research:
            p += (
                f"\n\n## 🔍 ARAŞTIRMA SONUÇLARI:\n{research}\n\n"
                "ARAŞTIRMA CEVAP KURALLARI:\n"
                "- Sadece yukarıdaki araştırma sonuçlarında AÇIKÇA yazan bilgileri kullan.\n"
                "- Kaynaklarda görünmeyen olay, kişi, şirket, dava, tarih veya iddia ekleme.\n"
                "- Sonuçlar genel haber sayfasıysa bunu açıkça söyle.\n"
                "- Emin olmadığın detayı uydurma.\n"
                "- Cevabın sonunda kullanılan kaynak adlarını kısa yaz.\n"
                "- Eğer sonuçlar yetersizse: 'Kaynaklar genel kaldı, daha derin araştırma gerekir efendim.' de.\n"
            )

        if memory:
            p += (
                f"\n\n## 🧠 GEÇMİŞ:\n{memory}\n"
                "Bu geçmişi tanıyormuş gibi davran.\n"
            )

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
                json={
                    "model": self.MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2, "num_predict": 200},
                },
                timeout=45,
            )

            return json.loads(r.json().get("response", "{}"))

        except Exception:
            return {
                "knows_answer": True,
                "needs_research": False,
                "confidence": 0.5,
            }

    def _cross_check(self, msg: str, answer: str) -> str:
        """
        Cross-check: Cevabı araştırma sonucu ile karşılaştırır.
        Dosya/proje aracı sorularında çalışmaz.
        """
        if self._try_file_tool(msg):
            return answer

        if not self._is_factual(msg) or not self.researcher:
            return answer

        low = answer.lower()

        if "bilmiyorum" in low or "araştır" in low or "emin değilim" in low:
            return answer

        research = self.researcher.research_and_learn(msg)

        if not research:
            return answer

        check_prompt = f"""SORU: {msg}

CEVAP-1:
{answer[:500]}

CEVAP-2 ARAŞTIRMA:
{research[:1000]}

JSON döndür:
{{
  "uyumlu_mu": <true/false>,
  "düzeltme": "<doğru cevap>"
}}"""

        try:
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.MODEL,
                    "prompt": check_prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=60,
            )

            check = json.loads(r.json().get("response", "{}"))

            if not check.get("uyumlu_mu", True) and check.get("düzeltme"):
                console.print("[yellow]🛡️ Cross-Check: cevap düzeltildi[/]")
                return check["düzeltme"]

        except Exception:
            pass

        return answer

    def _detect_skill_pattern(self, msg: str):
        """
        Skill Auto-Discovery:
        3+ kez tekrarlanan kalıpları skill yapar.
        """
        key_words = re.findall(r"\b\w{4,}\b", msg.lower())[:3]

        if not key_words:
            return

        pattern = " ".join(sorted(key_words))
        self._recent_patterns[pattern] = self._recent_patterns.get(pattern, 0) + 1

        if self._recent_patterns[pattern] == 3:
            try:
                from agents.skill_library import SkillLibrary

                lib = SkillLibrary()
                name = f"auto_{pattern.replace(' ', '_')[:30]}"
                lib.add(
                    name,
                    [pattern],
                    f"Otomatik tespit: '{msg}'",
                    tags=["auto-learned"],
                )
                console.print(f"[cyan]📚 Yeni skill tespiti: {name}[/]")

            except Exception:
                pass

    def _try_file_tool(self, msg: str):
        """
        Dosya/kod/proje içeriği sorularında LLM'e tahmin ettirmez.
        Doğrudan dosya araçlarını çalıştırır.
        """
        m = msg.lower().strip()

        # Proje dosyalarını listeleme
        if any(
            x in m
            for x in [
                "dosyaları listele",
                "proje dosyaları",
                "klasör ağacı",
                "hangi dosyalar var",
            ]
        ):
            return list_project_files()

        # Proje içinde metin arama
        search_patterns = [
            r"projede ['\"](.+?)['\"] ara",
            r"proje içinde ['\"](.+?)['\"] ara",
            r"nerede geçiyor ['\"](.+?)['\"]",
            r"['\"](.+?)['\"] nerede geçiyor",

            # Tırnaksız kullanım:
            # projede research_and_learn ara
            # proje içinde TavilyClient ara
            # research_and_learn nerede geçiyor
            r"projede\s+([A-Za-z0-9_\-\.]+)\s+ara",
            r"proje içinde\s+([A-Za-z0-9_\-\.]+)\s+ara",
            r"([A-Za-z0-9_\-\.]+)\s+nerede geçiyor",
        ]

        for pattern in search_patterns:
            mt = re.search(pattern, msg, re.IGNORECASE)
            if mt:
                text = mt.group(1).strip()
                return search_text_in_project(text)

        # Kod kelimesi sayma:
        # jarvis_brain.py dosyasında kaç tane def var
        # brain dosyasında kaç tane elif var
        if "kaç" in m and any(x in m for x in ["var", "geçiyor", "bulunuyor", "tane"]):
            code_words = [
                "elif",
                "def",
                "class",
                "return",
                "import",
                "if",
                "for",
                "while",
                "try",
                "except",
                "with",
                "from",
                "pass",
                "break",
                "continue",
            ]

            wanted_word = None

            for word in code_words:
                if re.search(rf"\b{re.escape(word)}\b", m):
                    wanted_word = word
                    break

            if wanted_word:
                file_match = re.search(r"([\w\-/\\\.]+\.py)", msg, re.IGNORECASE)

                if file_match:
                    file_path = file_match.group(1).strip()
                elif "brain" in m or "beyin" in m or "jarvis_brain" in m:
                    file_path = "jarvis_brain.py"
                else:
                    file_path = None

                if file_path:
                    return count_regex_in_file(
                        file_path,
                        rf"\b{re.escape(wanted_word)}\b",
                    )

        # Dosya okuma
        read_patterns = [
            r"([\w\-/\\\.]+\.py).*oku",
            r"oku.*([\w\-/\\\.]+\.py)",
            r"([\w\-/\\\.]+\.txt).*oku",
            r"oku.*([\w\-/\\\.]+\.txt)",
            r"([\w\-/\\\.]+\.md).*oku",
            r"oku.*([\w\-/\\\.]+\.md)",
            r"([\w\-/\\\.]+\.json).*oku",
            r"oku.*([\w\-/\\\.]+\.json)",
        ]

        for pattern in read_patterns:
            mt = re.search(pattern, msg, re.IGNORECASE)
            if mt:
                file_path = mt.group(1).strip()
                return read_file(file_path)

        return None

    def chat(self, msg):
        """
        Ana konuşma akışı.

        Faz -1/0/1 düzeltmesi:
        - Her başarılı/başarısız path kesinlikle str döndürür.
        - Explicit memory, file tool, system command, web research ve LLM cevabı net ayrılır.
        - Önceki refactor'dan kalan erişilemeyen/ölü kod kaldırıldı.
        """
        msg = (msg or "").strip()
        if not msg:
            return "Efendim, boş bir komut aldım. Ne yapmamı istediğinizi yazarsanız hemen ilgilenirim."

        m = msg.lower().strip()

        try:
            if any(x in m for x in [
                "kendini test et",
                "self test",
                "self-test",
                "çekirdek test",
                "sistem testi",
            ]):
                result = run_self_tests()
                self._add_history(msg, result)
                self._save_chat(msg, result, q=8, r=False)
                return result

            if any(x in m for x in [
                "kendini kontrol et",
                "sağlık kontrolü",
                "sistem durumu",
                "jarvis durumu",
                "diagnostics",
                "diag",
            ]):
                result = run_diagnostics()
                self._add_history(msg, result)
                self._save_chat(msg, result, q=8, r=False)
                return result

            if any(x in m for x in [
                "panel zekasını göster",
                "panel zekası",
                "operasyon paneli",
                "jarvis panel",
                "durum zekası",
            ]):
                result = format_panel_intelligence()
                self._add_history(msg, result)
                self._save_chat(msg, result, q=8, r=False)
                return result

            self._extract_info(msg)
            self._auto_learn(msg)

            explicit_memory_result = self._handle_explicit_memory(msg)
            if explicit_memory_result:
                return explicit_memory_result

            # Önce dosya/proje/kod araçları.
            file_tool_result = self._try_file_tool(msg)
            if file_tool_result:
                self._add_history(msg, file_tool_result)
                self._save_chat(msg, file_tool_result, q=8, r=False)
                return file_tool_result

            # Faz 1: Router ve skill pattern gözlemi. Hata üretirse ana akışı bozmaz.
            if getattr(self, "router", None):
                try:
                    route_info = self.router.explain(msg)
                    console.print(f"[dim]🧭 Route: {route_info.get('route', 'unknown')}[/]")
                except Exception:
                    pass

            try:
                self._detect_skill_pattern(msg)
            except Exception:
                pass

            # Sistem komutu.
            if self.system:
                try:
                    cmd = self.system.detect_command(msg)
                except Exception:
                    cmd = None

                if cmd:
                    try:
                        res = self.system.execute(cmd[0], cmd[1])
                    except Exception as e:
                        res = f"Sistem komutunu çalıştırırken hata aldım efendim: {str(e)[:120]}"

                    if res:
                        self._add_history(msg, res)
                        self._save_chat(msg, res, q=6, r=False)
                        return res

            # Vector recall.
            mem_ctx = ""
            if self.memory:
                try:
                    sim = self.memory.find_similar(msg, n=5, threshold=0.7)
                except Exception:
                    sim = []

                if sim and self.memory_retrieval:
                    try:
                        sim = self.memory_retrieval.filter_hits(sim, query=msg)
                    except Exception:
                        sim = []

                if sim:
                    mem_ctx = "\n".join(
                        f"- (Geçmiş) {s.get('user_msg', '')} → {s.get('jarvis_msg', '')[:120]}..."
                        for s in sim[:3]
                    )

            # Düşünme/niyet analizi.
            thinking = self._think(msg)
            if not isinstance(thinking, dict):
                thinking = {"knows_answer": True, "needs_research": False, "confidence": 0.5, "topic": ""}

            conf = float(thinking.get("confidence", 0.5) or 0.5)
            research = ""

            # Canlı araştırma gerekiyorsa deterministik güvenli cevap dön.
            should_r = self._needs_web_research(msg, thinking)
            if should_r:
                mem_ctx = ""
                print(f"🔍 Araştır (conf:{conf:.1f}): {msg[:50]}")

                try:
                    self.researcher.cache = {}
                except Exception:
                    pass

                try:
                    research = self.researcher.research_and_learn(msg)
                except Exception as e:
                    research = ""
                    print(f"[FAIL] Araştırma hatası: {e}")

                print(f"{'[OK]' if research else '[FAIL]'} {len(research)} char")

                candidate_result = self._queue_web_memory_candidate(msg, research, mode="sync")
                if candidate_result.get("ok"):
                    print("[OK] Web memory candidate queued.")

                safe_answer = self._answer_from_research(research)

                candidate = candidate_result.get("candidate") if isinstance(candidate_result, dict) else None
                if candidate:
                    safe_answer += (
                        "\n\nEfendim, bu araştırmadan kalıcı hafıza adayı oluşturdum. "
                        "Onayınıza kadar uzun hafızaya yazmayacağım."
                    )

                self._add_history(msg, safe_answer)
                self._save_chat(msg, safe_answer, q=8, r=True)
                return safe_answer

            # LLM cevabı üret.
            messages = [{"role": "system", "content": self._build_prompt(research, mem_ctx)}]
            messages.extend(self.history[-6:])
            messages.append({"role": "user", "content": msg})

            try:
                r = requests.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": self.MODEL,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_ctx": 4096,
                            "num_predict": 300,
                        },
                    },
                    timeout=120,
                )
                r.raise_for_status()
                cevap = r.json().get("message", {}).get("content", "").strip()
            except Exception as e:
                cevap = f"Hata efendim: Ollama yanıtı alınamadı. Detay: {str(e)[:100]}"

            if not isinstance(cevap, str) or not cevap.strip():
                cevap = "Efendim, cevap üretildi fakat boş döndü. Alt sistemi kontrol etmek gerekiyor."

            # Belirsizlik varsa bir kez araştırma ile sağlamlaştırmayı dene.
            if self._is_uncertain(cevap) and not research and self._needs_web_research(msg, thinking):
                try:
                    print("[WARN]  Belirsiz, araştır...")
                    research = self.researcher.research_and_learn(msg)
                except Exception:
                    research = ""

                if research:
                    candidate_result = self._queue_web_memory_candidate(msg, research, mode="sync")
                    if candidate_result.get("ok"):
                        print("[OK] Web memory candidate queued.")

                    messages[0] = {
                        "role": "system",
                        "content": self._build_prompt(research, mem_ctx),
                    }
                    try:
                        r = requests.post(
                            "http://localhost:11434/api/chat",
                            json={
                                "model": self.MODEL,
                                "messages": messages,
                                "stream": False,
                                "options": {
                                    "temperature": 0.2,
                                    "num_predict": 300,
                                },
                            },
                            timeout=120,
                        )
                        r.raise_for_status()
                        cevap = r.json().get("message", {}).get("content", cevap).strip() or cevap
                    except Exception:
                        pass

            # Cross-check hata verse bile cevap çöpe gitmesin.
            try:
                cevap = self._cross_check(msg, cevap)
            except Exception:
                pass

            if len(cevap) > 600:
                cevap = cevap[:600].rsplit(".", 1)[0] + "."

            self._add_history(msg, cevap)

            q = 5
            memory_decision = None

            if research:
                q = 7
            if "bilmiyorum" in cevap.lower() or "ara" in cevap.lower():
                q = max(q, 6)

            if getattr(self, "scorer", None):
                try:
                    memory_decision = self.scorer.policy_decision(msg, cevap)
                    q = self.scorer.score(msg, cevap)
                except Exception:
                    memory_decision = None

            if not isinstance(memory_decision, dict):
                memory_decision = {
                    "action": "temporary",
                    "importance": q,
                    "reason": "Memory policy unavailable.",
                    "tags": ["policy_fallback"],
                    "retention_days": 14,
                    "allow_vector": False,
                    "allow_daily_summary": False,
                    "requires_review": False,
                }

            mem_tags = memory_decision.get("tags", [])
            if isinstance(mem_tags, list):
                mem_tags = ",".join(str(t) for t in mem_tags)

            mem_meta = {
                "researched": bool(research),
                "confidence": conf,
                "topic": thinking.get("topic", ""),
                "type": "chat",
                "memory_action": memory_decision.get("action", "temporary"),
                "memory_importance": int(memory_decision.get("importance", q) or q),
                "memory_tags": str(mem_tags or ""),
                "allow_vector": bool(memory_decision.get("allow_vector", False)),
                "allow_daily_summary": bool(memory_decision.get("allow_daily_summary", False)),
                "requires_review": bool(memory_decision.get("requires_review", False)),
            }

            if self.memory and self._should_remember(msg, cevap, mem_meta):
                try:
                    self.memory.remember(msg, cevap, mem_meta)
                except Exception:
                    pass

            self._save_chat(msg, cevap, q, bool(research), mem_meta)
            return cevap

        except Exception as e:
            # Son sigorta: chat() hiçbir koşulda None döndürmemeli.
            fallback = f"Efendim, konuşma akışında beklenmeyen bir hata oluştu: {str(e)[:120]}"
            try:
                self._add_history(msg, fallback)
                self._save_chat(msg, fallback, q=3, r=False)
            except Exception:
                pass
            return fallback

    def _should_remember(self, msg: str, answer: str = "", meta: dict | None = None) -> bool:
        """Decide whether an exchange may be written to long-term vector memory.

        C1 policy rule:
        - only keep_long_term + allow_vector can enter vector memory
        - sensitive_review never enters vector memory
        - researched/debug/file/test content stays out
        """
        m = (msg or "").lower().strip()
        meta = meta or {}

        blocked_terms = [
            "test_jarvis_tools",
            "test et",
            "deneme",
            "debug",
            "traceback",
            "proje dosyalari",
            "proje dosyalar?",
            "dosyalari listele",
            "dosyalar? listele",
            "klasor agaci",
            "klas?r a?ac?",
            "nerede geciyor",
            "nerede ge?iyor",
            "dosyasini oku",
            "dosyas?n? oku",
            ".py",
            ".json",
            ".txt",
            "kac tane def",
            "ka? tane def",
            "kac tane elif",
            "ka? tane elif",
            "kac tane class",
            "ka? tane class",
            "kac tane import",
            "ka? tane import",
        ]

        if any(t in m for t in blocked_terms):
            return False

        blocked_types = {
            "file_tool",
            "command",
            "web_research_safe",
            "debug",
            "test",
        }

        if meta.get("type") in blocked_types:
            return False

        if meta.get("researched") is True:
            return False

        if meta.get("requires_review") is True:
            return False

        if meta.get("allow_vector") is False:
            return False

        action = str(meta.get("memory_action", "") or "")
        if action:
            return action == "keep_long_term"

        if getattr(self, "scorer", None):
            try:
                decision = self.scorer.policy_decision(msg, answer)
                return (
                    decision.get("action") == "keep_long_term"
                    and decision.get("allow_vector") is True
                    and decision.get("requires_review") is not True
                )
            except Exception:
                return False

        return False

    def _handle_explicit_memory(self, msg: str):
        """Handle explicit save requests with MemoryPolicy safety gate."""
        original = msg or ""
        m = original.lower().strip()

        remember_terms = [
            "bunu hat?rla",
            "bunu hatirla",
            "bunu unutma",
            "akl?nda tut",
            "aklinda tut",
            "kaydet",
            "not al",
        ]

        if not any(t in m for t in remember_terms):
            return None

        clean_msg = original.strip()
        for phrase in remember_terms:
            clean_msg = re.sub(re.escape(phrase), "", clean_msg, flags=re.IGNORECASE)

        clean_msg = clean_msg.replace(":", " ").replace(",", " ").strip()
        clean_msg = re.sub(r"\s+", " ", clean_msg)

        if not clean_msg:
            clean_msg = original.strip()

        answer = f"Kaydettim efendim: {clean_msg}"
        decision = None
        q = 9

        if getattr(self, "scorer", None):
            try:
                decision = self.scorer.policy_decision(original, answer)
                q = self.scorer.score(original, answer)
            except Exception:
                decision = None

        if not isinstance(decision, dict):
            decision = {
                "action": "temporary",
                "importance": q,
                "reason": "Memory policy unavailable.",
                "tags": ["policy_fallback"],
                "allow_vector": False,
                "allow_daily_summary": False,
                "requires_review": False,
            }

        tags = decision.get("tags", [])
        if isinstance(tags, list):
            tags = ",".join(str(t) for t in tags)

        mem_meta = {
            "type": "explicit_memory",
            "importance": int(decision.get("importance", q) or q),
            "memory_action": decision.get("action", "temporary"),
            "memory_tags": str(tags or ""),
            "allow_vector": bool(decision.get("allow_vector", False)),
            "allow_daily_summary": bool(decision.get("allow_daily_summary", False)),
            "requires_review": bool(decision.get("requires_review", False)),
        }

        if self.memory and self._should_remember(original, answer, mem_meta):
            try:
                self.memory.remember(original, answer, mem_meta)
            except Exception:
                pass

        self._add_history(original, answer)
        self._save_chat(original, answer, q=q, r=False, memory_meta=mem_meta)
        return answer

    def _add_history(self, u, j):
        self.history.append({"role": "user", "content": u})
        self.history.append({"role": "assistant", "content": j})

        if len(self.history) > 20:
            self.history = self.history[-20:]

    def analyze_document(self, file_path, question=None):
        """
        Dokümanı oku ve analiz et.
        """
        summary = DocumentReader.summary(file_path, max_chars=4000)

        if "error" in str(summary).lower():
            return summary

        q = question or "Bu dokümanı özetle ve ana noktaları çıkar."

        prompt = f"""Aşağıdaki doküman içeriğini analiz et.

DOKÜMAN:
{summary}

GÖREV:
{q}

Türkçe, net, kısa cevap ver."""

        try:
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 500,
                    },
                },
                timeout=180,
            )

            return r.json().get("response", "").strip()

        except Exception as e:
            return f"Analiz hatası: {e}"