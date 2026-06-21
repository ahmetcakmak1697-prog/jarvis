"""
mutation_gate.run_gate davranis kilidi.
Gercek pytest alt-sureci ile: zayif test -> survivor, guclu test -> skor 1.0.
"""
import subprocess
import sys
import textwrap

import pytest

from mutation_gate import run_gate

SRC = textwrap.dedent("""
    def grade(score):
        passed = score >= 50 and score <= 100
        return passed
""")

# Zayif: yalniz orta deger -> and/or ayni sonucu verir, mutant kacar.
WEAK_TEST = textwrap.dedent("""
    import os, sys
    sys.path.insert(0, os.path.dirname(__file__))
    from srcmod import grade
    def test_mid():
        assert grade(75) is True
""")

# Guclu: dusuk skor da test edilir -> and->or mutanti yakalanir.
STRONG_TEST = textwrap.dedent("""
    import os, sys
    sys.path.insert(0, os.path.dirname(__file__))
    from srcmod import grade
    def test_mid():
        assert grade(75) is True
    def test_low():
        assert grade(40) is False
    def test_high():
        assert grade(120) is False
""")


def _setup(tmp_path, src, test_src):
    (tmp_path / "srcmod.py").write_text(src, encoding="utf-8")
    (tmp_path / "test_srcmod.py").write_text(test_src, encoding="utf-8")
    src_path = str(tmp_path / "srcmod.py")
    test_cmd = f'"{sys.executable}" -m pytest "{tmp_path / "test_srcmod.py"}" -q'
    return src_path, test_cmd


def test_weak_tests_leave_survivor(tmp_path):
    src_path, test_cmd = _setup(tmp_path, SRC, WEAK_TEST)
    score, survivors, ran = run_gate(src_path, test_cmd, threshold=0.8, max_mutants=0)
    assert ran >= 3
    assert score < 0.8
    assert survivors
    assert any("And" in s or "Or" in s for s in survivors)


def test_strong_tests_kill_all(tmp_path):
    src_path, test_cmd = _setup(tmp_path, SRC, STRONG_TEST)
    score, survivors, ran = run_gate(src_path, test_cmd, threshold=0.8, max_mutants=0)
    assert score == pytest.approx(1.0)
    assert survivors == []


def test_zero_targets_is_neutral(tmp_path):
    src = "def f(x):\n    return x + 1\n"
    src_path, test_cmd = _setup(tmp_path, src, "def test_noop():\n    assert True\n")
    score, survivors, ran = run_gate(src_path, test_cmd, threshold=0.8, max_mutants=0)
    assert (score, survivors, ran) == (1.0, [], 0)


def test_source_restored_after_run(tmp_path):
    src_path, test_cmd = _setup(tmp_path, SRC, STRONG_TEST)
    before = open(src_path, encoding="utf-8").read()
    run_gate(src_path, test_cmd, threshold=0.8, max_mutants=0)
    after = open(src_path, encoding="utf-8").read()
    assert before == after


def test_timeout_counts_as_killed(tmp_path):
    src = "def f(n):\n    return n > 0\n"
    src_path, _ = _setup(tmp_path, src, "def test_x():\n    assert True\n")
    slow_cmd = f'"{sys.executable}" -c "import time; time.sleep(5)"'
    score, survivors, ran = run_gate(src_path, slow_cmd, threshold=0.8,
                                     max_mutants=0, timeout=1)
    assert ran == 1
    assert survivors == []
    assert score == pytest.approx(1.0)
