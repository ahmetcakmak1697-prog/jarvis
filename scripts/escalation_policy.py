#!/usr/bin/env python3
"""
escalation_policy.py
"GM sadece önemli şeyleri imzalar" kuralının DETERMİNİSTİK karşılığı.

Bir adım için verifier verdict'i + diff istatistiği + maliyet + ardışık hata
sayısı alır; dört karardan birini döndürür:

    PROCEED_COMMIT  -> PASS + hiçbir imza tetikleyicisi yok. Otomatik commit + sonraki adım.
    REPAIR          -> FAIL ama repair hakkı var. Maker tekrar denesin.
    HUMAN_GATE      -> İmza gerekiyor. Sebep(ler) raporlanır, loop durur, sen bakarsın.
    HALT            -> Bütçe aşıldı veya repair tükendi. Loop tamamen durur.

Tasarım ilkesi: ÖNEM bir his değil, bir kuraldır. Otonomi adım bazında
"makinece doğrulanabilirlik" ile HAK EDİLİR, global olarak VERİLMEZ.

Bu dosya hiçbir şey çalıştırmaz/commit etmez; yalnızca karar verir.
Hızlı doğrulama:  python escalation_policy.py --selftest
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Decision(str, Enum):
    PROCEED_COMMIT = "PROCEED_COMMIT"
    REPAIR = "REPAIR"
    HUMAN_GATE = "HUMAN_GATE"
    HALT = "HALT"


_SEVERITY = {Decision.PROCEED_COMMIT: 0, Decision.REPAIR: 1,
             Decision.HUMAN_GATE: 2, Decision.HALT: 3}


@dataclass
class Step:
    id: str
    kind: str = "implement"            # implement|refactor|spec|integration|architectural
    autonomy: str = "auto"             # auto|human_required
    acceptance_criteria_human: list[str] = field(default_factory=list)
    correctness_critical: bool = False


@dataclass
class DiffStats:
    files_changed: int = 0
    deletions: int = 0
    files_deleted: int = 0
    changed_paths: list[str] = field(default_factory=list)


@dataclass
class PolicyConfig:
    budget_usd: float = 5.0
    max_repair_rounds: int = 4
    # Bu glob'lara dokunan diff -> her zaman imza
    sensitive_globs: list[str] = field(default_factory=lambda: [
        "**/privacy/**", "**/security/**", "**/auth/**",
        "**/migrations/**", "**/schema/**", "**/*secret*",
        "**/execution_policy*", "**/data_classifier*",
    ])
    # Public API yüzeyi -> imza
    api_globs: list[str] = field(default_factory=lambda: [
        "**/api/**", "**/*interface*", "**/registry*", "**/contracts/**",
    ])
    # Test/spec dosyası değişimi = yargı (spec-by-test güvencesi)
    test_globs: list[str] = field(default_factory=lambda: [
        "**/tests/**", "**/test_*.py", "**/*_test.py",
    ])
    big_diff_files: int = 12           # bundan fazla dosya = geniş blast radius -> imza
    big_diff_deletions: int = 150      # bundan fazla silme -> imza
    # Bu adım türleri her zaman yargı gerektirir
    judgment_kinds: list[str] = field(default_factory=lambda: [
        "architectural", "spec", "integration",
    ])


def _touches(paths: list[str], globs: list[str]) -> list[str]:
    hit = []
    for p in paths:
        q = p.replace("\\", "/")
        for g in globs:
            if fnmatch.fnmatch(q, g) or fnmatch.fnmatch(q, g.lstrip("*/")):
                hit.append(p)
                break
    return hit


def decide(step: Step, verdict: str, diff: DiffStats,
           cost_usd: float, consecutive_failures: int,
           cfg: Optional[PolicyConfig] = None) -> tuple[Decision, list[str]]:
    cfg = cfg or PolicyConfig()
    reasons: list[str] = []
    decision = Decision.PROCEED_COMMIT  # varsayılan; aşağıdaki kurallar yükseltir

    def raise_to(d: Decision, why: str):
        nonlocal decision
        reasons.append(why)
        if _SEVERITY[d] > _SEVERITY[decision]:
            decision = d

    # 0) Bütçe en sert kısıt
    if cost_usd >= cfg.budget_usd:
        raise_to(Decision.HALT, f"Bütçe aşıldı: ${cost_usd:.2f} >= ${cfg.budget_usd:.2f}")

    # 1) Verdict FAIL -> repair veya tükenme
    if verdict == "FAIL":
        if consecutive_failures >= cfg.max_repair_rounds:
            raise_to(Decision.HUMAN_GATE,
                     f"Repair tükendi ({consecutive_failures}/{cfg.max_repair_rounds}).")
        else:
            raise_to(Decision.REPAIR,
                     f"FAIL, repair hakkı var ({consecutive_failures}/{cfg.max_repair_rounds}).")
        # FAIL durumunda diğer imza kontrolleri anlamsız; mevcut kararı döndür
        return decision, reasons

    # 2) Verifier zaten insan istedi
    if verdict == "NEEDS_HUMAN":
        raise_to(Decision.HUMAN_GATE, "Verifier NEEDS_HUMAN döndürdü.")

    # 3) Buradan sonrası: verdict == PASS. Yine de imza gerektirebilir.
    if step.kind in cfg.judgment_kinds:
        raise_to(Decision.HUMAN_GATE, f"Adım türü yargı gerektiriyor: {step.kind}.")
    if step.autonomy == "human_required":
        raise_to(Decision.HUMAN_GATE, "Adım otonomi=human_required olarak işaretli.")
    if step.acceptance_criteria_human:
        raise_to(Decision.HUMAN_GATE,
                 "Adımda makinece doğrulanamayan (insan) kabul kriteri var.")

    sens = _touches(diff.changed_paths, cfg.sensitive_globs)
    if sens:
        raise_to(Decision.HUMAN_GATE, "Hassas alan değişti: " + ", ".join(sens[:5]))
    api = _touches(diff.changed_paths, cfg.api_globs)
    if api:
        raise_to(Decision.HUMAN_GATE, "Public API yüzeyi değişti: " + ", ".join(api[:5]))
    tst = _touches(diff.changed_paths, cfg.test_globs)
    if tst:
        raise_to(Decision.HUMAN_GATE,
                 "Test/spec dosyası değişti (yargı adımı): " + ", ".join(tst[:5]))

    if diff.files_deleted > 0:
        raise_to(Decision.HUMAN_GATE, f"Kaynak dosya silindi ({diff.files_deleted} dosya).")
    if diff.files_changed > cfg.big_diff_files:
        raise_to(Decision.HUMAN_GATE,
                 f"Geniş blast radius: {diff.files_changed} dosya > {cfg.big_diff_files}.")
    if diff.deletions > cfg.big_diff_deletions:
        raise_to(Decision.HUMAN_GATE,
                 f"Çok silme: {diff.deletions} satır > {cfg.big_diff_deletions}.")

    # 4) Correctness-critical gate: testler PASS olsa bile insan imzası gerekir
    if step.correctness_critical:
        raise_to(Decision.HUMAN_GATE,
                 "Doğruluk-kritik adım (correctness_critical): deterministik testler PASS olsa "
                 "da insan imzası gereklidir.")

    if decision == Decision.PROCEED_COMMIT:
        reasons.append("PASS + imza tetikleyicisi yok -> otonom devam.")
    return decision, reasons


# --------------------------------------------------------------------------- #
# CLI / JSON arayüzü (orchestrator buradan çağırır)
# --------------------------------------------------------------------------- #

def _from_payload(data: dict) -> tuple[Step, str, DiffStats, float, int, PolicyConfig]:
    s = data.get("step", {})
    step = Step(
        id=s.get("id", "?"),
        kind=s.get("kind", "implement"),
        autonomy=s.get("autonomy", "auto"),
        acceptance_criteria_human=s.get("acceptance_criteria_human", []),
        correctness_critical=s.get("correctness_critical", False),
    )
    d = data.get("diff", {})
    diff = DiffStats(
        files_changed=d.get("files_changed", 0),
        deletions=d.get("deletions", 0),
        changed_paths=d.get("changed_paths", []),
    )
    cfg_in = data.get("config", {})
    cfg = PolicyConfig(**{k: v for k, v in cfg_in.items()
                          if k in PolicyConfig.__dataclass_fields__})
    return (step, data.get("verdict", "FAIL"), diff,
            float(data.get("cost_usd", 0.0)), int(data.get("consecutive_failures", 0)), cfg)


def _selftest() -> int:
    cfg = PolicyConfig(budget_usd=5.0, max_repair_rounds=4)
    cases = [
        # (step, verdict, diff, cost, fails) -> beklenen
        (Step("a", "implement", "auto"), "PASS",
         DiffStats(1, 3, 0, ["jarvis/util/x.py"]), 0.1, 0,
         Decision.PROCEED_COMMIT),
        (Step("b", "architectural"), "PASS", DiffStats(1, 0, 0, ["x.py"]), 0.1, 0,
         Decision.HUMAN_GATE),
        (Step("c", "implement", "auto", ["Türkçe kalite iyi olmalı"]), "PASS",
         DiffStats(1, 0, 0, ["x.py"]), 0.1, 0, Decision.HUMAN_GATE),
        (Step("d"), "PASS", DiffStats(1, 0, 0, ["jarvis/privacy/redactor.py"]), 0.1, 0,
         Decision.HUMAN_GATE),
        (Step("e"), "PASS", DiffStats(20, 0, 0, ["x.py"]), 0.1, 0, Decision.HUMAN_GATE),
        (Step("f"), "NEEDS_HUMAN", DiffStats(1, 0, 0, ["x.py"]), 0.1, 0, Decision.HUMAN_GATE),
        (Step("g"), "FAIL", DiffStats(1, 0, 0, ["x.py"]), 0.1, 1, Decision.REPAIR),
        (Step("h"), "FAIL", DiffStats(1, 0, 0, ["x.py"]), 0.1, 4, Decision.HUMAN_GATE),
        (Step("i"), "PASS", DiffStats(1, 0, 0, ["x.py"]), 9.0, 0, Decision.HALT),
        (Step("j", "implement", "auto"), "PASS",
         DiffStats(2, 0, 0, ["jarvis/x.py", "tests/test_x.py"]), 0.1, 0,
         Decision.HUMAN_GATE),  # implement adımı teste dokundu -> kapı
        (Step("k", "implement", "auto"), "PASS",
         DiffStats(1, 40, 1, ["jarvis/old.py"]), 0.1, 0,
         Decision.HUMAN_GATE),  # kaynak dosya silindi -> kapı
        (Step("l", "implement", "auto", correctness_critical=True), "PASS",
         DiffStats(1, 3, 0, ["jarvis/util/x.py"]), 0.1, 0,
         Decision.HUMAN_GATE),  # correctness_critical -> PASS olsa da kapı
    ]
    ok = True
    for step, verdict, diff, cost, fails, expected in cases:
        got, reasons = decide(step, verdict, diff, cost, fails, cfg)
        flag = "OK" if got == expected else "FAIL"
        if got != expected:
            ok = False
        print(f"[{flag}] {step.id}: {verdict} -> {got.value} (beklenen {expected.value})"
              f"  | {reasons[0] if reasons else ''}")
    print("SELFTEST:", "GEÇTİ" if ok else "BAŞARISIZ")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="JARVIS eskalasyon politikası (deterministik)")
    ap.add_argument("--payload", help="Karar girdisi JSON yolu (yoksa STDIN)")
    ap.add_argument("--selftest", action="store_true", help="Kuralları test et ve çık")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    raw = (open(args.payload, encoding="utf-8").read() if args.payload
           else sys.stdin.read())
    step, verdict, diff, cost, fails, cfg = _from_payload(json.loads(raw))
    decision, reasons = decide(step, verdict, diff, cost, fails, cfg)
    print(json.dumps({"decision": decision.value, "reasons": reasons},
                     ensure_ascii=False, indent=2))
    # çıkış kodu orchestrator için: 0=proceed,1=repair,2=human,3=halt
    return {"PROCEED_COMMIT": 0, "REPAIR": 1, "HUMAN_GATE": 2, "HALT": 3}[decision.value]


if __name__ == "__main__":
    raise SystemExit(main())
