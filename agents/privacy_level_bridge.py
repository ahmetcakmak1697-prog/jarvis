"""Privacy Level Bridge (FAZ 1B.13D, partial -- compatibility layer only).

One-way translation from the contract's data_class
(agents.provider_profiles.DATA_CLASS_SET) to the older APIExecutor
PRIVACY_LEVELS enum (agents.api_executor.PRIVACY_LEVELS).

THIS IS A TEMPORARY BRIDGE, NOT A CONSOLIDATION.
agents/api_executor.py currently has its own, parallel provider/privacy
system (APIProvider, PRIVACY_LEVELS, _DEFAULT_PROVIDERS) that does not yet
know about agents.provider_profiles / agents.provider_selector at all.
Full consolidation onto a single source of truth is future work.

THIS MODULE IS NOT YET WIRED INTO AssistantExecutor. AssistantExecutor
currently calls executor.generate(question, level=level) with NO
data_class/privacy_level argument at all, which means APIExecutor
defaults to privacy_level="PUBLIC" for every single external call today.
Wiring this bridge in requires a NEW capability that does not exist yet
anywhere in this codebase: computing a data_class for an incoming
question at intake time. That is separate, real feature work (its own
phase), not a one-line connection.

IMPORTANT SEMANTIC TRAP (read before ever changing this mapping):
The old PRIVACY_LEVELS enum conflates two different concerns that the new
contract deliberately keeps separate:
  1. Sensitivity / origin state -- this is what data_class represents.
  2. Content domain / role (TECHNICAL, CODE) -- not a sensitivity concept
     at all, it's about what KIND of work a provider is good at. This
     bridge never produces TECHNICAL or CODE; those remain reachable only
     through the old system's own internal defaults.

A second, more dangerous trap: "PERSONAL_REDACTED" in the old enum means
personal data that has ALREADY been redacted/de-identified -- it
corresponds to our "redacted" data_class (the post-redaction STATE), NOT
our "personal" data_class (which represents RAW personal data and is, by
contract, forbidden from ever reaching an external provider via
EXTERNAL_FORBIDDEN_DATA_CLASSES). Mapping "personal" -> "PERSONAL_REDACTED"
would silently undo that safety invariant. Do not do this. The test suite
for this module locks the correct mapping in place specifically to catch
that mistake if anyone "simplifies" this later.
"""
from __future__ import annotations

from agents.provider_profiles import DATA_CLASS_SET

# data_class -> old PRIVACY_LEVELS value.
# Deliberately conservative: when a data_class has no exact old-system
# analogue, this maps to a value that the old system itself already
# treats as sensitive (see SENSITIVE_PRIVACY_LEVELS in api_executor.py),
# rather than guessing optimistically. Fail-closed, same philosophy as
# the rest of this phase.
_DATA_CLASS_TO_PRIVACY_LEVEL: dict[str, str] = {
    "public": "PUBLIC",
    "synthetic": "PUBLIC",
    "redacted": "REDACTED_LOW_RISK",
    # Raw personal data is NOT the same as already-redacted personal data.
    # Treat it as sensitive, never as PERSONAL_REDACTED.
    "personal": "WORK_INTERNAL",
    "sensitive": "WORK_INTERNAL",
    "institution_internal": "WORK_INTERNAL",
}


def data_class_to_privacy_level(data_class: str) -> str:
    """Translate a contract data_class into an old-system PRIVACY_LEVELS value.

    Raises ValueError for any data_class not in DATA_CLASS_SET. Never
    guesses at an unknown classification (fail closed).
    """
    if data_class not in DATA_CLASS_SET:
        raise ValueError(f"unknown data_class: {data_class!r}")
    return _DATA_CLASS_TO_PRIVACY_LEVEL[data_class]
