"""Provider Selector (FAZ 1B.13B).

Pure selection logic over an already-validated ProviderProfileRegistry.

SCOPE (intentionally narrow, same discipline as provider_profiles.py):
  * NO router integration. AssistantExecutor / ExecutionPolicy will call
    this in a LATER phase.
  * NO API calls, no network, no I/O.
  * NO knowledge of cost ledger, budget gate, or runtime smoke-pass state.
    Those remain the job of higher-level policy layers; this module only
    answers "which configured provider satisfies these static
    constraints?" -- deterministically and safely.

SAFETY INVARIANT (do not weaken this):
  data_class and level constraints are NEVER bypassed, even for an
  explicit provider_id request. The ONLY thing an explicit request may
  override is `default_enabled`. That is the intentional, audited
  escalation path: e.g. a future ExecutionPolicy explicitly invoking a
  disabled-by-default external provider *after* a budget-gate approval,
  while still being physically unable to send institution_internal data
  to it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agents.provider_profiles import (
    DATA_CLASS_SET,
    LEVELS,
    ProviderProfile,
    ProviderProfileRegistry,
)


class ProviderSelectionError(ValueError):
    """Raised when no provider can be safely selected for a request."""


# Lower rank = preferred by default when multiple candidates qualify.
# Local/free options are preferred over paid ones unless explicitly
# overridden via SelectionRequest.prefer_order or require_external.
COST_TIER_RANK = {
    "local_free": 0,
    "free_quota_limited": 1,
    "cheap": 2,
    "standard": 3,
    "premium": 4,
}
# Defensive fallback only; validated profiles always have a known cost_tier.
_UNKNOWN_TIER_RANK = 99

# A provider with status "experimental" may ONLY be reached via an explicit
# request, and ONLY for these data classes -- regardless of what its own
# allowed_data_classes declares. This is a selector-level ceiling on top of
# the profile's own (already validated) declaration; defense in depth for
# providers that are still being onboarded/benchmarked.
EXPERIMENTAL_DATA_CLASSES = frozenset({"public", "synthetic"})

# Statuses that may never be selected at all, by any path.
_NEVER_SELECTABLE_STATUSES = frozenset({"deprecated", "unverified"})


@dataclass(frozen=True)
class SelectionRequest:
    """Static selection constraints. No runtime state, no side effects.

    Fields:
        level: required capability level (must be one of provider_profiles.LEVELS)
        data_class: sensitivity class of the data this call will carry
        exclude: provider_ids to skip (e.g. already failed in this fallback chain)
        explicit_provider_id: bypass automatic ranking and request one provider
            by id. Still subject to the level/data_class safety invariant.
        require_external: True = must be an api/cloud provider, False = must
            be local (ollama), None = no preference
        prefer_order: provider_ids in priority order, consulted before the
            default cost_tier-based tie-break
    """

    level: str
    data_class: str
    exclude: frozenset[str] = frozenset()
    explicit_provider_id: Optional[str] = None
    require_external: Optional[bool] = None
    prefer_order: tuple[str, ...] = ()


class ProviderSelector:
    """Selects a provider profile matching a SelectionRequest."""

    def __init__(self, registry: ProviderProfileRegistry):
        self._registry = registry

    def select(self, request: SelectionRequest) -> ProviderProfile:
        if request.level not in LEVELS:
            raise ProviderSelectionError(f"unknown level: {request.level!r}")
        if request.data_class not in DATA_CLASS_SET:
            raise ProviderSelectionError(
                f"unknown data_class: {request.data_class!r}"
            )

        if request.explicit_provider_id is not None:
            return self._select_explicit(request)
        return self._select_automatic(request)

    # -- explicit path: bypasses default_enabled, NEVER bypasses safety ----

    def _select_explicit(self, request: SelectionRequest) -> ProviderProfile:
        pid = request.explicit_provider_id
        profile = self._registry.get(pid)
        if profile is None:
            raise ProviderSelectionError(f"unknown provider_id: {pid!r}")
        if pid in request.exclude:
            raise ProviderSelectionError(
                f"provider_id {pid!r} is excluded for this request"
            )
        if profile.status in _NEVER_SELECTABLE_STATUSES:
            raise ProviderSelectionError(
                f"provider {pid!r} has status {profile.status!r} and can "
                "never be selected (deprecated/unverified providers must "
                "be removed or promoted before use)"
            )
        if profile.status == "experimental":
            if request.data_class not in EXPERIMENTAL_DATA_CLASSES:
                raise ProviderSelectionError(
                    f"provider {pid!r} is experimental and may only be used "
                    f"with data_class in {sorted(EXPERIMENTAL_DATA_CLASSES)}, "
                    f"not {request.data_class!r}"
                )
        if not profile.allows_level(request.level):
            raise ProviderSelectionError(
                f"provider {pid!r} does not allow level {request.level!r}"
            )
        if not profile.allows_data_class(request.data_class):
            raise ProviderSelectionError(
                f"provider {pid!r} does not allow data_class {request.data_class!r}"
            )
        if request.require_external is True and not profile.is_external:
            raise ProviderSelectionError(f"provider {pid!r} is not external")
        if request.require_external is False and not profile.is_local:
            raise ProviderSelectionError(f"provider {pid!r} is not local")
        return profile

    # -- automatic path: only default_enabled providers participate -------

    def _select_automatic(self, request: SelectionRequest) -> ProviderProfile:
        # Defense in depth: even though the contract layer ties
        # default_enabled=True to status="verified", the selector does not
        # rely on that coupling alone -- it checks status independently in
        # case that contract invariant is ever relaxed.
        candidates = [
            p
            for p in self._registry.all()
            if p.default_enabled
            and p.status == "verified"
            and p.provider_id not in request.exclude
            and p.allows_level(request.level)
            and p.allows_data_class(request.data_class)
        ]
        if request.require_external is True:
            candidates = [p for p in candidates if p.is_external]
        elif request.require_external is False:
            candidates = [p for p in candidates if p.is_local]

        if not candidates:
            raise ProviderSelectionError(
                "no enabled provider satisfies level="
                f"{request.level!r}, data_class={request.data_class!r}, "
                f"require_external={request.require_external!r}, "
                f"excluded={sorted(request.exclude)}"
            )

        if request.prefer_order:
            known_ids = {p.provider_id for p in self._registry.all()}
            unknown_prefs = [
                pid for pid in request.prefer_order if pid not in known_ids
            ]
            if unknown_prefs:
                raise ProviderSelectionError(
                    "prefer_order contains unknown provider_id(s): "
                    f"{unknown_prefs} (check for typos in config)"
                )
            for pid in request.prefer_order:
                for c in candidates:
                    if c.provider_id == pid:
                        return c

        candidates.sort(
            key=lambda p: (
                COST_TIER_RANK.get(p.cost_tier, _UNKNOWN_TIER_RANK),
                p.provider_id,
            )
        )
        return candidates[0]
