"""Provider Profile Contract (FAZ 1B.13A).

Strict, fail-closed validation of provider identity cards loaded from JSON.

SCOPE (intentionally narrow):
  * Contract / schema / config validation ONLY.
  * NO router integration.
  * NO API calls.
  * NO provider selection logic (that is a later phase: ProviderSelector).

SECURITY STANCE: fail-closed.
  Anything ambiguous, unknown, or malformed is REJECTED, never silently
  accepted. A typo in a security-critical field (e.g. allowed_data_classes)
  must NOT fail open and let sensitive data reach an external provider.

All error messages are ASCII-only on purpose (transport/encoding safety).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

# --------------------------------------------------------------------------
# Allowed value sets (enums). Exact-match, case-sensitive.
# --------------------------------------------------------------------------

EXECUTOR_KEYS = frozenset({"api", "ollama"})

# Data sensitivity classes (low -> high sensitivity).
DATA_CLASSES = (
    "public",
    "synthetic",
    "redacted",
    "personal",
    "sensitive",
    "institution_internal",
)
DATA_CLASS_SET = frozenset(DATA_CLASSES)

# Classes that may EVER leave the machine to an external cloud provider.
EXTERNAL_SAFE_DATA_CLASSES = frozenset({"public", "synthetic", "redacted"})
# Classes that must NEVER reach an external provider.
EXTERNAL_FORBIDDEN_DATA_CLASSES = DATA_CLASS_SET - EXTERNAL_SAFE_DATA_CLASSES

LEVELS = frozenset({"L0", "L1", "L2", "L3", "L4"})

STATUSES = frozenset({"verified", "experimental", "unverified", "deprecated"})
COST_TIERS = frozenset(
    {"local_free", "free_quota_limited", "cheap", "standard", "premium"}
)
BILLING_MODES = frozenset(
    {"hardware", "token_balance", "free_quota_limited", "subscription"}
)

PROVIDER_ID_RE = re.compile(r"^[a-z0-9_]+$")

MAX_TIMEOUT_S = 120.0

SCHEMA_VERSION = "1.0"

# Exact set of allowed keys in a profile object. Unknown keys are rejected.
ALLOWED_FIELDS = frozenset(
    {
        "provider_id",
        "executor_key",
        "model",
        "status",
        "cost_tier",
        "billing_mode",
        "allowed_levels",
        "allowed_data_classes",
        "default_enabled",
        "requires_budget_gate",
        "requires_smoke_pass",
        "env_key",
        "timeout_s",
    }
)
# env_key is conditionally required (api executor only); not in this base set.
REQUIRED_FIELDS = frozenset(
    {
        "provider_id",
        "executor_key",
        "model",
        "status",
        "cost_tier",
        "billing_mode",
        "allowed_levels",
        "allowed_data_classes",
        "default_enabled",
        "requires_budget_gate",
        "requires_smoke_pass",
        "timeout_s",
    }
)

ALLOWED_TOP_LEVEL_KEYS = frozenset({"schema_version", "providers"})


class ProviderProfileError(ValueError):
    """Raised when a provider profile or config fails strict validation."""


@dataclass(frozen=True)
class ProviderProfile:
    """A single validated provider identity card.

    Construct only via validate_profile(); the dataclass itself assumes its
    inputs are already validated.
    """

    provider_id: str
    executor_key: str
    model: str
    status: str
    cost_tier: str
    billing_mode: str
    allowed_levels: tuple[str, ...]
    allowed_data_classes: tuple[str, ...]
    default_enabled: bool
    requires_budget_gate: bool
    requires_smoke_pass: bool
    timeout_s: float
    env_key: str | None = None

    @property
    def is_external(self) -> bool:
        """External = reaches a third-party cloud (api executor)."""
        return self.executor_key == "api"

    @property
    def is_local(self) -> bool:
        return self.executor_key == "ollama"

    def allows_data_class(self, data_class: str) -> bool:
        return data_class in self.allowed_data_classes

    def allows_level(self, level: str) -> bool:
        return level in self.allowed_levels


# --------------------------------------------------------------------------
# Strict single-profile validation
# --------------------------------------------------------------------------


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_number(value: Any) -> bool:
    # bool is a subclass of int; exclude it explicitly.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_str_list(
    value: Any, field_name: str, allowed: frozenset[str], errors: list[str]
) -> tuple[str, ...]:
    if not isinstance(value, list):
        errors.append(f"{field_name}: must be a list")
        return ()
    if len(value) == 0:
        errors.append(f"{field_name}: must be non-empty")
        return ()
    seen: set[str] = set()
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            errors.append(f"{field_name}: items must be strings, got {type(item).__name__}")
            continue
        if item in seen:
            errors.append(f"{field_name}: duplicate value {item!r}")
            continue
        if item not in allowed:
            errors.append(f"{field_name}: invalid value {item!r}")
            continue
        seen.add(item)
        out.append(item)
    return tuple(out)


def validate_profile(raw: Mapping[str, Any]) -> ProviderProfile:
    """Validate one raw profile mapping. Raise ProviderProfileError on any issue.

    All detected problems for the profile are aggregated into one error.
    """
    errors: list[str] = []

    if not isinstance(raw, Mapping):
        raise ProviderProfileError("profile: must be a JSON object")

    keys = set(raw.keys())

    # 1) Unknown keys -> reject (prevents fail-open via typo'd security field).
    unknown = keys - ALLOWED_FIELDS
    if unknown:
        errors.append(f"unknown field(s): {sorted(unknown)}")

    # 2) Missing required fields.
    missing = REQUIRED_FIELDS - keys
    if missing:
        errors.append(f"missing required field(s): {sorted(missing)}")

    pid = raw.get("provider_id")
    if "provider_id" in keys:
        if not isinstance(pid, str) or not PROVIDER_ID_RE.match(pid or ""):
            errors.append("provider_id: must match ^[a-z0-9_]+$")

    executor_key = raw.get("executor_key")
    if "executor_key" in keys and executor_key not in EXECUTOR_KEYS:
        errors.append(f"executor_key: must be one of {sorted(EXECUTOR_KEYS)}")

    model = raw.get("model")
    if "model" in keys and (not isinstance(model, str) or not model.strip()):
        errors.append("model: must be a non-empty string")

    status = raw.get("status")
    if "status" in keys and status not in STATUSES:
        errors.append(f"status: must be one of {sorted(STATUSES)}")

    cost_tier = raw.get("cost_tier")
    if "cost_tier" in keys and cost_tier not in COST_TIERS:
        errors.append(f"cost_tier: must be one of {sorted(COST_TIERS)}")

    billing_mode = raw.get("billing_mode")
    if "billing_mode" in keys and billing_mode not in BILLING_MODES:
        errors.append(f"billing_mode: must be one of {sorted(BILLING_MODES)}")

    allowed_levels: tuple[str, ...] = ()
    if "allowed_levels" in keys:
        allowed_levels = _check_str_list(
            raw.get("allowed_levels"), "allowed_levels", LEVELS, errors
        )

    allowed_data_classes: tuple[str, ...] = ()
    if "allowed_data_classes" in keys:
        allowed_data_classes = _check_str_list(
            raw.get("allowed_data_classes"),
            "allowed_data_classes",
            DATA_CLASS_SET,
            errors,
        )

    for bfield in ("default_enabled", "requires_budget_gate", "requires_smoke_pass"):
        if bfield in keys and not _is_bool(raw.get(bfield)):
            errors.append(f"{bfield}: must be a boolean (true/false)")

    timeout_s = raw.get("timeout_s")
    if "timeout_s" in keys:
        if not _is_number(timeout_s):
            errors.append("timeout_s: must be a number")
        elif not (0 < float(timeout_s) <= MAX_TIMEOUT_S):
            errors.append(f"timeout_s: must be in (0, {MAX_TIMEOUT_S}]")

    # env_key rules depend on executor_key.
    env_key = raw.get("env_key")
    has_env_key = "env_key" in keys and env_key is not None
    if executor_key == "api":
        if not has_env_key or not isinstance(env_key, str) or not env_key.strip():
            errors.append("env_key: required and non-empty for api executor")
    elif executor_key in EXECUTOR_KEYS:  # non-api known executor (ollama)
        if has_env_key:
            errors.append("env_key: not allowed for non-api executor")

    # --- External (api) hardening rules -----------------------------------
    is_external = executor_key == "api"
    if is_external:
        forbidden = set(allowed_data_classes) & EXTERNAL_FORBIDDEN_DATA_CLASSES
        if forbidden:
            errors.append(
                "allowed_data_classes: external provider may not carry "
                f"{sorted(forbidden)}; allowed only {sorted(EXTERNAL_SAFE_DATA_CLASSES)}"
            )
        if raw.get("requires_budget_gate") is False:
            errors.append("requires_budget_gate: external provider must be true")
        if raw.get("default_enabled") is True:
            errors.append("default_enabled: external provider must be false")
        if raw.get("requires_smoke_pass") is False:
            errors.append("requires_smoke_pass: external provider must be true")

    # --- Extra hardening: do not auto-enable unverified providers ----------
    if raw.get("default_enabled") is True and status != "verified":
        errors.append("default_enabled: true requires status 'verified'")

    if errors:
        label = pid if isinstance(pid, str) else "<unknown>"
        raise ProviderProfileError(
            f"provider profile '{label}' invalid: " + "; ".join(errors)
        )

    return ProviderProfile(
        provider_id=pid,
        executor_key=executor_key,
        model=model,
        status=status,
        cost_tier=cost_tier,
        billing_mode=billing_mode,
        allowed_levels=allowed_levels,
        allowed_data_classes=allowed_data_classes,
        default_enabled=bool(raw["default_enabled"]),
        requires_budget_gate=bool(raw["requires_budget_gate"]),
        requires_smoke_pass=bool(raw["requires_smoke_pass"]),
        timeout_s=float(timeout_s),
        env_key=env_key if executor_key == "api" else None,
    )


# --------------------------------------------------------------------------
# Registry + loader
# --------------------------------------------------------------------------


class ProviderProfileRegistry:
    """Read-only collection of validated provider profiles, keyed by id."""

    def __init__(self, profiles: list[ProviderProfile]):
        by_id: dict[str, ProviderProfile] = {}
        for p in profiles:
            if p.provider_id in by_id:
                raise ProviderProfileError(
                    f"duplicate provider_id: {p.provider_id!r}"
                )
            by_id[p.provider_id] = p
        self._by_id = by_id

    def get(self, provider_id: str) -> ProviderProfile | None:
        return self._by_id.get(provider_id)

    def require(self, provider_id: str) -> ProviderProfile:
        p = self._by_id.get(provider_id)
        if p is None:
            raise ProviderProfileError(f"unknown provider_id: {provider_id!r}")
        return p

    def all(self) -> tuple[ProviderProfile, ...]:
        return tuple(self._by_id.values())

    def external(self) -> tuple[ProviderProfile, ...]:
        return tuple(p for p in self._by_id.values() if p.is_external)

    def local(self) -> tuple[ProviderProfile, ...]:
        return tuple(p for p in self._by_id.values() if p.is_local)

    def enabled(self) -> tuple[ProviderProfile, ...]:
        return tuple(p for p in self._by_id.values() if p.default_enabled)

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, provider_id: object) -> bool:
        return provider_id in self._by_id


def load_provider_profiles(path: str | Path) -> ProviderProfileRegistry:
    """Load + strictly validate a provider profiles JSON config.

    Top-level shape (strict):
        {"schema_version": "1.0", "providers": [ {profile}, ... ]}
    """
    p = Path(path)
    if not p.is_file():
        raise ProviderProfileError(f"config file not found: {p}")

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProviderProfileError(f"config is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ProviderProfileError("config top-level must be a JSON object")

    top_keys = set(data.keys())
    unknown_top = top_keys - ALLOWED_TOP_LEVEL_KEYS
    if unknown_top:
        raise ProviderProfileError(
            f"config: unknown top-level key(s): {sorted(unknown_top)}"
        )

    if data.get("schema_version") != SCHEMA_VERSION:
        raise ProviderProfileError(
            f"config: schema_version must be {SCHEMA_VERSION!r}"
        )

    providers_raw = data.get("providers")
    if not isinstance(providers_raw, list) or len(providers_raw) == 0:
        raise ProviderProfileError("config: 'providers' must be a non-empty list")

    profiles = [validate_profile(item) for item in providers_raw]
    return ProviderProfileRegistry(profiles)
