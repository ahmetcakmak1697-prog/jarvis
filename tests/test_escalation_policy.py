"""
escalation_policy.decide() davranis kilidi.
Karar matrisi: PROCEED_COMMIT < REPAIR < HUMAN_GATE < HALT (en yuksek siddet kazanir).
"""
import pytest

from escalation_policy import Decision, DiffStats, PolicyConfig, Step, decide


def D(paths=None, **kw):
    return DiffStats(changed_paths=paths or [], **kw)


# --------------------------------------------------------------------------- #
# Temel yollar
# --------------------------------------------------------------------------- #

def test_clean_pass_proceeds():
    dec, _ = decide(Step("s"), "PASS", D(["jarvis/x.py"], files_changed=1), 0.1, 0)
    assert dec == Decision.PROCEED_COMMIT


def test_fail_under_max_repairs():
    dec, _ = decide(Step("s"), "FAIL", D(["jarvis/x.py"]), 0.1, 1)
    assert dec == Decision.REPAIR


def test_fail_at_max_repairs_goes_human():
    cfg = PolicyConfig(max_repair_rounds=4)
    dec, _ = decide(Step("s"), "FAIL", D(["jarvis/x.py"]), 0.1, 4, cfg)
    assert dec == Decision.HUMAN_GATE


def test_needs_human_verdict_routes_to_gate():
    dec, _ = decide(Step("s"), "NEEDS_HUMAN", D(["jarvis/x.py"]), 0.1, 0)
    assert dec == Decision.HUMAN_GATE


# --------------------------------------------------------------------------- #
# Butce / HALT onceligi
# --------------------------------------------------------------------------- #

def test_over_budget_halts_on_pass():
    cfg = PolicyConfig(budget_usd=1.0)
    dec, _ = decide(Step("s"), "PASS", D(["jarvis/x.py"], files_changed=1), 5.0, 0, cfg)
    assert dec == Decision.HALT


def test_halt_beats_fail():
    cfg = PolicyConfig(budget_usd=1.0)
    dec, reasons = decide(Step("s"), "FAIL", D(["jarvis/x.py"]), 5.0, 1, cfg)
    assert dec == Decision.HALT
    assert any("bütçe" in r.lower() or "budget" in r.lower() for r in reasons)


def test_halt_beats_human_gate():
    cfg = PolicyConfig(budget_usd=1.0)
    dec, _ = decide(Step("s"), "PASS",
                    D(["jarvis/security/auth.py"], files_changed=1), 9.9, 0, cfg)
    assert dec == Decision.HALT


# --------------------------------------------------------------------------- #
# Hassas / API / test / buyuk-diff kapilari
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("path", [
    "jarvis/privacy/redactor.py",
    "jarvis/security/keys.py",
    "jarvis/auth/login.py",
    "db/migrations/0003.py",
    "jarvis/schema/user.py",
    "config/my_secret.py",
    "jarvis/execution_policy.py",
    "jarvis/data_classifier.py",
])
def test_sensitive_globs_force_gate(path):
    dec, _ = decide(Step("s"), "PASS", D([path], files_changed=1), 0.1, 0)
    assert dec == Decision.HUMAN_GATE


@pytest.mark.parametrize("path", [
    "jarvis/api/routes.py",
    "jarvis/provider_interface.py",
    "jarvis/registry.py",
    "jarvis/contracts/provider.py",
])
def test_api_surface_forces_gate(path):
    dec, _ = decide(Step("s"), "PASS", D([path], files_changed=1), 0.1, 0)
    assert dec == Decision.HUMAN_GATE


@pytest.mark.parametrize("path", [
    "tests/test_router.py",
    "jarvis/tests/test_x.py",
    "foo_test.py",
])
def test_test_file_change_forces_gate(path):
    dec, _ = decide(Step("s"), "PASS", D([path], files_changed=1), 0.1, 0)
    assert dec == Decision.HUMAN_GATE


def test_big_diff_file_count_forces_gate():
    paths = [f"jarvis/m{i}.py" for i in range(13)]
    dec, _ = decide(Step("s"), "PASS", D(paths, files_changed=13), 0.1, 0)
    assert dec == Decision.HUMAN_GATE


def test_big_diff_deletions_force_gate():
    dec, _ = decide(Step("s"), "PASS",
                    D(["jarvis/x.py"], files_changed=1, deletions=200), 0.1, 0)
    assert dec == Decision.HUMAN_GATE


def test_source_file_deleted_forces_gate():
    dec, _ = decide(Step("s"), "PASS",
                    D(["jarvis/old.py"], files_changed=1, files_deleted=1), 0.1, 0)
    assert dec == Decision.HUMAN_GATE


# --------------------------------------------------------------------------- #
# Adim turu / yargi / dogruluk-kritik
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("kind", ["architectural", "spec", "integration"])
def test_judgment_kinds_force_gate(kind):
    dec, _ = decide(Step("s", kind=kind), "PASS",
                    D(["jarvis/x.py"], files_changed=1), 0.1, 0)
    assert dec == Decision.HUMAN_GATE


def test_human_required_autonomy_forces_gate():
    dec, _ = decide(Step("s", autonomy="human_required"), "PASS",
                    D(["jarvis/x.py"], files_changed=1), 0.1, 0)
    assert dec == Decision.HUMAN_GATE


def test_human_acceptance_criteria_force_gate():
    dec, _ = decide(Step("s", acceptance_criteria_human=["baskana sunulabilir"]),
                    "PASS", D(["jarvis/x.py"], files_changed=1), 0.1, 0)
    assert dec == Decision.HUMAN_GATE


def test_correctness_critical_forces_gate_even_on_clean_pass():
    dec, reasons = decide(Step("s", correctness_critical=True), "PASS",
                          D(["jarvis/stats/metrics.py"], files_changed=1), 0.1, 0)
    assert dec == Decision.HUMAN_GATE
    assert any("doğruluk-kritik" in r.lower() for r in reasons)


# --------------------------------------------------------------------------- #
# Cok-sebep birikimi
# --------------------------------------------------------------------------- #

def test_multiple_gate_reasons_accumulate():
    dec, reasons = decide(Step("s", correctness_critical=True), "PASS",
                          D(["jarvis/security/auth.py"], files_changed=1), 0.1, 0)
    assert dec == Decision.HUMAN_GATE
    assert len(reasons) >= 2
