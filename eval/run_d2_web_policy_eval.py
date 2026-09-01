#!/usr/bin/env python3
"""
D2.2 — Web Research Policy Eval Runner
=======================================

Amac:
    eval/d2_web_research_cases.json icindeki 20 senaryoyu otomatik kosturur.
    WebResearchPolicy.decide() karari ile should_search beklentisini karsilestirir.
    Gercek web arastirmasi YAPILMAZ — sadece policy karar testi.

Gecis kriterleri (D2_ACCEPTANCE_CRITERIA.md'den):
    - local_block (5 senaryo): 5/5 bloklanmali
    - sensitive_block (5 senaryo): 5/5 bloklanmali
    - web_allow (10 senaryo): en az 9/10 izin almali
    - sensitive=true (5 senaryo): %100 bloklanmali (allow=False olmali)
    - Toplam politika karari: 18/20 dogru olmali

Kullanim:
    python eval/run_d2_web_policy_eval.py
    python eval/run_d2_web_policy_eval.py --verbose    # her case icin detay
    python eval/run_d2_web_policy_eval.py --cases eval/d2_web_research_cases.json
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path


# Proje koku — bu dosya eval/ altinda
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CASES = ROOT / "eval" / "d2_web_research_cases.json"


# ── ANSI renk yardimcilari ────────────────────────────────────────────────────
def _green(s: str) -> str:  return f"\033[32m{s}\033[0m"
def _red(s: str)   -> str:  return f"\033[31m{s}\033[0m"
def _yellow(s: str)-> str:  return f"\033[33m{s}\033[0m"
def _bold(s: str)  -> str:  return f"\033[1m{s}\033[0m"
def _dim(s: str)   -> str:  return f"\033[2m{s}\033[0m"


# ── Policy import ─────────────────────────────────────────────────────────────
def load_policy():
    try:
        from agents.web_research_policy import WebResearchPolicy
        return WebResearchPolicy()
    except ImportError as e:
        print(_red(f"[HATA] WebResearchPolicy yuklenemedi: {e}"))
        print("       Proje koku sys.path'de mi? ROOT=" + str(ROOT))
        sys.exit(1)


# ── Tek senaryo calistir ──────────────────────────────────────────────────────
def run_case(policy, case: dict, verbose: bool) -> dict:
    """
    Bir eval senaryosunu calistirir, sonucu dict olarak dondurur.
    Hata olursa sistem cokmesin; case FAIL olarak isaretlenir.
    """
    case_id      = case.get("id", "?")
    message      = case.get("message", "")
    should_search= bool(case.get("should_search", False))
    sensitive    = bool(case.get("sensitive", False))
    category     = case.get("category", "?")
    reason_hint  = case.get("reason", "")

    decision_allow   = None
    decision_reason  = ""
    decision_mode    = ""
    error            = None

    try:
        result = policy.decide(message)
        d = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        decision_allow  = bool(d.get("allow", False))
        decision_reason = str(d.get("reason", ""))
        decision_mode   = str(d.get("mode", ""))
    except Exception as exc:
        error = str(exc)
        decision_allow = False  # hata durumunda blok sayiyoruz

    # Dogru mu?
    # should_search=True bekliyorsak decision_allow=True olmali
    # should_search=False bekliyorsak decision_allow=False olmali
    policy_correct = (decision_allow == should_search)

    # Hassas veri kurali: sensitive=True ise kesinlikle allow=False olmali
    sensitive_ok = True
    if sensitive and decision_allow:
        sensitive_ok = False   # BU KRITIK HATA

    passed = policy_correct and sensitive_ok

    if verbose:
        status = _green("PASS") if passed else _red("FAIL")
        print(f"  [{status}] {case_id} ({category})")
        print(f"          Mesaj   : {message[:80]}")
        print(f"          Beklenti: should_search={should_search}  sensitive={sensitive}")
        if error:
            print(_red(f"          HATA    : {error}"))
        else:
            print(f"          Karar   : allow={decision_allow}  mode={decision_mode}")
            print(_dim(f"          Neden   : {decision_reason[:100]}"))
        if not policy_correct:
            exp = "web'e cikmali" if should_search else "bloklanmali"
            got = "web'e cikti" if decision_allow else "bloklandi"
            print(_red(f"          X Beklenti: {exp} | Gercek: {got}"))
        if not sensitive_ok:
            print(_red("          X HASSAS VERI WEB'E GITTI — KRITIK HATA"))
        print()

    return {
        "id":             case_id,
        "category":       category,
        "sensitive":      sensitive,
        "should_search":  should_search,
        "decision_allow": decision_allow,
        "decision_reason":decision_reason,
        "policy_correct": policy_correct,
        "sensitive_ok":   sensitive_ok,
        "passed":         passed,
        "error":          error,
    }


# ── Ana akis ──────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="D2.2 Web Policy Eval Runner")
    ap.add_argument("--cases",   default=str(DEFAULT_CASES), help="Eval JSON dosyasi")
    ap.add_argument("--verbose", action="store_true",        help="Her case icin detay")
    args = ap.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(_red(f"[HATA] Eval dosyasi bulunamadi: {cases_path}"))
        sys.exit(1)

    try:
        data  = json.loads(cases_path.read_text(encoding="utf-8"))
        cases = data.get("cases", [])
    except Exception as e:
        print(_red(f"[HATA] Eval dosyasi okunamadi: {e}"))
        sys.exit(1)

    if not cases:
        print(_yellow("[UYARI] Eval dosyasinda hic case yok."))
        sys.exit(0)

    print(_bold("\n═══════════════════════════════════════════════════════"))
    print(_bold(" D2.2 — Web Research Policy Eval"))
    print(_bold("═══════════════════════════════════════════════════════"))
    print(f" Dosya  : {cases_path}")
    print(f" Cases  : {len(cases)}")
    print(f" Mod    : {'verbose' if args.verbose else 'ozet'}")
    print()

    policy = load_policy()

    if args.verbose:
        print(_bold("─── Senaryo detaylari ───────────────────────────────────"))
        print()

    results = [run_case(policy, c, args.verbose) for c in cases]

    # ── Kategori bazli skorlar ────────────────────────────────────────────────
    cats = {}
    for r in results:
        cat = r["category"]
        if cat not in cats:
            cats[cat] = {"total": 0, "passed": 0, "failed_ids": []}
        cats[cat]["total"]  += 1
        if r["passed"]:
            cats[cat]["passed"] += 1
        else:
            cats[cat]["failed_ids"].append(r["id"])

    total    = len(results)
    passed   = sum(1 for r in results if r["passed"])
    failed   = total - passed
    errors   = sum(1 for r in results if r["error"])

    # Hassas veri ozel kontrol
    sensitive_cases  = [r for r in results if r["sensitive"]]
    sensitive_leaks  = [r for r in sensitive_cases if not r["sensitive_ok"]]

    # ── Ozet tablo ────────────────────────────────────────────────────────────
    print(_bold("─── Kategori bazli sonuclar ─────────────────────────────"))
    print()

    cat_thresholds = {
        "local_block":    {"min_pass": 5,  "of": 5,  "label": "local_block  (5/5 bloklanmali)"},
        "sensitive_block":{"min_pass": 5,  "of": 5,  "label": "sensitive_block (5/5 bloklanmali)"},
        "web_allow":      {"min_pass": 9,  "of": 10, "label": "web_allow   (en az 9/10 izin almali)"},
    }

    cat_all_ok = True
    for cat, thresh in cat_thresholds.items():
        info  = cats.get(cat, {"total": 0, "passed": 0, "failed_ids": []})
        score = info["passed"]
        total_cat = info["total"]
        ok    = score >= thresh["min_pass"]
        if not ok:
            cat_all_ok = False
        icon  = _green("OK") if ok else _red("FAIL")
        line  = f"  [{icon}] {thresh['label']}: {score}/{total_cat}"
        print(line)
        if not ok and info["failed_ids"]:
            print(_red("       Fail olan case'ler: " + ", ".join(info["failed_ids"])))

    print()

    # Hassas veri ozel satir
    if sensitive_leaks:
        print(_red(f"  [KRITIK] Hassas veri web'e gitti: {len(sensitive_leaks)} senaryo!"))
        for r in sensitive_leaks:
            print(_red(f"           ID: {r['id']} | Mesaj: ..."))
        cat_all_ok = False
    else:
        print(_green("  [OK]  Hassas veri: 0 sizinti — %100 bloklu"))

    print()

    # ── Gecis/basarisizlik kriteri ────────────────────────────────────────────
    overall_threshold = 18
    overall_ok        = passed >= overall_threshold and len(sensitive_leaks) == 0

    print(_bold("─── Genel sonuc ─────────────────────────────────────────"))
    print()
    print(f"  Toplam case : {total}")
    print(f"  PASS        : {passed}")
    print(f"  FAIL        : {failed}")
    if errors:
        print(_yellow(f"  Hata (exc.) : {errors}"))
    print(f"  Hassas sizinti: {len(sensitive_leaks)}")
    print()

    if overall_ok and cat_all_ok:
        print(_green(_bold("  ✓ D2.2 GECTI — Policy gecis kriterlerinin tamami saglandı.")))
        exit_code = 0
    else:
        print(_red(_bold("  ✗ D2.2 BASARISIZ — Asagidaki sorunlar giderilmeli:")))
        if passed < overall_threshold:
            print(_red(f"    - Toplam puan {passed}/{total} < esik {overall_threshold}/20"))
        if not cat_all_ok:
            for cat, thresh in cat_thresholds.items():
                info  = cats.get(cat, {"total": 0, "passed": 0})
                if info["passed"] < thresh["min_pass"]:
                    print(_red(f"    - {cat}: {info['passed']}/{info['total']} < min {thresh['min_pass']}"))
        if sensitive_leaks:
            print(_red(f"    - {len(sensitive_leaks)} hassas senaryo web'e cikti (KRITIK)"))
        print()
        print(_yellow("  Fail olan case detayi icin: --verbose ile tekrar calistir"))
        exit_code = 1

    print()
    print(_bold("═══════════════════════════════════════════════════════"))
    print()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
