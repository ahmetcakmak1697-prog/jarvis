import os
import json
import re
from overrides import final
import requests
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import wikipedia
from ddgs import DDGS

try:
    from tavily import TavilyClient
except Exception:
    TavilyClient = None

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None


class WebResearcher:
    def __init__(self):
        self.tavily_key = os.getenv("TAVILY_API_KEY", "")
        self.tavily = TavilyClient(api_key=self.tavily_key) if self.tavily_key and TavilyClient else None

        self.cache_path = Path("memory/research_cache.json")
        self.credit_path = Path("memory/search_credits.json")

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36"
            )
        }

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.credit_path.parent.mkdir(parents=True, exist_ok=True)

        self.cache = self._load_json(self.cache_path)
        self._init_credits()

        try:
            wikipedia.set_lang("tr")
        except Exception:
            pass

    def _load_json(self, path):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        self.cache_path.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _init_credits(self):
        if not self.credit_path.exists():
            data = {
                "remaining": 1000,
                "reset_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            }
            self.credit_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def get_credit_status(self):
        data = self._load_json(self.credit_path)

        if "remaining" not in data:
            data["remaining"] = 1000

        if "reset_date" not in data:
            data["reset_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        try:
            reset_dt = datetime.strptime(data["reset_date"], "%Y-%m-%d")
            days_left = (reset_dt - datetime.now()).days
        except Exception:
            days_left = 0

        return f"[KREDİ: {data['remaining']}/1000 | YENİLENME: {max(0, days_left)} GÜN]"

    def _use_credit(self):
        data = self._load_json(self.credit_path)

        if "remaining" not in data:
            data["remaining"] = 1000

        if data["remaining"] > 0:
            data["remaining"] -= 1

        self.credit_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _normalize_query(self, query: str) -> str:
        q = query.strip()

        remove_phrases = [
            "internetten bak",
            "webden bak",
            "google'dan bak",
            "google dan bak",
            "araştır",
            "bana anlat",
            "özetle",
            "efendim",
        ]

        q_low = q.lower()
        for phrase in remove_phrases:
            q_low = q_low.replace(phrase, "")

        q_low = re.sub(r"\s+", " ", q_low).strip()
        return q_low or q
    
    def _expand_queries(self, query: str) -> list[str]:
        """
        Türkçe sorguyu daha kaliteli web sonuçları için birkaç farklı sorguya genişletir.
        """
        q = query.strip()
        q_lower = q.lower()

        queries = [q]

        ai_terms = ["yapay zeka", "ai", "artificial intelligence", "openai", "llm", "model"]
        current_terms = ["bugün", "güncel", "son durum", "haber", "bu hafta", "bu ay", "2025", "2026"]

        is_ai_query = any(t in q_lower for t in ai_terms)
        is_current = any(t in q_lower for t in current_terms)

        if is_ai_query and is_current:
            queries.extend([
                "latest artificial intelligence news OpenAI Anthropic Google DeepMind Nvidia 2026",
                "latest AI model releases research OpenAI Anthropic Google DeepMind Nvidia 2026",
                "AI news 2026 OpenAI Anthropic Google DeepMind Nvidia Reuters AP TechCrunch The Verge",
            ])

        elif is_ai_query:
            queries.extend([
                "artificial intelligence latest developments OpenAI Anthropic Google DeepMind Nvidia",
                "AI research model releases OpenAI Anthropic Google DeepMind Nvidia",
            ])

        return list(dict.fromkeys(queries))
    
    def _domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            return ""

    def _is_bad_result(self, title: str, body: str, url: str) -> bool:
        text = f"{title} {body} {url}".lower()
        domain = self._domain(url)

        bad_domains = [
            "pinterest.",
            "facebook.",
            "instagram.",
            "tiktok.",
            "quora.",
            "reddit.",
            "medium.com",
            "eksisozluk",
            "sozluk",
            "youtube.com",
            "hotspotshield",
            "vpn",
            "dictionary",
            "shiftdelete.net",
            "ogusto.com",
            "karar.com",
            "abcgazetesi.com.tr",
            "trhaber.com",
            "webtekno.com",
            "tamindir.com",
            "donanimhaber.com",
        ]

        if any(b in domain for b in bad_domains):
            return True

        bad_phrases = [
            "casino",
            "bahis",
            "kupon",
            "torrent",
            "apk",
            "crack",
            "adult",
            "escort",
            "vpn",
            "bedava indir",
            "full indir",
        ]

        if any(p in text for p in bad_phrases):
            return True

        # Çok zayıf snippet
        if len(body.strip()) < 40:
            return True

        return False

    def _score_result(self, query: str, title: str, body: str, url: str) -> int:
        q_words = set(re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{3,}", query.lower()))
        text = f"{title} {body}".lower()
        domain = self._domain(url)

        score = 0

        # Sorgu kelimeleri başlık/metin içinde geçiyorsa puan ver
        for w in q_words:
            if w in text:
                score += 2
            if w in title.lower():
                score += 4

        # Yüksek güvenilir AI / teknoloji / haber kaynakları
        top_sources = [
            "openai.com",
            "deepmind.google",
            "googleblog.com",
            "anthropic.com",
            "mistral.ai",
            "meta.com",
            "ai.meta.com",
            "nvidia.com",
            "microsoft.com",
            "ibm.com",
            "huggingface.co",
            "arxiv.org",
            "nature.com",
            "science.org",
            "mit.edu",
            "stanford.edu",
            "technologyreview.com",
            "reuters.com",
            "apnews.com",
            "techcrunch.com",
            "theverge.com",
            "wired.com",
            "venturebeat.com",
        ]

        if any(d in domain for d in top_sources):
            score += 12

        # Türkiye haber kaynakları orta güvenilir, ama kategori sayfasıysa düşecek
        tr_news_sources = [
            "aa.com.tr",
            "trthaber.com",
            "haberturk.com",
            "hurriyet.com.tr",
            "cnnturk.com",
            "ntv.com.tr",
            "dunya.com",
            "bloomberght.com",
        ]

        if any(d in domain for d in tr_news_sources):
            score += 6

        # Devlet/üniversite kaynakları
        if ".gov" in domain or ".edu" in domain:
            score += 8

        # Wikipedia genel bilgi için iyi ama güncel haber için sınırlı
        if "wikipedia.org" in domain:
            score += 4

        # Genel kategori / etiket sayfalarını düşür
        category_signals = [
            "/etiket/",
            "/tag/",
            "/tags/",
            "/haberleri/",
            "yapay-zeka-haberleri",
            "son-dakika",
            "guncel",
            "güncel",
        ]

        if any(sig in url.lower() for sig in category_signals):
            score -= 6

        # SEO/blog/forum düşük puan
        weak_signals = [
            "blog",
            "forum",
            "medium.com",
            "substack",
            "wordpress",
            "listicle",
            "en-iyi",
            "nedir",
            "ne-zaman",
        ]

        if any(sig in domain or sig in url.lower() for sig in weak_signals):
            score -= 4

        # Güncel soruysa tarih/güncellik izi ara
        current_terms = ["bugün", "güncel", "son durum", "haber", "bu hafta", "bu ay", "2026", "2025"]

        if any(t in query.lower() for t in current_terms):
            date_signals = [
                "2026",
                "2025",
                "bugün",
                "son dakika",
                "güncel",
                "yeni",
                "açıkladı",
                "duyurdu",
                "yayınladı",
                "tanıttı",
            ]

            if any(sig in text for sig in date_signals):
                score += 5
            else:
                score -= 5

        # Çok kısa özet güvenilmez
        if len(body.strip()) < 80:
            score -= 5

        return score

    def _scrape_site(self, url):
        if not sync_playwright:
            return ""

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=15000)
                content = page.inner_text("body")
                browser.close()

                content = re.sub(r"\s+", " ", content).strip()
                return content[:1500]
        except Exception:
            return ""

    def _is_scientific(self, q):
        terms = [
            "kara delik",
            "kuantum",
            "astrofizik",
            "denklem",
            "teori",
            "fizik",
            "evren",
            "izafiyet",
            "band gap",
            "ehull",
            "kristal",
            "alaşım",
            "molekül",
        ]
        return any(t in q.lower() for t in terms)

    def _search_wikipedia(self, query: str):
        results = []

        try:
            wiki = wikipedia.summary(query, sentences=3)
            if wiki:
                results.append(
                    {
                        "source": "WİKİPEDİA",
                        "title": query,
                        "url": "https://tr.wikipedia.org",
                        "content": wiki,
                        "score": 8,
                    }
                )
        except Exception:
            pass

        return results

    def _search_arxiv(self, query: str):
        results = []

        if not self._is_scientific(query):
            return results

        try:
            r = requests.get(
                "http://export.arxiv.org/api/query",
                params={"search_query": f"all:{query}", "max_results": 2},
                timeout=10,
            )

            entries = re.findall(r"<entry>(.*?)</entry>", r.text, re.DOTALL)

            for entry in entries:
                title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
                summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
                link = re.search(r'<link href="(.*?)"', entry)

                if summary:
                    results.append(
                        {
                            "source": "ARXIV",
                            "title": re.sub(r"\s+", " ", title.group(1)).strip() if title else "arXiv",
                            "url": link.group(1) if link else "https://arxiv.org",
                            "content": re.sub(r"\s+", " ", summary.group(1)).strip()[:700],
                            "score": 10,
                        }
                    )

        except Exception:
            pass

        return results

    def _search_duckduckgo(self, query: str):
        results = []

        queries = self._expand_queries(query)

        try:
            with DDGS() as ddgs:
                for q in queries:
                    ddg_res = list(ddgs.text(q, max_results=6))

                    for r in ddg_res:
                        title = r.get("title", "")
                        body = r.get("body", "")
                        url = r.get("href", "")

                        if not url:
                            continue

                        if self._is_bad_result(title, body, url):
                            continue

                        score = self._score_result(query, title, body, url)

                        # İngilizce teknik genişletme sorgularından gelen iyi kaynaklara ekstra puan
                        domain = self._domain(url)
                        if q != query and any(
                            d in domain
                            for d in [
                                "openai.com",
                                "deepmind.google",
                                "anthropic.com",
                                "nvidia.com",
                                "microsoft.com",
                                "technologyreview.com",
                                "reuters.com",
                                "apnews.com",
                                "techcrunch.com",
                                "theverge.com",
                                "wired.com",
                                "venturebeat.com",
                            ]
                        ):
                            score += 8

                        results.append(
                            {
                                "source": "GÜNCEL",
                                "title": title,
                                "url": url,
                                "content": body,
                                "score": score,
                            }
                        )

        except Exception as e:
            results.append(
                {
                    "source": "HATA",
                    "title": "DuckDuckGo hatası",
                    "url": "",
                    "content": str(e),
                    "score": -100,
                }
            )

        return results

    def _search_tavily(self, query: str, deep: bool):
        results = []

        if not self.tavily:
            return results

        if not deep:
            return results

        self._use_credit()

        try:
            tav_res = self.tavily.search(
                query=query,
                search_depth="advanced",
                max_results=5,
            )

            for r in tav_res.get("results", []):
                content = r.get("content", "")
                url = r.get("url", "")
                title = r.get("title", "")

                if not url:
                    continue

                if self._is_bad_result(title, content, url):
                    continue

                score = self._score_result(query, title, content, url) + 8

                results.append(
                    {
                        "source": "TAVILY",
                        "title": title or url,
                        "url": url,
                        "content": content[:800],
                        "score": score,
                    }
                )

        except Exception as e:
            results.append(
                {
                    "source": "HATA",
                    "title": "Tavily hatası",
                    "url": "",
                    "content": str(e),
                    "score": -100,
                }
            )

        return results

    def _format_results(self, query: str, results: list) -> str:
        if not results:
            return "Araştırma sonucu bulunamadı."

        clean = [r for r in results if r.get("score", 0) >= 8]

        if not clean:
            return "Araştırma sonucu bulunamadı."

        def priority_bonus(r):
            domain = self._domain(r.get("url", ""))

            priority_domains = [
                "openai.com",
                "anthropic.com",
                "deepmind.google",
                "technologyreview.com",
                "techcrunch.com",
                "theverge.com",
                "wired.com",
                "reuters.com",
                "apnews.com",
                "nvidia.com",
                "microsoft.com",
                "huggingface.co",
                "arxiv.org",
            ]

            if any(d in domain for d in priority_domains):
                return 100

            return 0

        clean = sorted(
            clean,
            key=lambda x: x.get("score", 0) + priority_bonus(x),
            reverse=True,
        )

        priority_domains = [
            "openai.com",
            "anthropic.com",
            "deepmind.google",
            "technologyreview.com",
            "techcrunch.com",
            "theverge.com",
            "wired.com",
            "reuters.com",
            "apnews.com",
            "nvidia.com",
            "microsoft.com",
            "huggingface.co",
            "arxiv.org",
        ]

        priority_results = [
            r for r in clean
            if any(d in self._domain(r.get("url", "")) for d in priority_domains)
        ]

        final = []
        seen_domains = set()

        # Önce güçlü kaynakları ekle
        for r in priority_results:
            domain = self._domain(r.get("url", ""))

            if domain in seen_domains:
                continue

            seen_domains.add(domain)
            final.append(r)

            if len(final) >= 4:
                break

                   # En az 2 güçlü kaynak varsa zayıf kaynakla tamamlama.
        # 2 kaliteli kaynak, 3 karışık kaynaktan daha iyidir.
        if len(final) < 2:
            blocked_fallback_domains = [
                "shiftdelete.net",
                "ogusto.com",
                "karar.com",
                "abcgazetesi.com.tr",
                "trhaber.com",
                "webtekno.com",
                "tamindir.com",
                "donanimhaber.com",
            ]

            for r in clean:
                domain = self._domain(r.get("url", ""))

                if domain in seen_domains:
                    continue

                if any(b in domain for b in blocked_fallback_domains):
                    continue

                if r.get("score", 0) < 15:
                    continue

                seen_domains.add(domain)
                final.append(r)

                if len(final) >= 4:
                    break
        blocks = []

        for i, r in enumerate(final, start=1):
            blocks.append(
                f"[{i}] {r['source']} | Skor: {r.get('score', 0)}\n"
                f"Başlık: {r.get('title', '')}\n"
                f"Kaynak: {r.get('url', '')}\n"
                f"Özet: {r.get('content', '')[:900]}"
            )

        if not blocks:
            return "Araştırma sonucu bulunamadı."

        return "\n\n".join(blocks)

    def research(self, query, deep=False):
        raw_query = query.strip()
        clean_query = self._normalize_query(raw_query)
        key = clean_query.lower().strip()

            # if key in self.cache:
        #     print("[*] Jarvis bu bilgiyi hatırlıyor. Cache kullanıldı.")
        #     return self.cache[key]

        print(f"[*] {self.get_credit_status()} Araştırma başlatılıyor...")
        print(f"[*] Sorgu: {clean_query}")

        results = []

        # 1. Wikipedia
        results.extend(self._search_wikipedia(clean_query))

        # 2. Bilimsel ise arXiv
        results.extend(self._search_arxiv(clean_query))

        # 3. Güncel web
        results.extend(self._search_duckduckgo(clean_query))

        # 4. Gerekirse derin Tavily
        # Sonuç zayıfsa veya kullanıcı deep istediyse kullan.
        strong_results = [r for r in results if r.get("score", 0) >= 18]

        deep_terms = [
            "derin",
            "kapsamlı",
            "detaylı",
            "kaynaklı",
            "araştırma raporu",
            "rapor hazırla",
            "son gelişmeler",
            "güncel gelişmeler",
        ]

        needs_deep = deep or any(t in raw_query.lower() for t in deep_terms)

        # DuckDuckGo zayıf kaldıysa veya kullanıcı kapsamlı araştırma istediyse Tavily devreye girsin.
        if self.tavily and (needs_deep or len(strong_results) < 3):
            results.extend(self._search_tavily(clean_query, deep=True))

        final_report = self._format_results(clean_query, results)

        # self.cache[key] = final_report
        # self._save_cache()

        return final_report

    def research_and_learn(self, query: str) -> str:
        """
        Eski Jarvis beyni bu metodu çağırıyor.
        Yeni research() metoduna uyumluluk köprüsü.
        """
        return self.research(query, deep=False)