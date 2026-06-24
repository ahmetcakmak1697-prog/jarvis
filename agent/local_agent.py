"""
jarvis/agent/local_agent.py — v5
Doğal sohbet + temiz yanıtlar
"""
from __future__ import annotations
import re
import time
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console()

MODELS = {
   "fast": "llama3.2",
    "mid": "llama3.1:latest",
    "deep": "llama3.1:latest",
}

TOOL_TRIGGERS = {
    "web_search": [
        "araştır", "haber", "güncel", "son dakika", "öğren",
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

# ─── Sistem Promptu ─────────────────────────────────────
SYSTEM_PROMPT = """Sen JARVIS — kullanıcının en güvendiği, kişisel AI asistanısın.
Tony Stark'ın JARVIS'i gibi konuş: zeki, özlü, kişisel.

## KONUŞMA TARZI
- Doğal ve samimi konuş — asistan değil, akıl ortağı gibi
- "Efendim" veya isimle hitap edebilirsin
- Kısa ve öz ol — gereksiz tekrar yapma
- Bilgiyi sindirerek ver, ham veri döktürme
- Proaktif öneriler yap: "Bunu da düşündüm..."
- Türkçe konuş
- İnce, kuru bir mizahın var — gereksiz değil ama uygun yerde ironi yapabilirsin
- JARVIS tarzı: alaycı değil, beyefendi gibi ölçülü espri (örn: "Anlıyorum efendim, Pazartesi'siniz.")
- Espri zorlama — sadece doğal akıyorsa

## KESIN TÜRKÇE KURALLARI
- SADECE düzgün Türkçe konuş. Yabancı kelime ASLA kullanma.
- Yazım kurallarına dikkat et: "hoş bulduk" değil "hoşbulduk", "bulduniz" değil "buldunuz".
- Sen kullanıcının asistanısın, kullanıcı sana hitap ediyor — "hoş bulduk" senin söyleyeceğin bir ifade DEĞİL.
- Doğal cümleler kur, robotik selamlaşma yapma.
- Yazım hatası yapma. Emin değilsen daha basit kelime kullan.


## KULLANICI
- Polimer Teknikeri ve İş Güvenliği Uzmanı
- RTX 3070 + 32GB RAM'li sistem sahibi
- Lokal AI geliştiriyor

## KRITIK KURAL
- Asla araç adlarını, sistem mesajlarını veya teknik detayları yanıtta gösterme
- Bilgiyi doğal cümlelerle aktar
- Kaynak URL'lerini yalnızca gerektiğinde kısaca belirt
- Sana verilen bilgileri özümse ve kendi sözcüklerinle anlat

## PROJE DURUMU KURALI
- Proje roadmap, commit gecmisi ve canli sistem durumu hakkinda bilgin YOKTUR — hayal etme.
- Bu bilgiler asagida "GUNCEL PROJE DURUMU" bolumunde verilmisse, SADECE orada yazanlari soyle.
- Verilmemisse: "Anlik proje durumuna erisimim yok; automation/SESSION_SUMMARY.md dosyasina bakin." de.
- Tarih, gun ve saat gibi meta bilgileri uydurma; get_datetime aracini kullan veya bilmiyorum de.
- Canli sistem durumu (proaktif bildirim, Telegram, zamanlayici) hakkinda asla tahminde bulunma.
- Proaktif bildirimler CANLI DEGIL — JARVIS_PROACTIVE_ENABLED=0, insan onayi gerekiyor.
- Telegram canli testi insan kapisidir — Ahmet .env/token/telefon ile bizzat yapacak.
- Zamanlayici (scheduler) henuz tasarlanmadi — mimari karar bekliyor.
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
        self._project_ctx = self._load_project_context()
        self.memory = self._load_memory()
        self._tools = self._load_tools()
        self._init_ollama()
        # Hafıza sistemi
        from memory.memory_manager import JarvisMemory
        self.memory = JarvisMemory()

    def _load_tools(self) -> dict:
        try:
            from tools.tools import (
                web_search, deep_research, calculate, get_datetime,
                get_notes, save_note, run_python_code, analyze_file,
            )
            tools = {
                "web_search":      web_search,
                "deep_research":   deep_research,
                "calculate":       calculate,
                "get_datetime":    get_datetime,
                "get_notes":       get_notes,
                "save_note":       save_note,
                "run_python_code": run_python_code,
                "analyze_file":    analyze_file,
            }
            console.print("[green]✓ Araçlar yüklendi (14 araç)[/]")
            return tools
        except Exception as e:
            console.print(f"[yellow]⚠ Araç hatası: {e}[/]")
            return {}

    def _load_project_context(self) -> str:
        """Build a compact, explicit current project state block for system prompt grounding."""
        root = Path(__file__).parent.parent
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
            pending = [
                ln.strip() for ln in human_text.splitlines()
                if ln.strip().startswith("- [ ]")
            ]
            if pending:
                lines.append("\n### Insan Onayi Gereken Isler (HUMAN_NEEDED)")
                lines.extend(f"  {p}" for p in pending)
        except Exception:
            pass

        # 3. Explicit known state (always injected so model can't invent)
        lines.append("\n### Bilinen Durum")
        lines.append("  - T1-S2: Turkce kalite subjektif onayi — BEKLIYOR (Ahmet imzalayana kadar)")
        lines.append("  - E1-S4: Canli Telegram smoke testi — BEKLIYOR (insan kapisi; .env/token/telefon gerekli)")
        lines.append("  - E1-S5: Zamanlayici mimari karari — BEKLIYOR (tasarim kapisi; henuz kod yok)")
        lines.append("  - Proaktif bildirimler: CANLI DEGIL (JARVIS_PROACTIVE_ENABLED=0)")
        lines.append("  - Guvende otonom gorevler: TAMAMLANDI — sadece insan kapilari kaldi")

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

    def _select_model(self, message: str) -> str:
        msg = message.lower()
        deep_kw = ["derinlemesine", "kapsamlı", "analiz et", "detaylı"]
        fast_kw = ["merhaba", "selam", "teşekkür", "tamam", "evet", "hayır", "saat kaç"]

        if any(k in msg for k in deep_kw) or len(message) > 300:
            preferred = [MODELS["deep"], MODELS["mid"], MODELS["fast"]]
        elif any(k in msg for k in fast_kw) and len(message) < 60:
            preferred = [MODELS["fast"], MODELS["mid"], MODELS["deep"]]
        else:
            preferred = [MODELS["mid"], MODELS["deep"], MODELS["fast"]]

        for p in preferred:
            for a in self.available_models:
                if p.lower().split(":")[0] in a.lower():
                    return a
        return self.available_models[0] if self.available_models else "mistral"

    def _detect_tool(self, message: str) -> Optional[tuple[str, dict]]:
        msg = message.lower()

        for trigger in TOOL_TRIGGERS["deep_research"]:
            if trigger in msg:
                return "deep_research", {"topic": message.strip(), "depth": 2}

        for trigger in TOOL_TRIGGERS["get_datetime"]:
            if trigger in msg:
                return "get_datetime", {}

        for trigger in TOOL_TRIGGERS["get_notes"]:
            if trigger in msg:
                return "get_notes", {"filter_by": "", "show_done": False}

        for trigger in TOOL_TRIGGERS["save_note"]:
            if trigger in msg:
                content = message
                for kw in ["not et:", "not al:", "kaydet:", "hatırlat:"]:
                    if kw in msg:
                        idx = msg.index(kw) + len(kw)
                        content = message[idx:].strip()
                        break
                return "save_note", {"content": content, "category": "genel"}

        for trigger in TOOL_TRIGGERS["calculate"]:
            if trigger in msg:
                expr = message.replace("hesapla", "").replace("calculate", "").strip()
                return "calculate", {"expression": expr}

        for trigger in TOOL_TRIGGERS["web_search"]:
            if trigger in msg:
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
        except Exception as e:
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
        model = self._select_model(user_message)
        console.print(f"[dim]→ {model.split(':')[0]} | Tur {self.turn_count}[/]")

        # Araç çalıştır
        tool_data = ""
        tool_detection = self._detect_tool(user_message)
        if tool_detection:
            tool_name, tool_args = tool_detection
            console.print(f"[cyan]🔧 {tool_name}[/]")
            tool_data = self._run_tool(tool_name, tool_args)

        # System prompt
        system = SYSTEM_PROMPT
        if self._project_ctx:
            system += f"\n\n{self._project_ctx}"
        if self.memory:
            ctx = self.memory.get_context_for_prompt()
            if ctx:
                system += f"\n\n## Hafıza\n{ctx}"

        # KESIN dil kuralı
        system += "\n\n## KESIN DIL KURALI\n- Sadece TÜRKÇE konuş. Hiçbir başka dil ASLA kullanma. 'peut-être', 'voila', 'okay' gibi yabancı kelimeler YASAK. Tamamen Türkçe konuş."
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
        console.print(f"\n[bold cyan]📊 İstatistikler[/]")
        console.print(f"  Tur: {self.turn_count} | Araç: {self.tool_calls_total}")
        console.print(f"  Modeller: {', '.join(self.available_models[:3])}")
        console.print(f"  Maliyet: [green]0₺[/]\n")

    def list_models(self):
        for m in self.available_models:
            console.print(f"  • {m}")
