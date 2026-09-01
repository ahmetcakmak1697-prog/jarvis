"""
Semantic Router - Soruları doğru motora yönlendirir
'Geçen hafta ne konuştuk' → memory
'PDF'te ne var' → rag
'Saat kaç' → tool
'B4C Ehull' → research
'Merhaba' → llm_fast
'Derinlemesine analiz et' → llm_deep
"""
from typing import Literal

Route = Literal["memory", "rag", "tool", "llm_fast", "llm_deep", "research"]


class SemanticRouter:
    MEMORY_KW = ["geçen", "dün", "önceki", "hatırlıyor", "konuşmuştuk",
                 "söylemiştim", "demiştik", "anlatmıştım", "hatırla", "demin"]

    RAG_KW = ["dokümanda", "pdf'te", "dosyada", "belgede", "raporda",
              "kitapta", "makalede", "yönetmelikte", "pdf'i", "metinde"]

    TOOL_KW = {
        "datetime": ["saat kaç", "tarih nedir", "bugün ne", "hangi gün"],
        "calc":     ["hesapla", "kaç eder", "sqrt(", "sin(", "cos("],
        "notes":    ["not et", "not al", "notlarım", "kaydet:", "hatırlat:"],
    }

    DEEP_KW = ["derinlemesine", "kapsamlı", "detaylı analiz", "karşılaştır",
               "mukayese", "sistematik incele"]

    RESEARCH_KW = ["araştır", "öğren", "ne oldu", "son haber", "güncel",
                   "bilgi ver", "kim", "nedir", "ne demek", "ne kadar",
                   "kaç", "nerede", "ne zaman"]

    def route(self, message: str) -> Route:
        m = message.lower().strip()

        if any(k in m for k in self.MEMORY_KW):
            return "memory"
        if any(k in m for k in self.RAG_KW):
            return "rag"
        for kws in self.TOOL_KW.values():
            if any(k in m for k in kws):
                return "tool"
        if any(k in m for k in self.DEEP_KW) or len(message) > 300:
            return "llm_deep"
        if any(k in m for k in self.RESEARCH_KW):
            return "research"
        return "llm_fast"

    def explain(self, message: str) -> dict:
        return {"route": self.route(message), "message": message[:80]}


if __name__ == "__main__":
    r = SemanticRouter()
    for t in ["Dün ne konuştuk?", "PDF'te ne yazıyor?", "Saat kaç?",
              "Türkiye nüfusu ne kadar?", "Kuantum mekaniği derinlemesine analiz et",
              "Merhaba nasılsın"]:
        print(r.explain(t))
