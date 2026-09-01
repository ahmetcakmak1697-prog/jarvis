#!/usr/bin/env python3
"""
D2.3 — Memory Candidate + Audit Lifecycle Test
===============================================

Amac:
    MemoryCandidateQueue ve AuditLogger'in D1-D2 beklentilerini
    karsiladigini dogrulamak.

Tasarim:
    - temp root kullanilir — uretim memory/ dosyalarina DOKUNULMAZ
    - gercek web cagrisi YOK
    - Telegram/API cagrisi YOK
    - pytest olmadan `python tests/test_d2_lifecycle.py` ile calisir
    - her test PASS/FAIL yazar, fail varsa exit 1

Test senaryolari:
    T01 add_web_candidate → pending_review olusturur
    T02 memory_candidates.json dosyasi yazildi
    T03 audit log → web_candidate_queued event var
    T04 candidate ID, status, tier, query icerigi dogru
    T05 list_pending() → olusan candidate geri geliyor
    T06 get(candidate_id) → dogru candidate doniyor
    T07 decide(reject) → status rejected olur
    T08 audit log → memory_candidate_decision (reject) event var
    T09 decide(deferred) → status deferred olur
    T10 decide(deferred) → audit log'da decision event var
    T11 mark_stored() → status stored olur
    T12 audit log → memory_candidate_stored event var
    T13 stats() → counts dogru
    T14 duplicate add → ayni ID, dosyaya tekrar eklenmez
    T15 bos research_text → graceful (patlamamali)
    T16 uzun hafizaya otomatik yazim YOK
        (decide() dogrudan memory'ye yazmaz, sadece status gunceller)
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.memory_candidate_queue import MemoryCandidateQueue
from agents.audit_logger import AuditLogger


# ── Renk yardimcilari ─────────────────────────────────────────────────────────
def _g(s): return f"\033[32m{s}\033[0m"
def _r(s): return f"\033[31m{s}\033[0m"
def _b(s): return f"\033[1m{s}\033[0m"
def _d(s): return f"\033[2m{s}\033[0m"


# ── Test calistirici ──────────────────────────────────────────────────────────
_results: list[tuple[str, bool, str]] = []

def t(name: str, cond: bool, detail: str = "") -> None:
    _results.append((name, cond, detail))
    icon = _g("PASS") if cond else _r("FAIL")
    line = f"  [{icon}] {name}"
    if not cond and detail:
        line += f"\n         {_r(detail)}"
    elif cond and detail:
        line += f"  {_d(detail)}"
    print(line)


# ── Ortak test verisi ─────────────────────────────────────────────────────────
SAMPLE_RESEARCH = (
    "[1] Baslik: Izmir Hava Durumu\n"
    "Kaynak: MGM | https://mgm.gov.tr/tahmin/il-ve-ilceler.aspx?m=IZMIR\n"
    "Guven: high / 90\n"
    "Ozet: Izmir icin bugun acik hava, sicaklik 26-29 derece bekleniyor.\n\n"
    "[2] Baslik: Izmir 5 Gunluk Tahmin\n"
    "Kaynak: AccuWeather | https://www.accuweather.com/tr/tr/izmir\n"
    "Guven: medium / 65\n"
    "Ozet: Hafta boyunca kararli sicakliklar devam edecek.\n"
)

SAMPLE_SOURCES = [
    {"url": "https://mgm.gov.tr/tahmin/il-ve-ilceler.aspx?m=IZMIR", "score": 90, "tier": "high",   "reasons": ["official_source"]},
    {"url": "https://www.accuweather.com/tr/tr/izmir",              "score": 65, "tier": "medium", "reasons": ["known_provider"]},
]

SAMPLE_QUERY = "Izmir bugun hava durumu"


# ── Testler ───────────────────────────────────────────────────────────────────

def run_tests(tmp: str) -> None:
    tmp_root = Path(tmp)
    q = MemoryCandidateQueue(root=tmp_root)
    a = AuditLogger(root=tmp_root)

    print(_b("\n─── T01-T06: add_web_candidate lifecycle ────────────────"))

    # T01 — add_web_candidate pending_review olusturur
    c = q.add_web_candidate(
        query=SAMPLE_QUERY,
        research_text=SAMPLE_RESEARCH,
        source_scores=SAMPLE_SOURCES,
        mode="telegram",
        ttl_days=30,
        tags=["web_research", "telegram", "d2_test"],
    )

    t("T01 add_web_candidate donus dict",
      isinstance(c, dict),
      f"type={type(c)}")

    t("T01 status pending_review",
      c.get("status") == "pending_review",
      f"status={c.get('status')}")

    cid = c.get("id", "")
    t("T01 candidate ID olusturuldu",
      isinstance(cid, str) and cid.startswith("mc_"),
      f"id={cid}")

    # T02 — memory_candidates.json yazildi
    candidates_path = tmp_root / "memory" / "memory_candidates.json"
    t("T02 memory_candidates.json var",
      candidates_path.exists(),
      str(candidates_path))

    if candidates_path.exists():
        data = json.loads(candidates_path.read_text(encoding="utf-8"))
        t("T02 dosyada en az 1 kayit",
          len(data) >= 1,
          f"count={len(data)}")
        t("T02 ilk kayit pending_review",
          data[0].get("status") == "pending_review",
          f"status={data[0].get('status')}")
    else:
        t("T02 dosyada en az 1 kayit",  False, "dosya yok")
        t("T02 ilk kayit pending_review", False, "dosya yok")

    # T03 — audit log web_candidate_queued var
    tail  = a.tail(10)
    evts  = [e.get("event") for e in tail]
    t("T03 audit log web_candidate_queued",
      "web_candidate_queued" in evts,
      f"events={evts}")

    # T04 — candidate icerik dogrulugu
    t("T04 query alanı dogru",
      c.get("query") == SAMPLE_QUERY,
      f"query={c.get('query')!r}")

    t("T04 tier dolu",
      bool(c.get("tier")),
      f"tier={c.get('tier')}")

    t("T04 source_urls en az 1 URL",
      len(c.get("source_urls", [])) >= 1,
      f"urls={c.get('source_urls')}")

    t("T04 expires_at dolu (ttl_days=30)",
      bool(c.get("expires_at")),
      f"expires_at={c.get('expires_at')}")

    # T05 — list_pending
    pending = q.list_pending(limit=5)
    t("T05 list_pending donus liste",
      isinstance(pending, list),
      f"type={type(pending)}")

    t("T05 list_pending icinde cid var",
      any(p.get("id") == cid for p in pending),
      f"pending IDs={[p.get('id') for p in pending]}")

    # T06 — get(candidate_id)
    got = q.get(cid)
    t("T06 get() dogru candidate doniyor",
      got is not None and got.get("id") == cid,
      f"got id={got.get('id') if got else None}")

    # ─────────────────────────────────────────────────────────────────────────
    print(_b("\n─── T07-T10: decide() lifecycle ─────────────────────────"))

    # T07 — decide(rejected)
    r_rej = q.decide(cid, "rejected")
    t("T07 decide(rejected) ok=True",
      r_rej.get("ok") is True,
      f"result={r_rej}")

    t("T07 status rejected oldu",
      r_rej.get("candidate", {}).get("status") == "rejected",
      f"status={r_rej.get('candidate', {}).get('status')}")

    # T08 — audit log: rejected decision event
    tail2 = a.tail(10)
    decision_events = [e for e in tail2 if e.get("event") == "memory_candidate_decision"]
    t("T08 audit log memory_candidate_decision var",
      len(decision_events) >= 1,
      f"decision events count={len(decision_events)}")

    t("T08 decision action=rejected",
      any(e.get("action") == "rejected" for e in decision_events),
      f"actions={[e.get('action') for e in decision_events]}")

    # T09 — yeni candidate + decide(deferred)
    c2 = q.add_web_candidate(
        query="deferred test sorgusu",
        research_text="[1] Baslik: Test\nKaynak: example.com\nOzet: Deferred test.",
        source_scores=[],
        mode="sync",
        ttl_days=7,
        tags=["d2_test"],
    )
    cid2 = c2.get("id", "")

    r_def = q.decide(cid2, "deferred")
    t("T09 decide(deferred) ok=True",
      r_def.get("ok") is True,
      f"result={r_def}")

    t("T09 status deferred oldu",
      r_def.get("candidate", {}).get("status") == "deferred",
      f"status={r_def.get('candidate', {}).get('status')}")

    # T10 — audit log: deferred decision event
    tail3 = a.tail(20)
    t("T10 audit log deferred event var",
      any(e.get("action") == "deferred" for e in tail3),
      f"actions={[e.get('action') for e in tail3]}")

    # ─────────────────────────────────────────────────────────────────────────
    print(_b("\n─── T11-T13: mark_stored() + stats ──────────────────────"))

    # T11 — mark_stored
    c3 = q.add_web_candidate(
        query="stored test sorgusu",
        research_text="[1] Baslik: Stored Test\nKaynak: stored.com\nOzet: Stored test ozeti.",
        source_scores=[{"url": "https://stored.com", "score": 80, "tier": "high", "reasons": []}],
        mode="sync",
        ttl_days=60,
        tags=["d2_test"],
    )
    cid3 = c3.get("id", "")

    r_store = q.mark_stored(cid3, store_meta={"vector_id": "vec_test_001"})
    t("T11 mark_stored ok=True",
      r_store.get("ok") is True,
      f"result keys={list(r_store.keys())}")

    t("T11 status stored oldu",
      r_store.get("candidate", {}).get("status") == "stored",
      f"status={r_store.get('candidate', {}).get('status')}")

    t("T11 store_meta yazildi",
      r_store.get("candidate", {}).get("store_meta", {}).get("vector_id") == "vec_test_001",
      f"store_meta={r_store.get('candidate', {}).get('store_meta')}")

    # T12 — audit log: stored event
    tail4 = a.tail(20)
    t("T12 audit log memory_candidate_stored var",
      any(e.get("event") == "memory_candidate_stored" for e in tail4),
      f"events={[e.get('event') for e in tail4]}")

    # T13 — stats
    s = q.stats()
    t("T13 stats() donus dict",
      isinstance(s, dict),
      f"type={type(s)}")

    t("T13 stats total >= 3",
      s.get("total", 0) >= 3,
      f"total={s.get('total')}")

    t("T13 stats counts icinde stored",
      "stored" in s.get("counts", {}),
      f"counts={s.get('counts')}")

    # ─────────────────────────────────────────────────────────────────────────
    print(_b("\n─── T14-T16: guvenlik / edge case ───────────────────────"))

    # T14 — duplicate add_web_candidate ayni ID → dosyaya tekrar eklenmiyor
    before_count = q.stats()["total"]
    q.add_web_candidate(
        query=SAMPLE_QUERY,
        research_text=SAMPLE_RESEARCH,
        source_scores=SAMPLE_SOURCES,
        mode="telegram",
        ttl_days=30,
        tags=["d2_test"],
    )
    after_count = q.stats()["total"]
    t("T14 duplicate add yeni satir eklemez (idempotent)",
      after_count == before_count,
      f"before={before_count} after={after_count}")

    # T15 — bos research_text patlamaz
    try:
        c_empty = q.add_web_candidate(
            query="bos arastirma sorgusu",
            research_text="",
            source_scores=[],
            mode="sync",
            ttl_days=1,
        )
        t("T15 bos research_text patlamaz",
          isinstance(c_empty, dict),
          f"status={c_empty.get('status')}")
    except Exception as exc:
        t("T15 bos research_text patlamaz", False, f"exception: {exc}")

    # T16 — decide() dogrudan vector memory'ye YAZMIYOR
    # Kontrol: decide() ciktisinda vector_id veya chroma referansi olmamali
    r_check = q.decide(cid, "rejected")  # zaten rejected ama yine de cagir
    candidate_raw = r_check.get("candidate", {})
    vector_written = "vector_id" in candidate_raw or "chroma_id" in candidate_raw
    t("T16 decide() otomatik vector write YAPMAZ",
      not vector_written,
      f"candidate keys={list(candidate_raw.keys())}")


# ── Ana akis ──────────────────────────────────────────────────────────────────

def main() -> None:
    print(_b("\n═══════════════════════════════════════════════════════"))
    print(_b(" D2.3 — Memory Candidate + Audit Lifecycle Test"))
    print(_b("═══════════════════════════════════════════════════════"))
    print(" Temp root kullaniliyor — uretim dosyalarina dokunulmaz.")
    print()

    with tempfile.TemporaryDirectory(prefix="jarvis_d2_test_") as tmp:
        print(f" Temp dir : {tmp}\n")
        run_tests(tmp)

    total  = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = total - passed

    print()
    print(_b("─── Ozet ────────────────────────────────────────────────"))
    print(f"  Toplam : {total}")
    print(f"  PASS   : {passed}")
    print(f"  FAIL   : {failed}")
    print()

    if failed == 0:
        print(_g(_b("  ✓ D2.3 GECTI — Candidate/Audit lifecycle dogru calisiyor.")))
        exit_code = 0
    else:
        print(_r(_b(f"  ✗ D2.3 BASARISIZ — {failed} test fail oldu.")))
        for name, ok, detail in _results:
            if not ok:
                print(_r(f"    - {name}: {detail}"))
        exit_code = 1

    print()
    print(_b("═══════════════════════════════════════════════════════"))
    print()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
