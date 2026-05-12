"""Web Research - Wikipedia + DDG + Google + ArXiv."""
import requests
import json
import re
from urllib.parse import quote
from pathlib import Path


class WebResearcher:
    def __init__(self):
        self.cache_path = Path("memory/research_cache.json")
        self.cache = self._load()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        }

    def _load(self):
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text(encoding='utf-8'))
            except:
                pass
        return {}

    def _save(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=2), encoding='utf-8')

    def research_and_learn(self, query, deep=False):
        q = (query or "").strip()
        if not q:
            return ""
        key = f"{q.lower()}|{deep}"
        if key in self.cache:
            return self.cache[key]
        results = []
        wiki_tr = self._wiki(q, "tr")
        if wiki_tr:
            results.append(("Wikipedia-TR", wiki_tr))
        if not wiki_tr or deep:
            wiki_en = self._wiki(q, "en")
            if wiki_en:
                results.append(("Wikipedia-EN", wiki_en))
        ddg = self._ddg(q)
        if ddg:
            results.append(("DuckDuckGo", ddg))
        if deep or len(results) < 2:
            g = self._google(q)
            if g:
                results.append(("Google", g))
        if self._is_sci(q):
            a = self._arxiv(q)
            if a:
                results.append(("ArXiv", a))
        if not results:
            return ""
        combined = "\n\n".join(f"[{s}]\n{c}" for s, c in results[:4])
        self.cache[key] = combined
        self._save()
        return combined

    def _wiki(self, q, lang="tr"):
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(q)}",
                timeout=10, headers=self.headers)
            if r.status_code == 200:
                d = r.json()
                ext = d.get("extract", "").strip()
                if len(ext) > 50:
                    return f"{d.get('title', q)}: {ext}"
        except:
            pass
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={"action": "query", "list": "search", "srsearch": q,
                        "format": "json", "srlimit": 1},
                timeout=10, headers=self.headers)
            res = r.json().get("query", {}).get("search", [])
            if res:
                return self._wiki(res[0]["title"], lang)
        except:
            pass
        return ""

    def _ddg(self, q):
        try:
            from ddgs import DDGS
            with DDGS() as d:
                res = list(d.text(q, max_results=3, region="tr-tr"))
                if res:
                    parts = []
                    for r in res[:3]:
                        b = r.get("body", "").strip()
                        if b and len(b) > 30:
                            parts.append(f"- {r.get('title', '')}: {b}")
                    if parts:
                        return "\n".join(parts)
        except Exception as e:
            print(f"DDG: {e}")
        return ""

    def _google(self, q):
        try:
            r = requests.get(
                f"https://www.google.com/search?q={quote(q)}&hl=tr&num=5",
                headers=self.headers, timeout=10)
            text = r.text
            snips = []
            patterns = [
                r'<span[^>]*class="[^"]*hgKElc[^"]*"[^>]*>(.*?)</span>',
                r'<div[^>]*class="[^"]*VwiC3b[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*MUxGbd[^"]*"[^>]*>(.*?)</div>',
            ]
            for p in patterns:
                for m in re.findall(p, text, re.DOTALL)[:3]:
                    c = re.sub(r'<[^>]+>', '', m).strip()
                    c = re.sub(r'\s+', ' ', c)
                    if 30 < len(c) < 400 and c not in snips:
                        snips.append(c)
                if len(snips) >= 3:
                    break
            if snips:
                return "\n".join(f"- {s}" for s in snips[:3])
        except Exception as e:
            print(f"GG: {e}")
        return ""

    def _arxiv(self, q):
        try:
            r = requests.get("http://export.arxiv.org/api/query",
                             params={"search_query": f"all:{q}", "max_results": 2},
                             timeout=10)
            entries = re.findall(r'<entry>(.*?)</entry>', r.text, re.DOTALL)
            res = []
            for e in entries[:2]:
                tm = re.search(r'<title>(.*?)</title>', e, re.DOTALL)
                sm = re.search(r'<summary>(.*?)</summary>', e, re.DOTALL)
                if tm and sm:
                    t = re.sub(r'\s+', ' ', tm.group(1).strip())
                    s = re.sub(r'\s+', ' ', sm.group(1).strip())[:300]
                    res.append(f"{t}: {s}")
            return "\n\n".join(res) if res else ""
        except:
            return ""

    def _is_sci(self, q):
        terms = ['ehull', 'band gap', 'molecule', 'protein', 'algorithm',
                 'theorem', 'kuantum', 'fizik', 'kimya', 'biyoloji',
                 'mev/atom', 'ev/atom', 'denklem', 'compound', 'crystal']
        ql = q.lower()
        return any(t in ql for t in terms)
