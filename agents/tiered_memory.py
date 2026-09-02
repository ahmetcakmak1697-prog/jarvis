"""C1.7 - Tiered Memory classifier.

Classifies a memory text into one of four tiers:
  core     - identity, persistent facts (name, project, preferences)
  recall   - frequently used, technical, recent knowledge
  archival - old, infrequent, historical
  episodic - session/day-level context, transient

Rules are deterministic keyword-based (no LLM).
Zero side effects.
"""
from __future__ import annotations


class MemoryTier:
    CORE = "core"
    RECALL = "recall"
    ARCHIVAL = "archival"
    EPISODIC = "episodic"


_CORE_SIGNALS = [
    "benim adim", "ben ", "jarvis projesi", "projem", "eshot",
    "kawasaki", "vulcan", "dilara", "bagevi", "bag evi",
    "ismim", "calisiyorum", "oturuyorum", "izmir", "buca",
]

_EPISODIC_SIGNALS = [
    "bugun", "simdi", "su an", "bu oturumda", "az once",
    "patch", "commit", "test", "hata", "bug", "fix",
    "yapiyoruz", "yaziyoruz", "calistiriyoruz",
]

_ARCHIVAL_SIGNALS = [
    "yilinda", "eskiden", "once", "2019", "2020", "2021",
    "eski", "artik kullanmiyorum", "birakmistim",
]


def _tr_fold(s: str) -> str:
    s = s.replace("\u0130", "i").replace("\u0131", "i")
    s = s.replace("\u015f", "s").replace("\u015e", "s")
    s = s.replace("\u011f", "g").replace("\u011e", "g")
    s = s.replace("\u00fc", "u").replace("\u00dc", "u")
    s = s.replace("\u00f6", "o").replace("\u00d6", "o")
    s = s.replace("\u00e7", "c").replace("\u00c7", "c")
    s = s.replace("\u0049", "i")
    return s.lower()


class TieredMemoryRouter:
    """Classify memory text into a tier. Deterministic, no LLM."""

    def classify(self, text: str) -> str:
        """Return tier string: core/recall/archival/episodic."""
        return self.classify_with_meta(text)["tier"]

    def classify_with_meta(self, text: str) -> dict:
        """Return {tier, tier_reason}."""
        folded = _tr_fold(str(text or ""))

        for signal in _CORE_SIGNALS:
            if signal in folded:
                return {"tier": MemoryTier.CORE, "tier_reason": f"core_signal:{signal}"}

        for signal in _ARCHIVAL_SIGNALS:
            if signal in folded:
                return {"tier": MemoryTier.ARCHIVAL, "tier_reason": f"archival_signal:{signal}"}

        for signal in _EPISODIC_SIGNALS:
            if signal in folded:
                return {"tier": MemoryTier.EPISODIC, "tier_reason": f"episodic_signal:{signal}"}

        # default: recall (frequent technical knowledge)
        return {"tier": MemoryTier.RECALL, "tier_reason": "default:recall"}
