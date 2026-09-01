"""Tests for the Provider Decision Adapter (FAZ 1B.13C).

Decision dict fixtures below mirror the EXACT shapes produced by
agents/execution_policy.py's ExecutionPolicy.choose(), so these tests
double as documentation of the real integration contract.
"""
from pathlib import Path

import pytest

from agents.provider_decision import GATED_DESTINATIONS, resolve_provider
from agents.provider_profiles import load_provider_profiles
from agents.provider_selector import ProviderSelector

EXAMPLE_CONFIG = (
    Path(__file__).resolve().parents[1] / "config" / "provider_profiles.example.json"
)


@pytest.fixture
def selector() -> ProviderSelector:
    return ProviderSelector(load_provider_profiles(EXAMPLE_CONFIG))


# --------------------------------------------------------------------------
# Realistic decision dict fixtures (mirrors ExecutionPolicy.choose() output)
# --------------------------------------------------------------------------


def _local_answer_decision() -> dict:
    return {
        "level": "L0",
        "destination": "local_answer",
        "primary_executor": None,
        "fallback_executor": None,
        "requires_approval": False,
        "reason": "router_local_answer",
    }


def _blocked_decision() -> dict:
    return {
        "level": "L2",
        "destination": "blocked",
        "primary_executor": None,
        "fallback_executor": None,
        "requires_approval": False,
        "reason": "redacted_blocked",
    }


def _no_execution_decision() -> dict:
    return {
        "level": "L2",
        "destination": "no_execution",
        "primary_executor": None,
        "fallback_executor": None,
        "requires_approval": False,
        "reason": "unknown_router_decision",
    }


def _local_decision() -> dict:
    return {
        "level": "L2",
        "destination": "local",
        "primary_executor": "ollama",
        "fallback_executor": None,
        "requires_approval": False,
        "reason": "local_first_default",
    }


def _cloud_api_decision(level: str = "L3") -> dict:
    return {
        "level": level,
        "destination": "cloud_api",
        "primary_executor": "api",
        "fallback_executor": "ollama",
        "requires_approval": False,
        "reason": "cloud_api_enabled_for_level",
    }


def _premium_gate_decision() -> dict:
    return {
        "level": "L4",
        "destination": "premium_gate",
        "primary_executor": None,
        "fallback_executor": "ollama",
        "requires_approval": True,
        "reason": "premium_level_requires_approval",
    }


# --------------------------------------------------------------------------
# Passthrough destinations: no provider needed, decision unchanged
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "make_decision",
    [_local_answer_decision, _blocked_decision, _no_execution_decision, _local_decision],
)
def test_passthrough_destinations_get_provider_id_none(selector, make_decision):
    original = make_decision()
    result = resolve_provider(original, data_class="public", selector=selector)
    assert result["provider_id"] is None
    # everything else from the original decision must be preserved as-is
    for key, value in original.items():
        assert result[key] == value


def test_input_decision_dict_is_never_mutated(selector):
    original = _local_decision()
    snapshot = dict(original)
    resolve_provider(original, data_class="public", selector=selector)
    assert original == snapshot
    assert "provider_id" not in original


# --------------------------------------------------------------------------
# cloud_api: today, automatic resolution always degrades (no provider is
# default_enabled=True for external) -- this is the intentional finding.
# --------------------------------------------------------------------------


def test_cloud_api_without_explicit_provider_degrades_gracefully(selector):
    decision = _cloud_api_decision(level="L3")
    result = resolve_provider(decision, data_class="public", selector=selector)
    assert result["provider_id"] is None
    assert "provider_resolution_error" in result
    # destination/primary_executor are left untouched per the 13D contract
    assert result["destination"] == "cloud_api"
    assert result["primary_executor"] == "api"
    assert result["fallback_executor"] == "ollama"


def test_cloud_api_with_explicit_provider_resolves(selector):
    decision = _cloud_api_decision(level="L3")
    result = resolve_provider(
        decision,
        data_class="redacted",
        selector=selector,
        explicit_provider_id="deepseek_v4_flash",
    )
    assert result["provider_id"] == "deepseek_v4_flash"
    assert result["provider_model"] == "deepseek/deepseek-chat"
    assert result["provider_env_key"] == "DEEPSEEK_API_KEY"
    assert result["provider_timeout_s"] == 30.0


def test_cloud_api_explicit_provider_cannot_leak_sensitive_data(selector):
    # Even an explicit escalation request must respect the data_class
    # safety invariant inherited from ProviderSelector.
    decision = _cloud_api_decision(level="L3")
    result = resolve_provider(
        decision,
        data_class="institution_internal",
        selector=selector,
        explicit_provider_id="deepseek_v4_flash",
    )
    assert result["provider_id"] is None
    assert "provider_resolution_error" in result


def test_requires_approval_is_or_combined_with_provider_budget_gate(selector):
    # cloud_api's own requires_approval defaults to False, but
    # deepseek_v4_flash.requires_budget_gate is always True (contract
    # enforced for every external provider) -- the combined result must
    # be True.
    decision = _cloud_api_decision(level="L3")
    assert decision["requires_approval"] is False
    result = resolve_provider(
        decision,
        data_class="public",
        selector=selector,
        explicit_provider_id="deepseek_v4_flash",
    )
    assert result["requires_approval"] is True


# --------------------------------------------------------------------------
# premium_gate: today, no provider declares L4 in the example config, so
# resolution degrades too -- but the existing approval gate is untouched.
# --------------------------------------------------------------------------


def test_premium_gate_degrades_when_no_l4_provider_configured(selector):
    decision = _premium_gate_decision()
    result = resolve_provider(decision, data_class="public", selector=selector)
    assert result["provider_id"] is None
    assert "provider_resolution_error" in result
    # the human-approval gate from ExecutionPolicy must remain intact
    assert result["requires_approval"] is True
    assert result["destination"] == "premium_gate"
    assert result["fallback_executor"] == "ollama"


# --------------------------------------------------------------------------
# Constants sanity
# --------------------------------------------------------------------------


def test_gated_destinations_constant():
    assert GATED_DESTINATIONS == frozenset({"cloud_api", "premium_gate"})
