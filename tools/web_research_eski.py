"""
JARVIS Web Researcher v2 — Çok kaynaklı bilgi toplama
Wikipedia (TR → EN) → DuckDuckGo Instant → DuckDuckGo Search
"""
import requests
from urllib.parse import quote
from pathlib import Path
import json


class WebResearcher:
    def __init__(self):
        self.cache_path = Path("memory/research_cache.json")
        self.cache = self._load_cache()

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cache(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def research_and_learn(self, query: str) -> str:
        """Bir konuyu araştır, en iyi sonucu döndür"""
        query = query.strip()
        if not query:
            return ""

        # Cache kontrolü
        if query.lower() in self.cache:
            return self.cache[query.lower()]

        # 1) Türkçe Wikipedia
        result = self._wiki_search(query, lang="tr")
        if result:
            self.cache[query.lower()] = result
            self._save_cache()
            return result

        # 2) İngilizce Wikipedia
        result = self._wiki_search(query, lang="en")
        if result:
            self.cache[query.lower()] = result
            self._save_cache()
            return result

        # 3) DuckDuckGo Instant Answer
        result = self._ddg_instant(query)
        if result:
            self.cache[query.lower()] = result
            self._save_cache()
            return result

        # 4) DuckDuckGo Search
        result = self._ddg_search(query)
        if result:
            self.cache[query.lower()] = result
            self._save_cache()
            return result

        return ""   # Bulunamadı

    # ─────────────────────────────────────────────
    # KAYNAKLAR
    # ─────────────────────────────────────────────

    def _wiki_search(self, query: str, lang: str = "tr") -> str:
        """Wikipedia REST API"""
        try:
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(query)}"
            r = requests.get(
                url, timeout=10,
                headers={"User-Agent": "JARVIS/1.0"}
            )
            if r.status_code == 200:
                data = r.json()
                extract = data.get("extract", "").strip()
                if len(extract) > 50:
                    title = data.get("title", query)
                    return f"[Wikipedia-{lang.upper()}] {title}: {extract}"
        except:
            pass

        # Search API fallback
        try:
            url = f"https://{lang}.wikipedia.org/w/api.php"
            params = {
                "action": "query", "list": "search",
                "srsearch": query, "format": "json",
                "srlimit": 1
            }
            r = requests.get(url, params=params, timeout=10,
                             headers={"User-Agent": "JARVIS/1.0"})
            data = r.json()
            results = data.get("query", {}).get("search", [])
            if results:
                first_title = results[0]["title"]
                return self._wiki_search(first_title, lang)
        except:
            pass

        return ""

    def _ddg_instant(self, query: str) -> str:
        """DuckDuckGo Instant Answer API"""
        try:
            url = "https://api.duckduckgo.com/"
            params = {"q": query, "format": "json", "no_html": "1"}
            r = requests.get(url, params=params, timeout=10)
            data = r.json()

            abstract = data.get("AbstractText", "").strip()
            if abstract and len(abstract) > 30:
                source = data.get("AbstractSource", "DuckDuckGo")
                return f"[{source}] {abstract}"

            # Definition fallback
            definition = data.get("Definition", "").strip()
            if definition and len(definition) > 30:
                return f"[Definition] {definition}"

            # Related topics fallback
            related = data.get("RelatedTopics", [])
            if related and isinstance(related[0], dict):
                text = related[0].get("Text", "").strip()
                if text and len(text) > 30:
                    return f"[DDG] {text}"
        except:
            pass
        return ""

    def _ddg_search(self, query: str) -> str:
        """DuckDuckGo full search (3 sonuç birleşik)"""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3, region="tr-tr"))
                if results:
                    parts = []
                    for r in results[:3]:
                        title = r.get("title", "")
                        body = r.get("body", "")
                        if body:
                            parts.append(f"- {title}: {body}")
                    if parts:
                        return "[Web]\n" + "\n".join(parts)
        except Exception as e:
            print(f"DDG hata: {e}")
        return ""


if __name__ == "__main__":
    # Test
    r = WebResearcher()
    print("="*60)
    print("Test 1: Grafen")
    print("="*60)
    print(r.research_and_learn("grafen"))
    print()
    print("="*60)
    print("Test 2: B4C")
    print("="*60)
    print(r.research_and_learn("bor karbür"))
