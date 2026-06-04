import os
import json
import re
from overrides import final
import requests
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from agents.source_scorer import SourceScorer

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

        self.source_scorer = SourceScorer()
        self.last_source_scores = []

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.credit_path.parent.mkdir(parents=True, exist_ok=True)

        self.cache = self._load_json(self.cache_path)
        self._init_credits()

        # D2.4: cache TTL + rate limit + audit
        self._cache_ttl_seconds = 6 * 3600       # 6 saat tazelik
        self._rate_limit_per_hour = 30            # saatlik web istegi tavani
        self._request_times = []                  # son istek zaman damgalari
        try:
            from agents.audit_logger import AuditLogger
            self._audit = AuditLogger()
        except Exception:
            self._audit = None

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

    def _apply_source_scores(self, results: list) -> list:
        """Attach D1.5 SourceScorer metadata to raw web results."""
        enriched = []

        for item in results or []:
            if not isinstance(item, dict):
                continue

            try:
                scored = self.source_scorer.score_source(
                    url=str(item.get("url") or ""),
                    title=str(item.get("title") or ""),
                    snippet=str(item.get("content") or item.get("body") or ""),
                ).to_dict()

                item = dict(item)
                item["source_score"] = int(scored.get("score", 0) or 0)
                item["source_tier"] = scored.get("tier", "low")
                item["source_reasons"] = scored.get("reasons", [])
                item["retrieved_at"] = scored.get("retrieved_at", "")
            except Exception:
                item = dict(item)
                item["source_score"] = 50
                item["source_tier"] = "unknown"
                item["source_reasons"] = ["source_scorer_failed"]

            enriched.append(item)

        return enriched


    def _format_results(self, query: str, results: list) -> str:
        if not results:
            return "Araştırma sonucu bulunamadı."

        results = self._apply_source_scores(results)

        self.last_source_scores = [
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "score": r.get("source_score", 0),
                "tier": r.get("source_tier", "unknown"),
                "reasons": r.get("source_reasons", []),
                "source": r.get("source", ""),
            }
            for r in results
            if isinstance(r, dict)
        ]

        # Eski lokal skor + yeni kaynak güven skoru birlikte çalışır.
        clean = [
            r for r in results
            if r.get("score", 0) >= 8
            and r.get("source_tier") != "blocked"
            and r.get("source_score", 0) >= 40
        ]

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
                "gov.tr",
                "gov.uk",
                "nature.com",
                "science.org",
            ]

            if any(d in domain for d in priority_domains):
                return 100

            return 0

        clean = sorted(
            clean,
            key=lambda x: (
                int(x.get("source_score", 0) or 0)
                + int(x.get("score", 0) or 0)
                + priority_bonus(x)
            ),
            reverse=True,
        )

        blocks = []
        seen_domains = set()

        for r in clean:
            domain = self._domain(r.get("url", ""))

            if domain in seen_domains:
                continue

            seen_domains.add(domain)

            title = (r.get("title") or "Kaynak").strip()
            url = (r.get("url") or "").strip()
            content = (r.get("content") or "").strip()
            source = (r.get("source") or "WEB").strip()

            source_score = int(r.get("source_score", 0) or 0)
            source_tier = r.get("source_tier", "unknown")
            source_reasons = r.get("source_reasons", [])
            if isinstance(source_reasons, list):
                source_reasons = ", ".join(str(x) for x in source_reasons[:4])

            content = re.sub(r"\s+", " ", content)[:700]

            blocks.append(
                f"[{len(blocks) + 1}] {title}\n"
                f"Kaynak: {source} | {url}\n"
                f"Güven: {source_tier} / {source_score}\n"
                f"Güven nedeni: {source_reasons}\n"
                f"Özet: {content}"
            )

            if len(blocks) >= 5:
                break

        if not blocks:
            return "Araştırma sonucu bulunamadı."

        return "\n\n".join(blocks)


    def research(self, query, deep=False):
        raw_query = query.strip()
        clean_query = self._normalize_query(raw_query)
        key = clean_query.lower().strip()

        # D2.4: cache kontrol (TTL'li). Taze cache varsa web'e cikma.
        cached = self._cache_get(key)
        if cached is not None:
            self.last_source_scores = cached.get("source_scores", []) or []
            if self._audit:
                try:
                    self._audit.log(event="web_cache_hit", query=clean_query,
                                    action="cache_hit",
                                    payload={"key": key[:120]})
                except Exception:
                    pass
            print("[*] D2.4 cache hit — web'e cikilmadi.")
            return cached.get("report", "")

        # D2.4: rate limit kontrol. Tavan asildiysa web'e cikma.
        if not self._rate_ok():
            if self._audit:
                try:
                    self._audit.log(event="web_rate_limited", query=clean_query,
                                    action="rate_limited",
                                    payload={"limit_per_hour": self._rate_limit_per_hour})
                except Exception:
                    pass
            return (
                "Saatlik web arastirma siniri doldu efendim. "
                "Biraz sonra tekrar deneyelim; bu sinir API kredisini korur."
            )

        # D2.4: cache miss — web arastirmasi yapilacak.
        if self._audit:
            try:
                self._audit.log(event="web_cache_miss", query=clean_query,
                                action="cache_miss", payload={"key": key[:120]})
            except Exception:
                pass
        self._record_request()

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

        # D2.4: sonucu cache'e yaz (source_scores dahil) + kredi kullan.
        # Otomatik long-term memory YOK; bu sadece kisa sureli arastirma cache'i.
        try:
            self._cache_put(key, final_report, self.last_source_scores)
        except Exception:
            pass
        self._use_credit()

        return final_report

    # ── D2.4 cache + rate-limit yardimcilari ──────────────────────────
    def _now_ts(self) -> float:
        import time
        return time.time()

    def _cache_get(self, key: str):
        """TTL'li cache okuma. Taze degilse None doner."""
        if not key:
            return None
        entry = self.cache.get(key)
        if not isinstance(entry, dict):
            return None
        ts = entry.get("ts", 0)
        if (self._now_ts() - ts) > self._cache_ttl_seconds:
            return None  # bayat
        return entry

    def _cache_put(self, key: str, report: str, source_scores) -> None:
        """Cache'e yaz: rapor + kaynaklar + zaman damgasi."""
        if not key:
            return
        self.cache[key] = {
            "report": report,
            "source_scores": source_scores or [],
            "ts": self._now_ts(),
        }
        self._save_cache()

    def _rate_ok(self) -> bool:
        """Son 1 saatteki istek sayisi tavanin altinda mi?"""
        now = self._now_ts()
        self._request_times = [t for t in self._request_times if (now - t) < 3600]
        return len(self._request_times) < self._rate_limit_per_hour

    def _record_request(self) -> None:
        self._request_times.append(self._now_ts())

    def research_and_learn(self, query: str) -> str:
        """
        Eski Jarvis beyni bu metodu çağırıyor.
        Yeni research() metoduna uyumluluk köprüsü.
        """
        return self.research(query, deep=False)