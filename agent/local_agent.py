"""
jarvis/agent/local_agent.py — v5
Doğal sohbet + temiz yanıtlar
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional
from rich.console import Console

from agents.data_classifier import _fold_tr, keyword_present
from agents.model_registry import ModelRegistry
from agents.persona import VOICE_MODE_DIRECTIVE, build_system_prompt

console = Console()

#: Tur siniflandirmasi -> persona seviyesi. Ayni siniflandirma hem modeli hem
#: prompt derinligini secer; iki yerde ayri esik tutulmaz.
_TIER_TO_LEVEL = {"fast": "L1", "mid": "L2", "deep": "L3"}

#: Selamlama ve nezaket deyimleri (fold'lanmis). Iki isi birden yapar:
#: bunlar ARAC TETIKLEMEZ ve `fast` sinifina duser.
#:
#: Neden ayri bir katman: canli testte "Ne haber Jarvis?" web aramasi
#: tetikledi, cunku "haber" TOOL_TRIGGERS icinde. Kelime siniri bunu cozmez --
#: "ne haber" icinde "haber" zaten tam kelime. Ayrim deyimde: "ne haber" bir
#: selamlamadir, "son dakika haberleri" bir arama istegidir.
_SELAMLAR: tuple[str, ...] = (
    "merhaba", "selam", "naber", "ne haber", "ne haberler",
    "gunaydin", "iyi sabahlar", "iyi aksamlar", "iyi geceler", "iyi gunler",
    "nasilsin", "nasilsiniz", "iyi misin", "iyi misiniz", "keyifler nasil",
    "tesekkur", "tesekkurler", "sag ol", "sagol", "eyvallah",
    "gorusuruz", "hosca kal", "kolay gelsin", "hos geldin",
    "tamam", "peki", "anladim", "evet", "hayir", "olur",
)

#: Selamlama sayilmak icin ust sinir. Uzun bir mesaj selamla baslasa bile
#: selamlama degildir: "Merhaba, su konuyu uzun uzun anlat..." gercek bir istek.
_SELAM_MAX_UZUNLUK = 60


def _is_greeting(message: str) -> bool:
    """Mesaj bir selamlama/nezaket ifadesi mi?

    Uzunluk siniri kasitli: kisa bir tur selamlamadir, uzun bir tur icinde
    selamlama GECER ama kendisi selamlama degildir.
    """
    metin = (message or "").strip()
    if not metin or len(metin) > _SELAM_MAX_UZUNLUK:
        return False
    fold = _fold_tr(metin)
    return any(keyword_present(fold, s) for s in _SELAMLAR)

TOOL_TRIGGERS = {
    "web_search": [
        # "öğren" BİLEREK çıkarıldı: 5 harflik bir fiil kökü ve "öğrenme
        # algoritması", "öğrencilerim" gibi masum cümlelerde eşleşiyordu.
        # Hiçbir sınır kuralı bunu ayıramaz — "öğrenme" morfolojik olarak
        # "hissesinde" ile aynı yapıda (kök + Türkçe ek), ve "hisse" kökünün
        # ek almış hâlinde eşleşmesini İSTİYORUZ. Ayrım kelime listesinde.
        "araştır", "haber", "güncel", "son dakika",
        "search", "latest", "news", "find out", "look up",
        "ne oldu", "durum nedir", "bilgi ver",
    ],
    "deep_research": [
        "derinlemesine araştır", "kapsamlı araştır", "detaylı araştır",
        "hakkında her şey", "tam araştırma",
    ],
    "calculate": [
        "hesapla", "calculate", "sqrt(", "sin(", "cos(", "log(",
        "kaç eder", "kaçtır",
    ],
    "get_datetime": [
        "saat kaç", "tarih nedir", "bugün ne", "hangi gün",
        "şu an saat", "günün tarihi",
    ],
    "get_notes": [
        "notlarım", "notları göster", "notlarımı", "kayıtlarım",
    ],
    "save_note": [
        "not et:", "not al:", "şunu kaydet:", "bunu hatırla:",
        "hatırlat:", "not olarak kaydet",
    ],
}

# ─── Yerel ajana özgü ek yönergeler ─────────────────────
# Kimlik, sadakat, kişilik, üslup ve uydurma yasağı `agents/persona.py`'den
# gelir (SSOT). Burada YALNIZ bu ajana özgü olan kalır: araç çıktısı kuralları
# ve proje durumu için zemin kuralı.
#
# Proje durumunun KENDİSİ burada yazmaz. Sabit yazılan durum eskir ve model
# eskimiş durumu güvenle tekrar eder — canlı testte tam bu oldu. Olgular
# yalnız `_load_project_context()` üzerinden, canlı dosyalardan gelir.
LOCAL_AGENT_ADDENDUM = """## ARAÇ ÇIKTISI
- Araç adlarını, sistem mesajlarını veya teknik ayrıntıları yanıtta gösterme.
- Araçtan gelen bilgiyi özümse, kendi cümlelerinle anlat.
- Kaynak bağlantısını yalnız gerektiğinde ve kısaca ver.

## PROJE DURUMU
- Proje durumu, commit geçmişi ve canlı sistem hakkında kendiliğinden bilgin
  YOKTUR. Aşağıda "GUNCEL PROJE DURUMU" bloğu verilmişse yalnız oradakini söyle.
- Blok verilmemişse "anlık proje durumuna erişimim yok" de; tahmin yürütme.
- Bir konu blokta geçmiyorsa onun hakkında çıkarım yapma — bilmiyorsun.
- Tarih ve saat için get_datetime aracını kullan; uydurma.

## TÜRKÇE YAZIM
- Yalnız Türkçe konuş. "okay", "voila", "peut-être" gibi yabancı kelimeler yasak.
- Yazım hatası yapma; emin değilsen daha basit kelimeyi seç.
- "Hoş bulduk" konuğun sözüdür, ev sahibinin değil — sen kullanırsan yanlış olur.
"""


def _clean_response(text: str) -> str:
    """Yanıttan teknik/sistem kalıntılarını temizle."""
    noise_patterns = [
        r'\[Araç:.*?\]',
        r'\[Aşağıdaki.*?\]',
        r'\[.*?sonucu\]',
        r'Yukarıdaki bilgilere dayanarak.*?yanıt ver[.\s]*',
        r'kullanıcıya doğal.*?yanıt ver[.\s]*',
        r'\[.*?güncel bilgileri.*?\]',
        r'Polimer endüstrisindeki son gelişmeleri araştır\s*',
    ]
    for p in noise_patterns:
        text = re.sub(p, '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class LocalJarvisAgent:

    def __init__(self):
        self.history: list[dict] = []
        self.turn_count = 0
        self.tool_calls_total = 0
        self.ollama_available = False
        self.available_models: list[str] = []
        self._ollama = None
        self._registry = ModelRegistry()
        self._project_ctx = self._load_project_context()
        self.memory = self._load_memory()
        self._tools = self._load_tools()
        self._init_ollama()
        # Hafıza sistemi
        from memory.memory_manager import JarvisMemory
        self.memory = JarvisMemory()

    def _load_tools(self) -> dict:
        try:
            # `run_python_code` BILEREK yuklenmiyor. `tools/tools.py:482`
            # icinde `exec()` var ve SkillSpector bunu HIGH isaretledi; ama
            # asil sorun erisilebilirlik degil, ERISILEMEZLIK: `_detect_tool()`
            # yalnizca TOOL_TRIGGERS'ta karsiligi olan araclara yol aciyor,
            # bu arac hicbirine bagli degil. Yani yuklu olmasi deger uretmeden
            # risk tasiyordu. `tools/tools.py` DEGISTIRILMEDI (CLAUDE.md 3).
            from tools.tools import (
                web_search, deep_research, calculate, get_datetime,
                get_notes, save_note, analyze_file,
            )
            tools = {
                "web_search":      web_search,
                "deep_research":   deep_research,
                "calculate":       calculate,
                "get_datetime":    get_datetime,
                "get_notes":       get_notes,
                "save_note":       save_note,
                "analyze_file":    analyze_file,
            }
            console.print(f"[green]✓ Araçlar yüklendi ({len(tools)} araç)[/]")
            return tools
        except Exception as e:
            console.print(f"[yellow]⚠ Araç hatası: {e}[/]")
            return {}

    def _load_project_context(self, root: Path | None = None) -> str:
        """Modele verilecek **canlı** proje durumu bloğunu kurar.

        Olgular burada YAZILMAZ, okunur. Durum daha önce koda sabit
        yazılmıştı ve üç satırı eskimişti (E1-S4 "BEKLIYOR" iken
        `roadmap_state.json`'da DONE); model bu tabloyu her turda görüp
        "tasarım aşamasındayız" diyordu. Kaynak artık `roadmap_state.json` —
        dosya kendini "TEK DOĞRULUK KAYNAGI" ilan ediyor.

        Fail-safe korunur: bir kaynak okunamazsa o bölüm **atlanır**;
        uydurma durum yerine hiç durum yeğdir.

        ``root`` yalnız test içindir; üretimde depo kökü kullanılır.
        """
        root = Path(root) if root is not None else Path(__file__).parent.parent
        lines: list[str] = ["## GUNCEL PROJE DURUMU"]

        # 1. Git log (safe read-only subprocess)
        try:
            import subprocess
            result = subprocess.run(
                ["git", "log", "-5", "--oneline"],
                capture_output=True, text=True, timeout=5,
                cwd=str(root),
            )
            if result.returncode == 0 and result.stdout.strip():
                lines.append("\n### Son Commitler")
                for log_line in result.stdout.strip().splitlines():
                    lines.append(f"  {log_line}")
        except Exception:
            pass

        # 2. Human-needed pending items
        human_path = root / "automation" / "HUMAN_NEEDED.md"
        try:
            human_text = human_path.read_text(encoding="utf-8")
            # Sablon yer tutucusu ("- [ ] [YYYY-MM-DD] [TASK-ID] ...") gercek
            # bir bekleyen is DEGILDIR; modele oyle sunulursa uydurma bir
            # gorev olarak konusur. Dosyadaki ornek satir elenir.
            pending = [
                ln.strip() for ln in human_text.splitlines()
                if ln.strip().startswith("- [ ]")
                and "YYYY-MM-DD" not in ln and "TASK-ID" not in ln
            ]
            if pending:
                lines.append("\n### Insan Onayi Gereken Isler (HUMAN_NEEDED)")
                lines.extend(f"  {p}" for p in pending)
        except Exception:
            pass

        # 3. Yol haritasi durumu — TEK DOGRULUK KAYNAGI: roadmap_state.json.
        #    Sabit metin yok; dosya degisince blok degisir.
        try:
            import json as _json
            veri = _json.loads(
                (root / "roadmap_state.json").read_text(encoding="utf-8")
            )
            adimlar = veri.get("steps") or []
            if adimlar:
                biten = sum(1 for a in adimlar if a.get("status") == "done")
                lines.append("\n### Yol Haritasi Durumu")
                lines.append(f"  Tamamlanan adim: {biten}/{len(adimlar)}")
                for adim in adimlar:
                    if adim.get("status") == "done":
                        continue
                    lines.append(
                        f"  - {adim.get('id')} [{adim.get('status')}] "
                        f"{adim.get('title', '')}"
                    )
                    kanit = adim.get("evidence")
                    if isinstance(kanit, dict):
                        for ad, k in kanit.items():
                            if isinstance(k, dict) and k.get("verdict"):
                                tarih = k.get("date") or k.get("ts") or ""
                                lines.append(
                                    f"      {ad}: {k['verdict']}"
                                    + (f" ({tarih})" if tarih else "")
                                )
        except Exception:
            # Dosya yok/bozuk: durum bolumu ATLANIR. Uydurma durum yerine
            # hic durum yegdir.
            pass

        # 4. Ortamdan CANLI okunan durum (sabit iddia degil).
        import os as _os
        if _os.getenv("JARVIS_PROACTIVE_ENABLED", "0").strip() not in ("1", "true", "True"):
            lines.append("\n### Calisma Modu")
            lines.append("  - Proaktif bildirimler: CANLI DEGIL (JARVIS_PROACTIVE_ENABLED=0)")

        # 4. Optional: T1-S2 fail log summary if present
        fail_log = root / "automation" / "T1_S2_FAIL_LOG.md"
        try:
            fail_text = fail_log.read_text(encoding="utf-8")
            verdict_lines = [
                ln.strip() for ln in fail_text.splitlines()
                if "FAIL" in ln or "Verdict" in ln or "PASS" in ln
            ]
            if verdict_lines:
                lines.append("\n### T1-S2 Son Sonuc")
                lines.extend(f"  {v}" for v in verdict_lines[:3])
        except Exception:
            pass

        lines.append("\n### Onemli Kural")
        lines.append("  Bu blogun disindaki proje durumu, commit veya canli sistem")
        lines.append("  bilgilerini UYDURMA. Bilmiyorsan soyle.")

        return "\n".join(lines)

    def _load_memory(self):
        try:
            from agent.local_agent_memory import LocalMemory
            return LocalMemory()
        except Exception:
            return None

    def _init_ollama(self):
        try:
            import ollama as ol
            self._ollama = ol
            models_resp = ol.list()

            # ✅ FIX: Yeni ve eski Ollama versiyonu uyumlu
            self.available_models = []
            raw_models = getattr(models_resp, 'models', None)
            if raw_models is None:
                raw_models = models_resp.get('models', []) if isinstance(models_resp, dict) else []

            for m in raw_models:
                if isinstance(m, dict):
                    name = m.get('model') or m.get('name', '')
                else:
                    name = getattr(m, 'model', '') or getattr(m, 'name', '')
                if name:
                    self.available_models.append(name)

            if not self.available_models:
                console.print("[yellow]⚠ Model yok![/]")
                return
            self.ollama_available = True
            console.print(
                f"[green]✓ Ollama bağlı[/] | [cyan]{len(self.available_models)} model[/]: "
                f"{', '.join(self.available_models[:3])}"
            )
        except ImportError:
            console.print("[red]✗ pip install ollama[/]")
        except Exception as e:
            console.print(f"[red]✗ Ollama: {e}[/]")

    def _classify(self, message: str) -> str:
        """Turu siniflandirir: fast / mid / deep.

        Ayni karar hem modeli (rol uzerinden) hem persona seviyesini secer;
        boylece "kisa soru" esigi iki yerde ayri ayri tutulmaz.
        """
        # Duz .lower() KULLANILMAZ: "İ".lower() combining dot uretir ve
        # eslesme sessizce kacar (CLAUDE.md 6). Fold her iki tarafa da uygulanir.
        fold = _fold_tr(message)
        deep_kw = ("derinlemesine", "kapsamli", "analiz et", "detayli", "rapor hazirla")
        # Selamin disinda kalan kisa-tur isaretleri.
        fast_kw = ("saat kac", "gorusuruz", "tarih nedir")

        # Uzunluk once bakilir: uzun mesaj selamla baslasa bile kisa tur degil.
        if len(message) > 300 or any(keyword_present(fold, k) for k in deep_kw):
            return "deep"
        if _is_greeting(message) or any(keyword_present(fold, k) for k in fast_kw):
            return "fast"
        return "mid"

    def _model_for_tier(self, tier: str) -> str:
        """Turu aktif profildeki bir role cozer.

        Model adi burada yazili DEGILDIR (CLAUDE.md 7: "Model adi koda
        gomulmez -> ModelRegistry"). Profil degisince kod degismez.
        """
        small = self._registry.local_small()
        main = self._registry.local_main()
        adaylar = {
            "fast": [small, main],
            "mid": [main, small],
            "deep": [self._registry.research_model(), main, small],
        }.get(tier, [main, small])

        for aday in adaylar:
            for kurulu in self.available_models:
                if aday.lower().split(":")[0] in kurulu.lower():
                    return kurulu
        return self.available_models[0] if self.available_models else main

    def _detect_tool(self, message: str) -> Optional[tuple[str, dict]]:
        # Selamlama hicbir arac tetiklemez. Bu kontrol EN BASTA durur:
        # "Ne haber Jarvis?" canli testte web aramasi baslatiyordu.
        if _is_greeting(message):
            return None

        # Duz .lower() yerine fold: "İ" tuzagi (CLAUDE.md 6) ve kisa koklerde
        # kelime siniri, `keyword_present` icinde tek kaynaktan gelir.
        msg = _fold_tr(message)

        def _eslesir(grup: str) -> bool:
            return any(keyword_present(msg, t) for t in TOOL_TRIGGERS[grup])

        if _eslesir("deep_research"):
            return "deep_research", {"topic": message.strip(), "depth": 2}

        if _eslesir("get_datetime"):
            return "get_datetime", {}

        if _eslesir("get_notes"):
            return "get_notes", {"filter_by": "", "show_done": False}

        if _eslesir("save_note"):
            content = message
            for kw in ["not et:", "not al:", "kaydet:", "hatırlat:"]:
                if kw in message.lower():
                    idx = message.lower().index(kw) + len(kw)
                    content = message[idx:].strip()
                    break
            return "save_note", {"content": content, "category": "genel"}

        if _eslesir("calculate"):
            expr = message.replace("hesapla", "").replace("calculate", "").strip()
            return "calculate", {"expression": expr}

        if _eslesir("web_search"):
            query = message
            for kw in ["araştır", "ara ", "haber", "güncel bilgi ver", "öğren", "ne oldu"]:
                query = query.replace(kw, "").strip()
            if len(query) < 3:
                query = message
            return "web_search", {"query": query, "max_results": 5}

        return None

    def _run_tool(self, tool_name: str, args: dict) -> str:
        fn = self._tools.get(tool_name)
        if not fn:
            return ""
        try:
            console.print(f"[dim]🔧 {tool_name}...[/]")
            result = str(fn(**args))
            self.tool_calls_total += 1
            if len(result) > 3500:
                result = result[:3500]
            return result
        except Exception:
            return ""

    def _ask_ollama(self, messages: list[dict], model: str) -> str:
        try:
            response = self._ollama.chat(
                model=model,
                messages=messages,
                stream=False,
                options={
                    "temperature": 0.72,
                    "num_ctx": 4096,
                    "num_predict": 1024,
                    "stop": ["[Araç", "[System", "USER:", "JARVIS:"],
                }
            )
            return response.message.content
        except Exception as e:
            return f"Model hatası: {e}"

    def chat(self, user_message: str) -> str:
        if not self.ollama_available:
            return "⚠️ Ollama bağlı değil."
        # PDF/döküman algılama — JARVIS kendisi bulur ve yükler
        mesaj_lower = user_message.lower()
        pdf_keywords = ["pdf", "dosya", "döküman", "makale", "yükle",
                        "oku", "analiz", "incele", "bak", "indir"]
        if any(k in mesaj_lower for k in pdf_keywords):
            from tools.tools import find_and_load_pdf
            from rag.rag_engine import JarvisRAG
            yukle = find_and_load_pdf()
            rag = JarvisRAG()
            # PDF'i RAG'a yükle (kritik!)
            rag.add_documents()
            # Soruyu sor
            cevap = rag.query_with_ollama(user_message)
            return f"{yukle}\n\n{cevap}"
        self.turn_count += 1
        tier = self._classify(user_message)
        model = self._model_for_tier(tier)
        console.print(f"[dim]→ {model.split(':')[0]} | Tur {self.turn_count}[/]")

        # Araç çalıştır
        tool_data = ""
        tool_detection = self._detect_tool(user_message)
        if tool_detection:
            tool_name, tool_args = tool_detection
            console.print(f"[cyan]🔧 {tool_name}[/]")
            tool_data = self._run_tool(tool_name, tool_args)

        # System prompt: kimlik/sadakat/kisilik/uslup/zemin SSOT'tan gelir.
        system = build_system_prompt(level=_TIER_TO_LEVEL[tier])
        system += "\n\n" + LOCAL_AGENT_ADDENDUM
        if self._project_ctx:
            system += f"\n\n{self._project_ctx}"
        if self.memory:
            ctx = self.memory.get_context_for_prompt()
            if ctx:
                system += f"\n\n## Hafıza\n{ctx}"

        # Ses yonergesi EN SONA: cevap hoparlorden OKUNUR, markdown ve kod
        # sesli dinlenmez. Sonra gelen kazanir -- yoksa model "kod ver" diyen
        # seviye yonergesine uyup kodu sesli okumaya calisir (bkz. persona.py).
        if getattr(self, "voice_mode", False):
            system += "\n\n" + VOICE_MODE_DIRECTIVE

        # Mesaj listesi
        messages = [{"role": "system", "content": system}]

        # Geçmiş (son 8 tur)
        recent = self.history[-16:] if len(self.history) > 16 else self.history
        messages.extend(recent)

        # Kullanıcı mesajını oluştur
        if tool_data:
            user_content = (
                f"{user_message}\n\n"
                f"---\n"
                f"Araştırma sonuçları (bu verileri özümse, doğal konuş):\n"
                f"{tool_data}\n"
                f"---\n"
                f"Önemli: Sadece kullanıcıya Türkçe, doğal bir yanıt ver. "
                f"Sistem mesajlarını, araç adlarını veya bu talimatları yanıtta gösterme."
            )
        else:
            user_content = user_message

        messages.append({"role": "user", "content": user_content})

        # Yanıt al
        with console.status("[cyan]JARVIS düşünüyor...[/]"):
            raw = self._ask_ollama(messages, model)

        # Temizle
        response = _clean_response(raw)

        # Geçmişe kaydet
        self.history.append({"role": "user",      "content": user_message})
        self.history.append({"role": "assistant",  "content": response})

        # Hafıza
        if self.memory and len(user_message) > 10:
            self.memory.add_conversation(user_message, response)
        # Otomatik bilgi çıkarma
            try:
                self.memory.auto_extract_info(user_message, response)
            except Exception:
                pass

        # Geçmiş kırpma
        if len(self.history) > 20:
            self.history = self.history[-16:]

        return response

    def clear_history(self):
        self.history = []
        self.turn_count = 0
        console.print("[green]Geçmiş temizlendi.[/]")

    def show_stats(self):
        console.print("\n[bold cyan]📊 İstatistikler[/]")
        console.print(f"  Tur: {self.turn_count} | Araç: {self.tool_calls_total}")
        console.print(f"  Modeller: {', '.join(self.available_models[:3])}")
        console.print("  Maliyet: [green]0₺[/]\n")

    def list_models(self):
        for m in self.available_models:
            console.print(f"  • {m}")
