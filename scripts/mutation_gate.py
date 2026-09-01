#!/usr/bin/env python3
"""
mutation_gate.py
AKADEMİK ANTİ-TEST-GAMING KAPISI (deterministik, LLM yok).

Fikir: kaynağa küçük ama anlam-bozan mutasyonlar enjekte et (==/!=, </>=, and/or,
True/False ...). Her mutant için ilgili testleri koştur:
    test FAIL eder  -> mutant "öldürüldü" (testler bug'ı yakaladı = iyi)
    test PASS eder  -> mutant "hayatta kaldı" (testler bu bug'ı kaçırdı = zayıf test)
Mutation skoru = öldürülen / çalıştırılan. Eşik altında -> FAIL.

Bu, "kodu testten geçecek şekilde yaz" oyununu kıran tek deterministik araç:
testlerin gerçekten doğruladığını ölçer, sadece yeşil olduğunu değil.
Outcome Contract'ta matematiksel/istatistiksel kritik adımlarda zorunlu olmalı.

Kullanım:
    python mutation_gate.py --source jarvis/stats/metrics.py \
        --test-cmd "py -3.11 -m pytest tests/test_metrics.py -q" \
        --threshold 0.8
Çıkış: 0 = skor >= eşik (PASS), 1 = altında (FAIL).
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

_CMP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt,
        ast.Gt: ast.LtE, ast.LtE: ast.Gt, ast.Is: ast.IsNot, ast.IsNot: ast.Is,
        ast.In: ast.NotIn, ast.NotIn: ast.In}
_BOOL = {ast.And: ast.Or, ast.Or: ast.And}


def _count(tree: ast.AST) -> int:
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and type(node.ops[0]) in _CMP:
            n += 1
        elif isinstance(node, ast.BoolOp):
            n += 1
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            n += 1
    return n


class _Mutator(ast.NodeTransformer):
    """target'inci mutatable node'u (deterministik sırayla) tek bir mutasyonla değiştirir."""

    def __init__(self, target: int):
        self.target = target
        self.i = -1
        self.applied: str | None = None

    def _hit(self) -> bool:
        self.i += 1
        return self.i == self.target

    def visit_Compare(self, node):
        if type(node.ops[0]) in _CMP:
            if self._hit():
                old = type(node.ops[0])
                node.ops[0] = _CMP[old]()
                self.applied = f"karşılaştırma {old.__name__}->{type(node.ops[0]).__name__} @satır {node.lineno}"
        self.generic_visit(node)
        return node

    def visit_BoolOp(self, node):
        if self._hit():
            old = type(node.op)
            node.op = _BOOL[old]()
            self.applied = f"mantık {old.__name__}->{type(node.op).__name__} @satır {node.lineno}"
        self.generic_visit(node)
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, bool):
            if self._hit():
                old = node.value
                node.value = not node.value
                self.applied = f"sabit {old}->{node.value} @satır {node.lineno}"
        return node


def run_gate(source: str, test_cmd: str, threshold: float,
             max_mutants: int, timeout: int = 120) -> tuple[float, list[str], int]:
    path = Path(source)
    original = path.read_text(encoding="utf-8")
    tree = ast.parse(original)
    total = _count(tree)
    if total == 0:
        return 1.0, [], 0  # mutasyon hedefi yok -> nötr (gate'i geçir)

    targets = list(range(total))
    if max_mutants and total > max_mutants:  # deterministik eşit-aralık örnekleme
        stepf = total / max_mutants
        targets = sorted({int(k * stepf) for k in range(max_mutants)})

    killed, ran, survivors = 0, 0, []
    try:
        for t in targets:
            mtree = ast.parse(original)
            m = _Mutator(t)
            m.visit(mtree)
            if m.applied is None:
                continue
            ast.fix_missing_locations(mtree)
            try:
                mutated = ast.unparse(mtree)
            except Exception:  # noqa: BLE001
                continue
            path.write_text(mutated, encoding="utf-8")
            ran += 1
            try:
                cp = subprocess.run(test_cmd, shell=True, capture_output=True,
                                    text=True, timeout=timeout)
                if cp.returncode != 0:
                    killed += 1            # testler bug'ı yakaladı
                else:
                    survivors.append(m.applied)  # testler kaçırdı
            except subprocess.TimeoutExpired:
                killed += 1                # mutasyon takılmaya yol açtı = tespit edildi
    finally:
        path.write_text(original, encoding="utf-8")  # her zaman geri yükle (hata dahil)

    score = killed / ran if ran else 1.0
    return score, survivors, ran


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Mutation testing kapısı (anti-test-gaming)")
    ap.add_argument("--source", required=True, help="Mutasyona uğratılacak kaynak dosya")
    ap.add_argument("--test-cmd", required=True, help="İlgili testleri koşan komut (shell)")
    ap.add_argument("--threshold", type=float, default=0.8, help="Min mutation skoru (0-1)")
    ap.add_argument("--max-mutants", type=int, default=40, help="Çalışma süresi sınırı")
    ap.add_argument("--timeout", type=int, default=120, help="Mutant başına test timeout (sn)")
    args = ap.parse_args(argv)

    if not Path(args.source).exists():
        print(f"HATA: kaynak yok: {args.source}")
        return 1
    score, survivors, ran = run_gate(args.source, args.test_cmd, args.threshold,
                                     args.max_mutants, args.timeout)
    print(f"# Mutation Gate -- {args.source}")
    print(f"Skor: {score:.2f}  (çalıştırılan {ran}, hayatta kalan {len(survivors)}, eşik {args.threshold})")
    if survivors:
        print("Hayatta kalan mutantlar (testlerin KAÇIRDIĞI bozulmalar -> zayıf nokta):")
        for s in survivors[:20]:
            print(f"  - {s}")
    ok = score >= args.threshold
    print("SONUÇ:", "PASS" if ok else "FAIL (testler yetersiz; gerçek bug'ları kaçırabilir)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
