"""Tests for the Provider Profile Contract (FAZ 1B.13A).

Covers the stated acceptance criteria plus the extra fail-closed security
holes identified during review. No router integration, no API calls.
"""
import copy
import json
from pathlib import Path

import pytest

from agents.provider_profiles import (
    EXTERNAL_SAFE_DATA_CLASSES,
    ProviderProfile,
    ProviderProfileError,
    ProviderProfileRegistry,
    load_provider_profiles,
    validate_profile,
)

EXAMPLE_CONFIG = (
    Path(__file__).resolve().parents[1] / "config" / "provider_profiles.example.json"
)


# --------------------------------------------------------------------------
# Builders for valid baseline profiles (mutate to produce invalid cases).
# --------------------------------------------------------------------------


def _deepseek() -> dict:
    return {
        "provider_id": "deepseek_v4_flash",
        "executor_key": "api",
        "model": "deepseek/deepseek-chat",
        "status": "verified",
        "cost_tier": "cheap",
        "billing_mode": "token_balance",
        "allowed_levels": ["L3"],
        "allowed_data_classes": ["public", "redacted", "synthetic"],
        "default_enabled": False,
        "requires_budget_gate": True,
        "requires_smoke_pass": True,
        "env_key": "DEEPSEEK_API_KEY",
        "timeout_s": 30,
    }


def _ollama() -> dict:
    return {
        "provider_id": "ollama_local",
        "executor_key": "ollama",
        "model": "llama3.1",
        "status": "verified",
        "cost_tier": "local_free",
        "billing_mode": "hardware",
        "allowed_levels": ["L1", "L2", "L3"],
        "allowed_data_classes": [
            "public",
            "synthetic",
            "redacted",
            "personal",
            "sensitive",
            "institution_internal",
        ],
        "default_enabled": True,
        "requires_budget_gate": False,
        "requires_smoke_pass": False,
        "timeout_s": 60,
    }


def _write(tmp_path: Path, providers: list[dict], schema_version: str = "1.0") -> Path:
    cfg = {"schema_version": schema_version, "providers": providers}
    path = tmp_path / "provider_profiles.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Acceptance criteria
# --------------------------------------------------------------------------


def test_example_config_loads():
    reg = load_provider_profiles(EXAMPLE_CONFIG)
    assert isinstance(reg, ProviderProfileRegistry)
    assert len(reg) == 2
    assert "deepseek_v4_flash" in reg
    assert "ollama_local" in reg


def test_deepseek_profile_fields():
    p = validate_profile(_deepseek())
    assert isinstance(p, ProviderProfile)
    assert p.executor_key == "api"
    assert p.model == "deepseek/deepseek-chat"
    assert p.status == "verified"
    assert p.cost_tier == "cheap"
    assert p.billing_mode == "token_balance"
    assert p.allowed_levels == ("L3",)
    assert p.allowed_data_classes == ("public", "redacted", "synthetic")
    assert p.default_enabled is False
    assert p.requires_budget_gate is True
    assert p.requires_smoke_pass is True
    assert p.env_key == "DEEPSEEK_API_KEY"
    assert p.is_external is True
    assert p.is_local is False


def test_ollama_profile_fields():
    p = validate_profile(_ollama())
    assert p.executor_key == "ollama"
    assert p.cost_tier == "local_free"
    assert p.billing_mode == "hardware"
    assert "institution_internal" in p.allowed_data_classes
    assert p.default_enabled is True
    assert p.requires_budget_gate is False
    assert p.is_local is True
    assert p.env_key is None


def test_duplicate_provider_id_rejected(tmp_path):
    with pytest.raises(ProviderProfileError):
        load_provider_profiles(_write(tmp_path, [_deepseek(), _deepseek()]))


def test_missing_required_field_rejected():
    raw = _deepseek()
    del raw["model"]
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_invalid_level_rejected():
    raw = _deepseek()
    raw["allowed_levels"] = ["L3", "L99"]
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


@pytest.mark.parametrize("beyond", ["L5", "L6", "L7"])
def test_levels_beyond_l4_rejected(beyond):
    # Contract is narrowed to L0-L4; L5-L7 are not yet a production contract.
    raw = _deepseek()
    raw["allowed_levels"] = [beyond]
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_invalid_data_class_rejected():
    raw = _deepseek()
    raw["allowed_data_classes"] = ["public", "top_secret"]
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


@pytest.mark.parametrize("forbidden", ["institution_internal", "personal", "sensitive"])
def test_external_forbidden_data_class_rejected(forbidden):
    raw = _deepseek()
    raw["allowed_data_classes"] = ["public", forbidden]
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_api_executor_without_env_key_rejected():
    raw = _deepseek()
    del raw["env_key"]
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_external_requires_budget_gate_false_rejected():
    raw = _deepseek()
    raw["requires_budget_gate"] = False
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_external_default_enabled_true_rejected():
    raw = _deepseek()
    raw["default_enabled"] = True
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_timeout_zero_or_negative_rejected():
    for bad in (0, -5):
        raw = _deepseek()
        raw["timeout_s"] = bad
        with pytest.raises(ProviderProfileError):
            validate_profile(raw)


# --------------------------------------------------------------------------
# Extra fail-closed security holes (beyond the stated list)
# --------------------------------------------------------------------------


def test_unknown_field_rejected():
    raw = _deepseek()
    raw["allowed_data_class"] = ["public"]  # typo of the real field
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_empty_data_classes_rejected():
    raw = _deepseek()
    raw["allowed_data_classes"] = []
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_empty_levels_rejected():
    raw = _deepseek()
    raw["allowed_levels"] = []
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_duplicate_within_data_classes_rejected():
    raw = _deepseek()
    raw["allowed_data_classes"] = ["public", "public"]
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_non_bool_default_enabled_rejected():
    raw = _deepseek()
    raw["default_enabled"] = "false"  # string, not bool
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_int_as_bool_rejected():
    raw = _deepseek()
    raw["requires_budget_gate"] = 1  # int truthy, not bool
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_timeout_as_bool_rejected():
    raw = _deepseek()
    raw["timeout_s"] = True  # bool is not a valid number here
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_timeout_above_max_rejected():
    raw = _deepseek()
    raw["timeout_s"] = 999999
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_env_key_on_local_rejected():
    raw = _ollama()
    raw["env_key"] = "SOME_KEY"
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_external_requires_smoke_pass_false_rejected():
    raw = _deepseek()
    raw["requires_smoke_pass"] = False
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_default_enabled_requires_verified_status():
    raw = _ollama()
    raw["status"] = "experimental"  # but default_enabled is True
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_case_sensitive_level_rejected():
    raw = _deepseek()
    raw["allowed_levels"] = ["l3"]  # lowercase
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_level_with_whitespace_rejected():
    raw = _deepseek()
    raw["allowed_levels"] = ["L3 "]  # trailing space
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_bad_provider_id_rejected():
    for bad in ("DeepSeek", "deep seek", "deep-seek", ""):
        raw = _deepseek()
        raw["provider_id"] = bad
        with pytest.raises(ProviderProfileError):
            validate_profile(raw)


def test_invalid_status_rejected():
    raw = _deepseek()
    raw["status"] = "production"
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_invalid_cost_tier_rejected():
    raw = _deepseek()
    raw["cost_tier"] = "free"
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


def test_invalid_billing_mode_rejected():
    raw = _deepseek()
    raw["billing_mode"] = "credit_card"
    with pytest.raises(ProviderProfileError):
        validate_profile(raw)


# --------------------------------------------------------------------------
# Config-level (top-level) validation
# --------------------------------------------------------------------------


def test_missing_file_rejected(tmp_path):
    with pytest.raises(ProviderProfileError):
        load_provider_profiles(tmp_path / "nope.json")


def test_malformed_json_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ this is not json", encoding="utf-8")
    with pytest.raises(ProviderProfileError):
        load_provider_profiles(path)


def test_wrong_schema_version_rejected(tmp_path):
    with pytest.raises(ProviderProfileError):
        load_provider_profiles(_write(tmp_path, [_deepseek()], schema_version="2.0"))


def test_unknown_top_level_key_rejected(tmp_path):
    cfg = {"schema_version": "1.0", "providers": [_deepseek()], "evil": True}
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(ProviderProfileError):
        load_provider_profiles(path)


def test_empty_providers_rejected(tmp_path):
    with pytest.raises(ProviderProfileError):
        load_provider_profiles(_write(tmp_path, []))


def test_registry_helpers(tmp_path):
    reg = load_provider_profiles(_write(tmp_path, [_deepseek(), _ollama()]))
    assert len(reg.external()) == 1
    assert len(reg.local()) == 1
    assert reg.external()[0].provider_id == "deepseek_v4_flash"
    assert len(reg.enabled()) == 1  # only ollama_local default_enabled
    assert reg.require("ollama_local").is_local
    with pytest.raises(ProviderProfileError):
        reg.require("ghost")
