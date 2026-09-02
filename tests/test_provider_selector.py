"""Tests for ProviderSelector (FAZ 1B.13B).

No router integration, no API calls. Pure selection logic against the
ProviderProfileRegistry built from FAZ 1B.13A.
"""
from pathlib import Path

import pytest

from agents.provider_profiles import (
    ProviderProfile,
    ProviderProfileRegistry,
    load_provider_profiles,
    validate_profile,
)
from agents.provider_selector import (
    EXPERIMENTAL_DATA_CLASSES,
    ProviderSelectionError,
    ProviderSelector,
    SelectionRequest,
)

EXAMPLE_CONFIG = (
    Path(__file__).resolve().parents[1] / "config" / "provider_profiles.example.json"
)


@pytest.fixture
def example_registry() -> ProviderProfileRegistry:
    return load_provider_profiles(EXAMPLE_CONFIG)


@pytest.fixture
def selector(example_registry) -> ProviderSelector:
    return ProviderSelector(example_registry)


# --------------------------------------------------------------------------
# Automatic selection against the real shipped example config
# --------------------------------------------------------------------------


def test_automatic_selection_picks_local_for_public_l3(selector):
    # deepseek_v4_flash is default_enabled=False, so it never appears in
    # automatic selection. Only ollama_local qualifies.
    p = selector.select(SelectionRequest(level="L3", data_class="public"))
    assert p.provider_id == "ollama_local"


def test_automatic_selection_rejects_sensitive_data_for_external(selector):
    # Even explicitly asking for an external provider, automatic selection
    # must fail closed for institution_internal: no external provider may
    # ever carry it, so there is no candidate at all.
    with pytest.raises(ProviderSelectionError):
        selector.select(
            SelectionRequest(
                level="L3",
                data_class="institution_internal",
                require_external=True,
            )
        )


def test_automatic_selection_no_candidates_when_excluded(selector):
    with pytest.raises(ProviderSelectionError) as exc:
        selector.select(
            SelectionRequest(
                level="L3", data_class="public", exclude=frozenset({"ollama_local"})
            )
        )
    assert "excluded" in str(exc.value)


# --------------------------------------------------------------------------
# Explicit selection: the intentional escalation path
# --------------------------------------------------------------------------


def test_explicit_selection_can_use_disabled_provider(selector):
    # deepseek_v4_flash is default_enabled=False but CAN be reached via an
    # explicit, audited request -- this is how a future budget-gated
    # escalation will work.
    p = selector.select(
        SelectionRequest(
            level="L3",
            data_class="redacted",
            explicit_provider_id="deepseek_v4_flash",
        )
    )
    assert p.provider_id == "deepseek_v4_flash"


def test_explicit_selection_cannot_leak_sensitive_data(selector):
    # CRITICAL SECURITY TEST: explicit selection must never bypass the
    # data_class safety invariant, even when the caller deliberately names
    # the provider.
    with pytest.raises(ProviderSelectionError):
        selector.select(
            SelectionRequest(
                level="L3",
                data_class="institution_internal",
                explicit_provider_id="deepseek_v4_flash",
            )
        )


def test_explicit_selection_unknown_provider_rejected(selector):
    with pytest.raises(ProviderSelectionError):
        selector.select(
            SelectionRequest(
                level="L3", data_class="public", explicit_provider_id="ghost"
            )
        )


def test_explicit_selection_excluded_provider_rejected(selector):
    with pytest.raises(ProviderSelectionError):
        selector.select(
            SelectionRequest(
                level="L3",
                data_class="public",
                explicit_provider_id="deepseek_v4_flash",
                exclude=frozenset({"deepseek_v4_flash"}),
            )
        )


def test_explicit_selection_require_external_mismatch_rejected(selector):
    with pytest.raises(ProviderSelectionError):
        selector.select(
            SelectionRequest(
                level="L3",
                data_class="public",
                explicit_provider_id="ollama_local",
                require_external=True,
            )
        )


def test_explicit_selection_require_local_mismatch_rejected(selector):
    with pytest.raises(ProviderSelectionError):
        selector.select(
            SelectionRequest(
                level="L3",
                data_class="public",
                explicit_provider_id="deepseek_v4_flash",
                require_external=False,
            )
        )


def test_explicit_selection_level_mismatch_rejected(selector):
    # deepseek_v4_flash only declares allowed_levels = ["L3"]
    with pytest.raises(ProviderSelectionError):
        selector.select(
            SelectionRequest(
                level="L1",
                data_class="public",
                explicit_provider_id="deepseek_v4_flash",
            )
        )


# --------------------------------------------------------------------------
# Malformed request rejection
# --------------------------------------------------------------------------


def test_invalid_level_rejected(selector):
    with pytest.raises(ProviderSelectionError):
        selector.select(SelectionRequest(level="L9", data_class="public"))


def test_invalid_data_class_rejected(selector):
    with pytest.raises(ProviderSelectionError):
        selector.select(SelectionRequest(level="L3", data_class="top_secret"))


# --------------------------------------------------------------------------
# Tie-break behaviour with a synthetic multi-candidate registry
# --------------------------------------------------------------------------


def _local_profile(provider_id: str, cost_tier: str = "local_free") -> dict:
    return {
        "provider_id": provider_id,
        "executor_key": "ollama",
        "model": "m",
        "status": "verified",
        "cost_tier": cost_tier,
        "billing_mode": "hardware",
        "allowed_levels": ["L1", "L2", "L3"],
        "allowed_data_classes": ["public", "redacted"],
        "default_enabled": True,
        "requires_budget_gate": False,
        "requires_smoke_pass": False,
        "timeout_s": 10,
    }


def _registry(*raw_profiles: dict) -> ProviderProfileRegistry:
    return ProviderProfileRegistry([validate_profile(r) for r in raw_profiles])


def test_prefer_order_overrides_default_tiebreak():
    # Same cost_tier -> default tie-break is alphabetical provider_id,
    # which would pick "p_a". prefer_order must override that.
    reg = _registry(_local_profile("p_a"), _local_profile("p_b"))
    sel = ProviderSelector(reg)
    p = sel.select(
        SelectionRequest(
            level="L2", data_class="public", prefer_order=("p_b",)
        )
    )
    assert p.provider_id == "p_b"


def test_default_tiebreak_is_alphabetical_when_cost_tier_equal():
    reg = _registry(_local_profile("p_a"), _local_profile("p_b"))
    sel = ProviderSelector(reg)
    p = sel.select(SelectionRequest(level="L2", data_class="public"))
    assert p.provider_id == "p_a"


def test_cost_tier_rank_dominates_over_alphabetical_order():
    # Deliberately reversed alphabetical/cost ordering: "aa_cheap" would
    # win alphabetically but must lose because its cost_tier rank is
    # higher (worse) than "zz_local"'s local_free rank.
    reg = _registry(
        _local_profile("aa_cheap", cost_tier="cheap"),
        _local_profile("zz_local", cost_tier="local_free"),
    )
    sel = ProviderSelector(reg)
    p = sel.select(SelectionRequest(level="L2", data_class="public"))
    assert p.provider_id == "zz_local"


def test_require_external_false_filters_to_local_only():
    reg = _registry(_local_profile("only_local"))
    sel = ProviderSelector(reg)
    p = sel.select(
        SelectionRequest(
            level="L2", data_class="public", require_external=False
        )
    )
    assert p.provider_id == "only_local"


# --------------------------------------------------------------------------
# Status policy (GPT review hardening): deprecated/unverified never
# selectable; experimental only via explicit + public/synthetic ceiling.
# --------------------------------------------------------------------------


def _status_profile(provider_id: str, status: str, data_classes=("public", "redacted")) -> dict:
    # default_enabled must be False here: the contract layer itself forbids
    # default_enabled=True for any status other than "verified".
    return {
        "provider_id": provider_id,
        "executor_key": "ollama",
        "model": "m",
        "status": status,
        "cost_tier": "local_free",
        "billing_mode": "hardware",
        "allowed_levels": ["L1", "L2", "L3"],
        "allowed_data_classes": list(data_classes),
        "default_enabled": False,
        "requires_budget_gate": False,
        "requires_smoke_pass": False,
        "timeout_s": 10,
    }


def test_explicit_deprecated_provider_never_selectable():
    reg = _registry(_status_profile("old_one", "deprecated"))
    sel = ProviderSelector(reg)
    with pytest.raises(ProviderSelectionError):
        sel.select(
            SelectionRequest(
                level="L2", data_class="public", explicit_provider_id="old_one"
            )
        )


def test_explicit_unverified_provider_never_selectable():
    reg = _registry(_status_profile("new_one", "unverified"))
    sel = ProviderSelector(reg)
    with pytest.raises(ProviderSelectionError):
        sel.select(
            SelectionRequest(
                level="L2", data_class="public", explicit_provider_id="new_one"
            )
        )


@pytest.mark.parametrize("allowed_class", sorted(EXPERIMENTAL_DATA_CLASSES))
def test_explicit_experimental_provider_allowed_for_public_or_synthetic(allowed_class):
    reg = _registry(
        _status_profile(
            "exp_one", "experimental", data_classes=("public", "redacted", "synthetic")
        )
    )
    sel = ProviderSelector(reg)
    p = sel.select(
        SelectionRequest(
            level="L2", data_class=allowed_class, explicit_provider_id="exp_one"
        )
    )
    assert p.provider_id == "exp_one"


def test_explicit_experimental_provider_rejected_for_redacted_even_if_declared():
    # The profile itself declares "redacted" as allowed, but the selector
    # imposes an extra ceiling on experimental providers regardless.
    reg = _registry(
        _status_profile(
            "exp_one", "experimental", data_classes=("public", "redacted", "synthetic")
        )
    )
    sel = ProviderSelector(reg)
    with pytest.raises(ProviderSelectionError):
        sel.select(
            SelectionRequest(
                level="L2", data_class="redacted", explicit_provider_id="exp_one"
            )
        )


def test_automatic_defense_in_depth_status_check_bypassing_contract():
    # Construct a ProviderProfile directly (bypassing validate_profile's
    # default_enabled<->verified coupling) to prove the selector does NOT
    # blindly trust default_enabled alone for automatic selection.
    sketchy = ProviderProfile(
        provider_id="sketchy",
        executor_key="ollama",
        model="m",
        status="experimental",
        cost_tier="local_free",
        billing_mode="hardware",
        allowed_levels=("L1", "L2", "L3"),
        allowed_data_classes=("public",),
        default_enabled=True,
        requires_budget_gate=False,
        requires_smoke_pass=False,
        timeout_s=10.0,
        env_key=None,
    )
    reg = ProviderProfileRegistry([sketchy])
    sel = ProviderSelector(reg)
    with pytest.raises(ProviderSelectionError):
        sel.select(SelectionRequest(level="L2", data_class="public"))


# --------------------------------------------------------------------------
# prefer_order typo guard (GPT review hardening)
# --------------------------------------------------------------------------


def test_prefer_order_unknown_provider_rejected():
    reg = _registry(_local_profile("p_a"))
    sel = ProviderSelector(reg)
    with pytest.raises(ProviderSelectionError):
        sel.select(
            SelectionRequest(
                level="L2", data_class="public", prefer_order=("typo_id",)
            )
        )


def test_prefer_order_known_but_excluded_provider_falls_through():
    # p_a is a known provider_id (no typo) but excluded from this request;
    # this must NOT raise -- it should simply fall through to p_b.
    reg = _registry(_local_profile("p_a"), _local_profile("p_b"))
    sel = ProviderSelector(reg)
    p = sel.select(
        SelectionRequest(
            level="L2",
            data_class="public",
            exclude=frozenset({"p_a"}),
            prefer_order=("p_a", "p_b"),
        )
    )
    assert p.provider_id == "p_b"
