"""Data Classifier (FAZ 1B.13E): intake-time data_class inference.

Pure, rule-based, deterministic classifier that assigns an
agents.provider_profiles.DATA_CLASS_SET value to raw incoming text. This
is the missing piece between the existing router/redaction_guard and the
provider contract built in FAZ 1B.13A-D: without it, every ask_external
question is implicitly treated as "public" (api_executor.py's
privacy_level default), defeating the entire purpose of the data
classification matrix.

SCOPE (deliberately narrow, same discipline as the rest of this work):
  * Pure function of text -> data_class. No I/O, no model calls, no
    network, no state mutation.
  * WIRED into AssistantExecutor as of FAZ 1B.13F (commit 278597dba):
    AssistantExecutor._classify_for_external() calls classify() here,
    then forwards the resulting privacy_level ONLY to the "api" executor
    (never to ollama/local executors, which do not accept that kwarg).
    If this comment ever looks stale, trust agents/assistant_executor.py
    over this docstring -- comments rot, git history doesn't.
  * Does NOT replace redaction_guard. Actual secrets (API keys, tokens)
    are caught upstream by the router and never reach this point; by the
    time classification would run, the router has already decided
    "ask_external" rather than "redacted_blocked".
  * Only ever returns "public", "personal", "sensitive", or
    "institution_internal". NEVER returns "redacted" or "synthetic" --
    those two describe a PROCESSING STATE (already masked / deliberately
    synthetic test data), not something inferable from raw text. A caller
    holding already-redacted or synthetic text must set that data_class
    explicitly and must not call this classifier for that case.

PHILOSOPHY: default to "public" (maximize external-model capability,
matching the user's stated priority ranking: yetenek genisligi > karakter
> maliyet > gizlilik) and escalate to a more restrictive class ONLY when a
concrete signal is found. Classifying everything as sensitive by default
would make the external-provider path useless. The fail-closed property
that matters here is narrower: once ANY signal matches, the result is
decided by that signal, never downgraded by guesswork, and when multiple
signal categories match the same text, the MOST restrictive one wins.

This is heuristic, not a perfect classifier. The signal lists below are
deliberately kept as plain data (not control flow) so they can be tuned
and extended over time without touching the classification logic.
"""
from __future__ import annotations

import re
from typing import Iterable

from agents.provider_profiles import DATA_CLASS_SET


def _fold_tr(s: str) -> str:
    text = str(s or "").strip()
    # Turkish capital dotted I (U+0130, "İ") must be collapsed to plain
    # "i" BEFORE calling .lower(): Python's default Unicode lower() maps
    # U+0130 to "i" + COMBINING DOT ABOVE (U+0307) -- a TWO-codepoint
    # sequence, not a clean ASCII "i". Left unhandled, every substring
    # signal check below silently breaks on it (e.g. "İBAN" folds to
    # "i\u0307ban", which does NOT contain "iban" as a substring). This
    # is a real, verified Python/Unicode quirk (the "Turkish I problem"),
    # confirmed by direct interpreter test, not a hypothetical edge case.
    text = text.replace("\u0130", "i")
    return (
        text.lower()
        .replace("\u0131", "i").replace("\u011f", "g")
        .replace("\u00fc", "u").replace("\u015f", "s")
        .replace("\u00f6", "o").replace("\u00e7", "c")
    )


# Evaluated in this order; the FIRST matching category wins. Order reflects
# severity, most restrictive first -- not a claim that institution_internal
# is "worse" than sensitive in the abstract, just a deterministic tie-break
# when a single text trips more than one category.

_INSTITUTION_INTERNAL_SIGNALS: tuple[str, ...] = (
    "eshot", "bium", "bys", "zimbra",
    "rolanti", "rejen",
    "surucu karnesi", "surucu ihlal",
    "vardiya cetveli", "personel ozluk", "ozluk dosyasi",
    "kurum ici", "sirket ici", "ic rapor",
    "genel mudurluk",
)

_SENSITIVE_SIGNALS: tuple[str, ...] = (
    # legal
    "dava", "avukat", "muvekkil", "mahkeme", "dilekce",
    "icra dosyasi", "tahkim", "sozlesme ihtilafi", "vekaletname",
    # financial
    "iban", "banka hesap", "kredi karti", "hesap bakiyesi",
    "maas bordrosu", "kripto cuzdan", "borsa hesabi", "trade hesabi",
    "portfoy degeri",
)

_PERSONAL_PHRASE_SIGNALS: tuple[str, ...] = (
    "tc kimlik", "kimlik numaram", "ev adresim", "telefon numaram",
    "dogum tarihim", "saglik bilgim", "hasta dosyam",
)

# Bare 11-digit sequences (Turkish TC kimlik no length, also common
# Turkish mobile number length) are treated as a personal-data signal.
# Known limitation: this can false-positive on unrelated 11-digit numbers
# (invoice IDs, etc). Escalating to "personal" on a false positive is a
# safe-direction error (over-cautious, not under-cautious), so it is kept
# as-is rather than tightened with fragile extra heuristics.
_ELEVEN_DIGIT_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")


def _contains_any(folded_text: str, signals: Iterable[str]) -> bool:
    return any(sig in folded_text for sig in signals)


def classify(text: str) -> str:
    """Classify raw intake text into a data_class.

    Returns one of: "institution_internal", "sensitive", "personal",
    "public". Defaults to "public" when no signal is found. Never raises
    on None/empty input.
    """
    folded = _fold_tr(text)

    if _contains_any(folded, _INSTITUTION_INTERNAL_SIGNALS):
        return "institution_internal"

    if _contains_any(folded, _SENSITIVE_SIGNALS):
        return "sensitive"

    if _contains_any(folded, _PERSONAL_PHRASE_SIGNALS) or _ELEVEN_DIGIT_RE.search(str(text or "")):
        return "personal"

    return "public"


# Sanity: the four classes this module can ever return must all be valid
# members of the contract's data_class set. Checked once at import time
# rather than per-call (these are static, hardcoded return values).
_POSSIBLE_OUTPUTS = frozenset({"institution_internal", "sensitive", "personal", "public"})
assert _POSSIBLE_OUTPUTS <= DATA_CLASS_SET, "classifier output set drifted from DATA_CLASS_SET"
