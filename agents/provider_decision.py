"""Provider Decision Adapter (FAZ 1B.13C).

Pure glue between ExecutionPolicy's destination decision and
ProviderSelector's provider choice.

SCOPE (same discipline as the rest of this phase):
  * Does NOT call AssistantExecutor or APIExecutor.
  * Does NOT mutate the input decision dict (always returns a new one).
  * Does NOT perform any model/API call, no I/O, no cost ledger mutation.
  * Wiring this into AssistantExecutor/APIExecutor is a deliberate,
    separate next step (FAZ 1B.13D) -- intentionally NOT done here without
    first reviewing those files, to avoid risking the existing passing
    test suite under time pressure.

CONTRACT FOR THE NEXT PHASE (13D):
  When destination is "cloud_api" or "premium_gate" and the returned dict
  has provider_id=None, the wiring code should treat that exactly like an
  unavailable/failed "api" executor and take the existing
  fallback_executor path. This codebase already falls back to ollama on
  API failure / missing executor; resolving to "no provider" here is the
  same class of event, just detected one step earlier (before any network
  call would have been attempted).

OBSERVED BEHAVIOUR WITH THE CURRENT EXAMPLE CONFIG (intentional, not a
bug): every shipped external provider has default_enabled=False, so an
automatic (non-explicit) resolution for "cloud_api" will always degrade to
provider_id=None today. Reaching an external provider requires an
explicit, audited escalation (explicit_provider_id) -- e.g. from a future
budget-gate approval flow. This matches the "local by default, cloud only
on deliberate escalation" architecture decision.
"""
from __future__ import annotations

from typing import Any, Optional

from agents.provider_selector import (
    ProviderSelectionError,
    ProviderSelector,
    SelectionRequest,
)

# Destinations that require resolving a concrete external provider.
GATED_DESTINATIONS = frozenset({"cloud_api", "premium_gate"})


def resolve_provider(
    decision: dict[str, Any],
    *,
    data_class: str,
    selector: ProviderSelector,
    exclude: frozenset[str] = frozenset(),
    explicit_provider_id: Optional[str] = None,
    prefer_order: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Augment an ExecutionPolicy decision with a concrete provider choice.

    Returns a NEW dict; the input `decision` is never mutated.

    For destinations that do not need an external provider (local,
    local_answer, blocked, no_execution), the dict is returned unchanged
    except for an explicit `provider_id=None`.

    For "cloud_api" / "premium_gate", attempts ProviderSelector.select()
    with require_external=True. On success, the dict gains provider_id,
    provider_model, provider_timeout_s, provider_env_key, and
    requires_approval is OR-ed with the chosen provider's
    requires_budget_gate flag. On failure (no eligible provider), the dict
    gains provider_id=None and provider_resolution_error, while
    destination/primary_executor are left exactly as ExecutionPolicy
    produced them -- see the 13D contract note above for why.
    """
    out = dict(decision)
    destination = str(out.get("destination") or "")

    if destination not in GATED_DESTINATIONS:
        out["provider_id"] = None
        return out

    level = str(out.get("level") or "")
    try:
        profile = selector.select(
            SelectionRequest(
                level=level,
                data_class=data_class,
                exclude=exclude,
                explicit_provider_id=explicit_provider_id,
                require_external=True,
                prefer_order=prefer_order,
            )
        )
    except ProviderSelectionError as exc:
        out["provider_id"] = None
        out["provider_resolution_error"] = str(exc)
        return out

    out["provider_id"] = profile.provider_id
    out["provider_model"] = profile.model
    out["provider_timeout_s"] = profile.timeout_s
    out["provider_env_key"] = profile.env_key
    out["requires_approval"] = (
        bool(out.get("requires_approval", False)) or profile.requires_budget_gate
    )
    return out
