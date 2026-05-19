"""Memory Policy - C1.

Decides whether a user/JARVIS exchange should be:
- kept long term
- summarized daily
- kept temporarily
- ignored
- routed to sensitive review

This module does not write memory by itself.
It only returns a safe decision object.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class MemoryDecision:
    action: str
    importance: int
    reason: str
    tags: list[str]
    retention_days: int | None = None
    allow_vector: bool = False
    allow_daily_summary: bool = False
    requires_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemoryPolicy:
    """Rule-based memory policy for safe local assistant memory."""

    ACTION_KEEP_LONG_TERM = "keep_long_term"
    ACTION_DAILY_SUMMARY = "daily_summary"
    ACTION_TEMPORARY = "temporary"
    ACTION_IGNORE = "ignore"
    ACTION_SENSITIVE_REVIEW = "sensitive_review"

    LOW_VALUE_PATTERNS = [
        r"^\s*(merhaba|selam|hi|hello|tamam|ok|evet|hayir|hay?r|te?ekk?r|tesekkur)\s*[.!]*\s*$",
        r"^\s*(sa? ol|sag ol|eyvallah)\s*[.!]*\s*$",
    ]

    LONG_TERM_PATTERNS = [
        r"\b(projem|hedefim|plan?m|planim|tercihim|sevdi?im|sevdigim|sevmedi?im|sevmedigim)\b",
        r"\b(bundan sonra|ileride|gelecekte|hep|s?rekli|surekli|unutma|hat?rla|hatirla)\b",
        r"\b(jarvis|yerel asistan|roadmap|yol haritas?|yol haritasi)\b",
    ]

    DAILY_SUMMARY_PATTERNS = [
        r"\b(bug?n|bugun|yar?n|yarin|d?n|dun|bu hafta|toplant?|toplanti|g?rev|gorev)\b",
        r"\b(yap?lacak|yapilacak|not al|rapor|analiz|test|commit)\b",
    ]

    PROJECT_PATTERNS = [
        r"\b(commit|git|patch|server|telegram|tailscale|api|endpoint|dashboard|task|handler)\b",
        r"\b(c1|c2|c3|b2\.7|b2\.6|haf?za|hafiza|proje zekas?|proje zekasi)\b",
    ]

    # Sensitive data should not be silently stored as long-term vector memory.
    # We route it to review or temporary handling unless the user explicitly asks.
    SENSITIVE_PATTERNS = [
        r"telefon\s+numaram",
        r"numaram\s+\d",
        r"\b(adresim|ev adresim|tc kimlik|kimlik numaram|telefonum|telefon no|gsm|?ifrem|sifrem|parolam)\b",
        r"\b(kredi kart?|kredi karti|iban|banka hesab?|banka hesabi)\b",
        r"\b(hastal???m|hastaligim|alerjim|ila?|ilac|tan?|tani|te?his|teshis)\b",
        r"\b(siyasi g?r???m|siyasi gorusum|dinim|mezhebim|?rk?m|irkim|etnik)\b",
    ]

    EXPLICIT_SAVE_PATTERNS = [
        r"bunu\s+hat?rla",
        r"bunu\s+hatirla",
        r"bunu\s+unutma",
        r"haf?zaya\s+al",
        r"hafizaya\s+al",
        r"\b(kaydet|not et)\b",
    ]

    EXPLICIT_FORGET_PATTERNS = [
        r"\b(bunu unut|sil|haf?zadan ??kar|hafizadan cikar|kayd? sil|kaydi sil)\b",
    ]

    def decide(self, user_msg: str, jarvis_msg: str = "", meta: dict[str, Any] | None = None) -> MemoryDecision:
        user_msg = user_msg or ""
        jarvis_msg = jarvis_msg or ""
        meta = meta or {}

        text = f"{user_msg}\n{jarvis_msg}".lower()
        norm_text = self._normalize(text)
        norm_user = self._normalize(user_msg)
        tags: list[str] = []
        importance = 5

        if self._matches_any(user_msg.lower(), self.EXPLICIT_FORGET_PATTERNS) or "bunu unut" in norm_user or "hafizadan cikar" in norm_user:
            return MemoryDecision(
                action=self.ACTION_SENSITIVE_REVIEW,
                importance=9,
                reason="Kullan?c? haf?zadan silme/unutma talebi verdi.",
                tags=["forget_request"],
                retention_days=None,
                allow_vector=False,
                allow_daily_summary=True,
                requires_review=True,
            )

        if self._matches_any(user_msg.lower(), self.LOW_VALUE_PATTERNS):
            return MemoryDecision(
                action=self.ACTION_IGNORE,
                importance=1,
                reason="K?sa nezaket/onay mesaj?; kal?c? haf?za de?eri d???k.",
                tags=["low_value"],
                retention_days=0,
                allow_vector=False,
                allow_daily_summary=False,
                requires_review=False,
            )

        sensitive = self._matches_any(text, self.SENSITIVE_PATTERNS) or "telefon numaram" in norm_text or "numaram " in norm_text
        explicit_save = (
            self._matches_any(text, self.EXPLICIT_SAVE_PATTERNS)
            or "bunu hatirla" in norm_text
            or "bunu unutma" in norm_text
            or "hafizaya al" in norm_text
            or "kaydet" in norm_text
            or "not et" in norm_text
        )

        if sensitive:
            tags.append("sensitive")
            importance += 2

            if explicit_save:
                tags.append("explicit_save")
                return MemoryDecision(
                    action=self.ACTION_SENSITIVE_REVIEW,
                    importance=min(10, importance),
                    reason="Hassas bilgi i?eriyor ve kullan?c? kaydetme istedi; inceleme gerekli.",
                    tags=tags,
                    retention_days=None,
                    allow_vector=False,
                    allow_daily_summary=True,
                    requires_review=True,
                )

            return MemoryDecision(
                action=self.ACTION_SENSITIVE_REVIEW,
                importance=min(8, importance),
                reason="Hassas bilgi i?eriyor; otomatik uzun haf?zaya al?nmamal?.",
                tags=tags,
                retention_days=7,
                allow_vector=False,
                allow_daily_summary=False,
                requires_review=True,
            )

        if self._matches_any(text, self.PROJECT_PATTERNS):
            tags.append("project")
            importance += 2

        if self._matches_any(text, self.LONG_TERM_PATTERNS):
            tags.append("long_term_signal")
            importance += 2

        if self._matches_any(text, self.DAILY_SUMMARY_PATTERNS):
            tags.append("daily_signal")
            importance += 1

        if explicit_save:
            tags.append("explicit_save")
            importance += 3
            importance = max(importance, 8)

        if len(user_msg) > 300:
            tags.append("detailed")
            importance += 1

        importance = max(0, min(10, importance))

        if importance >= 8:
            return MemoryDecision(
                action=self.ACTION_KEEP_LONG_TERM,
                importance=importance,
                reason="Y?ksek ?nem: proje/tercih/kal?c? sinyal tespit edildi.",
                tags=tags or ["important"],
                retention_days=None,
                allow_vector=True,
                allow_daily_summary=True,
                requires_review=False,
            )

        if "daily_signal" in tags or "project" in tags:
            return MemoryDecision(
                action=self.ACTION_DAILY_SUMMARY,
                importance=importance,
                reason="G?nl?k ?zet/proje takibi i?in de?erli.",
                tags=tags or ["daily"],
                retention_days=30,
                allow_vector=False,
                allow_daily_summary=True,
                requires_review=False,
            )

        return MemoryDecision(
            action=self.ACTION_TEMPORARY,
            importance=importance,
            reason="Orta de?erli konu?ma; ge?ici tutulabilir.",
            tags=tags or ["temporary"],
            retention_days=14,
            allow_vector=False,
            allow_daily_summary=False,
            requires_review=False,
        )

    def _normalize(self, text: str) -> str:
        table = str.maketrans({
            "?": "i", "?": "i",
            "?": "g", "?": "g",
            "?": "u", "?": "u",
            "?": "s", "?": "s",
            "?": "o", "?": "o",
            "?": "c", "?": "c",
        })
        return (text or "").translate(table).lower()


    def _matches_any(self, text: str, patterns: list[str]) -> bool:
        for pattern in patterns:
            try:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    return True
            except re.error:
                # Defensive guard: one malformed pattern must not crash memory policy.
                # Fall back to a conservative plain-text containment check.
                plain = (
                    pattern
                    .replace(r"\\b", "")
                    .replace("\\b", "")
                    .replace("(", "")
                    .replace(")", "")
                    .replace("|", " ")
                    .replace(r"\\s", " ")
                    .replace("*", "")
                    .replace("+", "")
                    .replace("?", "")
                    .strip()
                    .lower()
                )
                if plain and plain in text.lower():
                    return True
        return False


if __name__ == "__main__":
    policy = MemoryPolicy()
    samples = [
        "Merhaba",
        "Bundan sonra Jarvis yol haritas?nda C1 haf?za politikas?n? unutma.",
        "Bug?n Telegram bot ve Tailscale testini tamamlad?k.",
        "Telefon numaram 555 ile ba?l?yor.",
        "Bunu hat?rla: projede C2 proje zekas?na ge?ece?iz.",
        "Bunu unut ve haf?zadan ??kar.",
    ]

    for sample in samples:
        decision = policy.decide(sample)
        print("---")
        print(sample)
        print(decision.to_dict())
