"""Tests for the Privacy Level Bridge (FAZ 1B.13D, partial).

These tests lock in the correct, non-obvious mapping decisions so that
nobody "simplifies" data_class -> PRIVACY_LEVELS later via naive string
matching and silently reopens a data-leak path.
"""
import pytest

from agents.api_executor import (
    PRIVACY_LEVELS,
    SENSITIVE_PRIVACY_LEVELS,
    _DEFAULT_PROVIDERS,
)
from agents.privacy_level_bridge import data_class_to_privacy_level
from agents.provider_profiles import (
    DATA_CLASS_SET,
    EXTERNAL_FORBIDDEN_DATA_CLASSES,
    EXTERNAL_SAFE_DATA_CLASSES,
)


def test_all_data_classes_map_to_a_known_old_privacy_level():
    for dc in DATA_CLASS_SET:
        result = data_class_to_privacy_level(dc)
        assert result in PRIVACY_LEVELS, f"{dc} -> {result} not a known PRIVACY_LEVELS value"


def test_unknown_data_class_raises():
    with pytest.raises(ValueError):
        data_class_to_privacy_level("top_secret")


def test_public_maps_to_public():
    assert data_class_to_privacy_level("public") == "PUBLIC"


def test_synthetic_maps_to_public():
    assert data_class_to_privacy_level("synthetic") == "PUBLIC"


def test_redacted_maps_to_redacted_low_risk():
    assert data_class_to_privacy_level("redacted") == "REDACTED_LOW_RISK"


# --------------------------------------------------------------------------
# THE critical regression guard: raw "personal" must NEVER map to
# "PERSONAL_REDACTED". That old value means already-redacted personal
# data and is explicitly allowed for deepseek_v4_flash -- mapping our raw
# "personal" data_class onto it would silently leak raw personal data to
# an external provider, undoing EXTERNAL_FORBIDDEN_DATA_CLASSES entirely.
# --------------------------------------------------------------------------


def test_personal_does_not_map_to_personal_redacted():
    assert data_class_to_privacy_level("personal") != "PERSONAL_REDACTED"


def test_personal_maps_to_a_sensitive_old_level():
    assert data_class_to_privacy_level("personal") in SENSITIVE_PRIVACY_LEVELS


# --------------------------------------------------------------------------
# Cross-system consistency: every class our contract forbids externally
# must map to an old privacy level that the old system ALSO treats as
# sensitive; every class our contract allows externally must map to an
# old privacy level the old system does NOT treat as sensitive.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("dc", sorted(EXTERNAL_FORBIDDEN_DATA_CLASSES))
def test_forbidden_data_classes_map_to_sensitive_old_levels(dc):
    assert data_class_to_privacy_level(dc) in SENSITIVE_PRIVACY_LEVELS


@pytest.mark.parametrize("dc", sorted(EXTERNAL_SAFE_DATA_CLASSES))
def test_safe_data_classes_do_not_map_to_sensitive_old_levels(dc):
    assert data_class_to_privacy_level(dc) not in SENSITIVE_PRIVACY_LEVELS


# --------------------------------------------------------------------------
# End-to-end proof against the REAL default providers shipped today:
# every forbidden data_class, once translated, must be rejected by BOTH
# default GREEN providers' own allowed_privacy declarations.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("dc", sorted(EXTERNAL_FORBIDDEN_DATA_CLASSES))
@pytest.mark.parametrize("provider_key", ["gemini_flash_free", "deepseek_v4_flash"])
def test_forbidden_data_class_rejected_by_real_default_providers(dc, provider_key):
    old_value = data_class_to_privacy_level(dc)
    provider = _DEFAULT_PROVIDERS[provider_key]
    assert old_value not in provider.allowed_privacy, (
        f"{dc} -> {old_value} would be ALLOWED by {provider_key}, "
        "which defeats the contract's external-forbidden guarantee"
    )
