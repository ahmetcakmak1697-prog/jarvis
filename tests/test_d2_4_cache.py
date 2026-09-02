#!/usr/bin/env python3
"""
D2.4 — Web Research Cache + Rate Limit Test
============================================

Amac:
    WebResearcher'a D2.4 ile eklenen cache + rate-limit + credit davranisini
    dogrulamak. Gercek web cagrisi YOK — arama metotlari mock'lanir.

Tasarim:
    - temp dir'e gecilir (memory/ orada olusur, uretim dosyalarina dokunulmaz)
    - dis bagimliliklar (tavily, wikipedia, ddgs, playwright) mock'lanir
    - arama metotlari (_search_*) mock'lanir
    - pytest olmadan `python tests/test_d2_4_cache.py` ile calisir

Test senaryolari:
    T01 __init__ D2.4 alanlari kuruldu
    T02 cache_put + cache_get (taze) calisiyor
    T03 cache TTL bayat -> None
    T04 rate_ok tavanda False, altinda True
    T05 ilk research() cache MISS -> web'e cikar, cache'e yazar
    T06 ayni sorgu research() cache HIT -> web'e CIKMAZ
    T07 credit sadece cache miss'te dusiyor
    T08 last_source_scores cache hit'te korunuyor
    T09 rate limit research() icinde tetikleniyor
    T10 otomatik long-term memory write YOK
"""

from __future__ import annotations

import sys
import os
import tempfile
import importlib.util
from pathlib import Path
import unittest.mock as mock

ROOT = Path(__file__).resolve().parents[1]
WEB_RESEARCH = ROOT / "tools" / "web_research.py"


# ── Renk ──────────────────────────────────────────────────────────────────────
def _g(s): return f"\033[32m{s}\033[0m"
def _r(s): return f"\033[31m{s}\033[0m"
def _b(s): return f"\033[1m{s}\033[0m"

_results = []
def t(name, cond, detail=""):
    _results.append((name, cond, detail))
    icon = _g("PASS") if cond else _r("FAIL")
    line = f"  [{icon}] {name}"
    if detail:
        line += f"  ({detail})"
    print(line)


def load_web_researcher(audit_sink):
    """Dis bagimliliklari mock'layip WebResearcher'i yukler."""
    for m in ["agents.source_scorer", "dotenv", "wikipedia", "ddgs",
              "tavily", "playwright", "playwright.sync_api",
              "overrides", "requests"]:
        sys.modules[m] = mock.MagicMock()
    sys.modules["overrides"].final = lambda x: x

    audit_mock = mock.MagicMock()
    audit_mock.log.side_effect = lambda **k: audit_sink.append(k.get("event"))
    am = mock.MagicMock()
    am.AuditLogger.return_value = audit_mock
    sys.modules["agents.audit_logger"] = am

    spec = importlib.util.spec_from_file_location("web_research_d24", str(WEB_RESEARCH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.WebResearcher, audit_mock


def fake_search_factory(counter):
    def _f(*a, **k):
        counter["n"] += 1
        return [{
            "url": "http://test.com", "title": "Test", "body": "icerik",
            "score": 20, "source_score": 80, "source_tier": "high",
        }]
    return _f


def run_tests(tmp):
    os.chdir(tmp)
    os.makedirs("memory", exist_ok=True)
    import json

    audit_sink = []
    WebResearcher, audit_mock = load_web_researcher(audit_sink)

    # T01 — __init__ alanlari
    wr = WebResearcher()
    wr._audit = audit_mock
    t("T01 cache_ttl_seconds = 6h", wr._cache_ttl_seconds == 6 * 3600, f"{wr._cache_ttl_seconds}")
    t("T01 rate_limit_per_hour = 30", wr._rate_limit_per_hour == 30)
    t("T01 request_times bos baslar", wr._request_times == [])

    # T02 — cache put/get
    wr._cache_put("k1", "rapor1", [{"url": "x.com", "score": 50}])
    got = wr._cache_get("k1")
    t("T02 cache_put + get taze", got is not None and got["report"] == "rapor1")
    t("T02 source_scores cache'te", got and got["source_scores"][0]["url"] == "x.com")

    # T03 — TTL bayat
    wr.cache["eski"] = {"report": "eski", "source_scores": [], "ts": 0}
    t("T03 bayat cache None doner", wr._cache_get("eski") is None)

    # T04 — rate_ok
    wr_rl = WebResearcher()
    for _ in range(30):
        wr_rl._record_request()
    t("T04 30 istek -> rate_ok False", wr_rl._rate_ok() is False)
    wr_rl2 = WebResearcher()
    for _ in range(29):
        wr_rl2._record_request()
    t("T04 29 istek -> rate_ok True", wr_rl2._rate_ok() is True)

    # T05-T08 — research() cache akisi
    counter = {"n": 0}
    wr2 = WebResearcher()
    wr2._audit = audit_mock
    wr2._search_wikipedia = fake_search_factory(counter)
    wr2._search_arxiv = lambda q: []
    wr2._search_duckduckgo = fake_search_factory(counter)
    wr2._search_tavily = lambda q, deep: []
    wr2._is_scientific = lambda q: False

    before_credit = json.loads(open("memory/search_credits.json").read())["remaining"]

    audit_sink.clear()
    r1 = wr2.research("izmir hava")
    miss_searches = counter["n"]
    t("T05 ilk research web'e cikar", miss_searches > 0, f"{miss_searches} arama")
    t("T05 cache_miss audit", "web_cache_miss" in audit_sink)

    audit_sink.clear()
    r2 = wr2.research("izmir hava")
    t("T06 ayni sorgu cache hit, web yok", counter["n"] == miss_searches, f"arama {counter['n']}")
    t("T06 cache_hit audit", "web_cache_hit" in audit_sink)
    t("T06 cache ayni rapor", r2 == r1)

    after_credit = json.loads(open("memory/search_credits.json").read())["remaining"]
    t("T07 credit sadece miss'te dusiyor", after_credit == before_credit - 1,
      f"{before_credit}->{after_credit}")

    t("T08 last_source_scores cache hit'te korunur", len(wr2.last_source_scores) > 0,
      f"{len(wr2.last_source_scores)} kaynak")

    # T09 — rate limit research() icinde
    counter2 = {"n": 0}
    wr3 = WebResearcher()
    wr3._audit = audit_mock
    wr3._search_wikipedia = fake_search_factory(counter2)
    wr3._search_arxiv = lambda q: []
    wr3._search_duckduckgo = lambda q: []
    wr3._search_tavily = lambda q, deep: []
    wr3._is_scientific = lambda q: False
    for _ in range(30):
        wr3._record_request()
    audit_sink.clear()
    r_rl = wr3.research("yepyeni rate limit sorgusu")
    t("T09 rate limit research icinde tetiklenir", "web_rate_limited" in audit_sink)
    t("T09 rate limit mesaji doner", "sinir" in r_rl.lower())

    # T10 — otomatik long-term memory write YOK
    # research_cache.json var ama bu uzun-vadeli hafiza degil; conversations.json'a
    # yazim olmamali. Cache != memory.
    conv_exists = Path("memory/conversations.json").exists()
    t("T10 conversations.json'a otomatik yazim yok", not conv_exists,
      "cache != long-term memory")


def main():
    print(_b("\n═══════════════════════════════════════════════════════"))
    print(_b(" D2.4 — Web Research Cache + Rate Limit Test"))
    print(_b("═══════════════════════════════════════════════════════"))
    print(" Temp dir + mock — uretim dosyalarina ve web'e dokunulmaz.\n")

    if not WEB_RESEARCH.exists():
        print(_r(f"[HATA] {WEB_RESEARCH} bulunamadi."))
        sys.exit(1)

    cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory(prefix="jarvis_d24_", ignore_cleanup_errors=True) as tmp:
            print(f" Temp dir: {tmp}\n")
            run_tests(tmp)
    finally:
        os.chdir(cwd)

    total = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = total - passed

    print()
    print(_b("─── Ozet ────────────────────────────────────────────────"))
    print(f"  Toplam: {total}  PASS: {passed}  FAIL: {failed}")
    print()
    if failed == 0:
        print(_g(_b("  ✓ D2.4 GECTI — cache + rate limit + credit dogru calisiyor.")))
        code = 0
    else:
        print(_r(_b(f"  ✗ D2.4 BASARISIZ — {failed} test fail.")))
        for n, ok, d in _results:
            if not ok:
                print(_r(f"    - {n}: {d}"))
        code = 1
    print()
    sys.exit(code)


if __name__ == "__main__":
    main()
