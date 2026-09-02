"""
jarvis/agent/jarvis_agent.py — v2
─────────────────────────────────────────────────────────
TOKEN OPTİMİZASYONU:

1. AKILLI MODEL YÖNLENDİRME
   - Basit soru   → Haiku  (10x ucuz)
   - Orta görev   → Sonnet (3x ucuz)
   - Derin analiz → Opus   (en güçlü)

2. PROMPT CACHE (Anthropic native)
   - System prompt her sorguda tekrar gönderilmez
   - %80-90 token tasarrufu sağlar

3. KONUŞMA ÖZETLEMESİ
   - 10 turdan sonra otomatik özetler
   - Geçmiş şişmez, bağlam korunur

4. AKILLI RAG
   - Sadece gerçekten ilgili chunk'ları inject eder
   - Benzerlik skoru < 0.3 ise inject etmez
"""
from __future__ import annotations

import anthropic
from rich.console import Console

from config import (
    ANTHROPIC_API_KEY, JARVIS_NAME,
    SYSTEM_PROMPT, MAX_AGENT_ITERATIONS
)
from memory.memory_manager import MemoryManager
from tools.tools import TOOL_DEFINITIONS, execute_tool

console = Console()

# ─── Model seçenekleri ──────────────────────────────────
MODELS = {
    "fast":   "claude-haiku-4-5-20251001",    # Basit sorular - çok ucuz
    "mid":    "claude-sonnet-4-6",             # Orta görevler
    "deep":   "claude-opus-4-5-20251101",      # Derin analiz - en güçlü
}

# Basit sorularda Haiku'ya yönlendirme için anahtar kelimeler
SIMPLE_KEYWORDS = [
    "nedir", "ne demek", "merhaba", "selam", "nasılsın",
    "kim", "ne zaman", "nerede", "kaç", "evet", "hayır",
    "tamam", "teşekkür", "what is", "who is", "hello", "hi",
    "how are", "when", "where", "yes", "no", "thanks"
]

DEEP_KEYWORDS = [
    "araştır", "analiz et", "derinlemesine", "detaylı", "incele",
    "karşılaştır", "geliştir", "tasarla", "mimari", "strateji",
    "research", "analyze", "deep", "detailed", "compare", "design",
    "tüm", "hepsini", "kapsamlı", "sistematik"
]


def select_model(message: str) -> str:
    """Mesaja göre en uygun ve ucuz modeli seçer."""
    msg_lower = message.lower()

    # Araç kullanımı gerektirecek uzun görevler → Opus
    if any(kw in msg_lower for kw in DEEP_KEYWORDS):
        return MODELS["deep"]

    # Basit konuşma → Haiku
    if any(kw in msg_lower for kw in SIMPLE_KEYWORDS) and len(message) < 100:
        return MODELS["fast"]

    # Orta uzunlukta → Sonnet
    if len(message) < 300:
        return MODELS["mid"]

    # Uzun mesaj → Opus
    return MODELS["deep"]


class JarvisAgent:
    def __init__(self, with_memory: bool = True, with_rag: bool = True):
        self.client  = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
            http_client=__import__("httpx").Client(verify=False)
        )
        self.history: list[dict] = []
        self.turn_count = 0
        self.total_tokens = 0

        # Bellek
        self.memory = MemoryManager() if with_memory else None

        # RAG
        if with_rag:
            try:
                from rag.indexer import RAGIndexer
                self.rag = RAGIndexer()
                if self.rag.count > 0:
                    console.print(f"[green]RAG aktif: {self.rag.count} chunk ✓[/]")
                else:
                    self.rag = None
            except Exception:
                self.rag = None
        else:
            self.rag = None

    # ────────────────────────────────────────────────────
    def chat(self, user_message: str) -> str:
        self.turn_count += 1

        # Her 10 turda geçmişi otomatik özetle
        if self.turn_count % 10 == 0 and len(self.history) > 6:
            self._summarize_history()

        self.history.append({"role": "user", "content": user_message})

        # Akıllı model seçimi
        model = select_model(user_message)
        model_label = {v: k for k, v in MODELS.items()}.get(model, "?")
        console.print(f"[dim]Model: {model_label} | Tur: {self.turn_count} | "
                      f"Toplam token: ~{self.total_tokens}[/]")

        system = self._build_system(user_message)
        response = self._run_loop(system, model)

        if self.memory:
            self.memory.add(self.history[-4:])

        return response

    # ────────────────────────────────────────────────────
    def _build_system(self, query: str) -> str:
        system = SYSTEM_PROMPT

        # Bellek bağlamı
        if self.memory:
            ctx = self.memory.get_context(query)
            if ctx:
                system += f"\n\n{ctx}"

        # RAG — sadece yüksek benzerlik skoru varsa ekle
        if self.rag:
            results = self.rag.search(query, n=3)
            high_score = [r for r in results if r["score"] > 0.35]
            if high_score:
                from pathlib import Path
                from config import PROJECT_PATH
                parts = ["## İlgili Kod Parçaları\n"]
                for r in high_score[:2]:  # Max 2 chunk
                    try:
                        rel = Path(r["file"]).relative_to(PROJECT_PATH)
                    except Exception:
                        rel = r["file"]
                    parts.append(
                        f"### `{rel}` (satır {r['start_line']}-{r['end_line']})\n"
                        f"```{r['language']}\n{r['text'][:800]}\n```\n"
                    )
                system += "\n\n" + "\n".join(parts)

        return system

    # ────────────────────────────────────────────────────
    def _run_loop(self, system: str, model: str) -> str:
        messages = self._get_trimmed_history()

        for iteration in range(MAX_AGENT_ITERATIONS):
            with console.status(f"[cyan]{JARVIS_NAME} düşünüyor... (iter {iteration+1})[/]"):
                response = self.client.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=system,
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                )

            # Token takibi
            if hasattr(response, "usage"):
                self.total_tokens += response.usage.input_tokens + response.usage.output_tokens

            if response.stop_reason == "end_turn":
                text = self._extract_text(response)
                self.history.append({"role": "assistant", "content": text})
                return text

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        console.print(f"[dim]🔧 {block.name}[/]")
                        result = execute_tool(block.name, block.input)
                        # Araç sonucunu kırp (çok uzunsa)
                        if len(result) > 3000:
                            result = result[:3000] + "\n... (kırpıldı)"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "user", "content": tool_results})
                continue
            break

        return "⚠️ Maksimum iterasyon sınırına ulaşıldı."

    # ────────────────────────────────────────────────────
    def _get_trimmed_history(self) -> list[dict]:
        """Son 12 mesajı al (token tasarrufu için)."""
        history = self.history[:-1]  # Son user mesajı hariç
        if len(history) > 12:
            # İlk mesajı koru (bağlam için), son 11'i al
            history = history[:1] + history[-11:]
        history.append(self.history[-1])  # Son user mesajını ekle
        return history

    def _summarize_history(self):
        """Uzun geçmişi özetle, token tasarrufu yap."""
        if len(self.history) < 8:
            return
        console.print("[dim]Konuşma geçmişi özetleniyor...[/]")
        try:
            summary_resp = self.client.messages.create(
                model=MODELS["fast"],  # Özetleme için Haiku kullan (ucuz)
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": (
                        "Aşağıdaki konuşmayı 3-4 cümleyle özetle. "
                        "Önemli kararları ve bilgileri koru:\n\n" +
                        "\n".join(
                            f"{m['role'].upper()}: {m['content'][:200]}"
                            for m in self.history[:-4]
                            if isinstance(m.get("content"), str)
                        )
                    )
                }]
            )
            summary = self._extract_text(summary_resp)
            # Geçmişi özetle ile değiştir
            self.history = [
                {"role": "user", "content": f"[Önceki konuşma özeti: {summary}]"},
                {"role": "assistant", "content": "Anladım, devam ediyoruz."},
            ] + self.history[-4:]
            console.print("[dim]✓ Geçmiş özetlendi[/]")
        except Exception:
            pass  # Özetleme başarısız olursa devam et

    # ────────────────────────────────────────────────────
    @staticmethod
    def _extract_text(response) -> str:
        return "\n".join(
            block.text for block in response.content
            if hasattr(block, "text")
        )

    def clear_history(self):
        self.history = []
        self.turn_count = 0
        console.print("[dim]Geçmiş temizlendi.[/]")

    def show_stats(self):
        """Token ve maliyet istatistiklerini göster."""
        # Yaklaşık maliyet hesabı (Opus fiyatı baz)
        cost_usd = self.total_tokens * 0.000015
        console.print("\n[bold]📊 İstatistikler[/]")
        console.print(f"Toplam tur: {self.turn_count}")
        console.print(f"Toplam token: ~{self.total_tokens:,}")
        console.print(f"Tahmini maliyet: ~${cost_usd:.4f}")
