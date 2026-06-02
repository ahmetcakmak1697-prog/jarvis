"""Memory Schema - C1.1.

Maps MemoryPolicy decisions into a stable memory routing schema.

This module does not write to vector memory, candidate queues, or JSON stores.
It only returns normalized routing records that later C1 phases can consume.

C1 principles:
- no silent sensitive long-term storage
- semantic memory requires an explicit safe route
- episodic data is temporary by default
- every meaningful route carries audit metadata
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any

from agents.memory_policy import MemoryDecision, MemoryPolicy


SCHEMA_VERSION = "c1.1"


@dataclass
class MemoryRoute:
    schema_version: str
    memory_type: str
    storage_target: str
    sensitivity: str
    action: str
    importance: int
    reason: str
    tags: list[str]
    requires_review: bool
    allow_vector: bool
    allow_daily_summary: bool
    retention_days: int | None
    created_at: str
    expires_at: str | None
    source: str
    confidence: int
    delete_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemorySchemaMapper:
    """Convert MemoryPolicy decisions into stable C1 memory routes."""

    TYPE_SEMANTIC = "semantic"
    TYPE_EPISODIC = "episodic"
    TYPE_IGNORE = "ignore"
    TYPE_SENSITIVE_REVIEW = "sensitive_review"

    TARGET_VECTOR = "vector"
    TARGET_DAILY_SUMMARY = "daily_summary"
    TARGET_TEMPORARY_JSON = "temporary_json"
    TARGET_REVIEW_QUEUE = "review_queue"
    TARGET_NONE = "none"

    SENSITIVITY_NORMAL = "normal"
    SENSITIVITY_PERSONAL = "personal"
    SENSITIVITY_SENSITIVE = "sensitive"
    SENSITIVITY_SECRET = "secret"

    def __init__(self, policy: MemoryPolicy | None = None):
        self.policy = policy or MemoryPolicy()

    def route_exchange(
        self,
        user_msg: str,
        jarvis_msg: str = "",
        meta: dict[str, Any] | None = None,
    ) -> MemoryRoute:
        meta = meta or {}
        decision = self.policy.decide(user_msg, jarvis_msg, meta)
        return self.route_decision(decision, user_msg=user_msg, jarvis_msg=jarvis_msg, meta=meta)

    def route_decision(
        self,
        decision: MemoryDecision,
        user_msg: str = "",
        jarvis_msg: str = "",
        meta: dict[str, Any] | None = None,
    ) -> MemoryRoute:
        meta = meta or {}
        action = decision.action
        tags = list(decision.tags or [])
        sensitivity = self._sensitivity_from_tags_and_text(tags, user_msg, jarvis_msg)

        memory_type, storage_target = self._map_action(
            action=action,
            allow_vector=decision.allow_vector,
            allow_daily_summary=decision.allow_daily_summary,
            requires_review=decision.requires_review,
            sensitivity=sensitivity,
        )

        created_at = datetime.now().isoformat(timespec="seconds")
        expires_at = self._expires_at(decision.retention_days)

        confidence = self._confidence_from_decision(decision)
        source = str(meta.get("source") or meta.get("source_type") or "conversation")
        delete_id = self._delete_id(user_msg, jarvis_msg, created_at, source)

        return MemoryRoute(
            schema_version=SCHEMA_VERSION,
            memory_type=memory_type,
            storage_target=storage_target,
            sensitivity=sensitivity,
            action=action,
            importance=int(decision.importance),
            reason=decision.reason,
            tags=tags,
            requires_review=bool(decision.requires_review),
            allow_vector=bool(decision.allow_vector),
            allow_daily_summary=bool(decision.allow_daily_summary),
            retention_days=decision.retention_days,
            created_at=created_at,
            expires_at=expires_at,
            source=source,
            confidence=confidence,
            delete_id=delete_id,
        )

    def _map_action(
        self,
        action: str,
        allow_vector: bool,
        allow_daily_summary: bool,
        requires_review: bool,
        sensitivity: str,
    ) -> tuple[str, str]:
        if requires_review or action == MemoryPolicy.ACTION_SENSITIVE_REVIEW:
            return self.TYPE_SENSITIVE_REVIEW, self.TARGET_REVIEW_QUEUE

        if action == MemoryPolicy.ACTION_IGNORE:
            return self.TYPE_IGNORE, self.TARGET_NONE

        if action == MemoryPolicy.ACTION_KEEP_LONG_TERM and allow_vector:
            if sensitivity in {self.SENSITIVITY_SENSITIVE, self.SENSITIVITY_SECRET}:
                return self.TYPE_SENSITIVE_REVIEW, self.TARGET_REVIEW_QUEUE
            return self.TYPE_SEMANTIC, self.TARGET_VECTOR

        if action == MemoryPolicy.ACTION_DAILY_SUMMARY or allow_daily_summary:
            return self.TYPE_EPISODIC, self.TARGET_DAILY_SUMMARY

        if action == MemoryPolicy.ACTION_TEMPORARY:
            return self.TYPE_EPISODIC, self.TARGET_TEMPORARY_JSON

        return self.TYPE_IGNORE, self.TARGET_NONE

    def _sensitivity_from_tags_and_text(self, tags: list[str], user_msg: str, jarvis_msg: str) -> str:
        text = f"{user_msg}\n{jarvis_msg}".lower()

        if "sensitive" in tags:
            return self.SENSITIVITY_SENSITIVE

        secret_markers = [
            "şifre",
            "sifre",
            "parola",
            "token",
            "api key",
            "apikey",
            "secret",
            "tc kimlik",
            "kredi kart",
            "iban",
        ]
        if any(marker in text for marker in secret_markers):
            return self.SENSITIVITY_SECRET

        personal_markers = [
            "telefon",
            "adres",
            "eşim",
            "esim",
            "ailem",
            "doğum",
            "dogum",
            "sağlık",
            "saglik",
        ]
        if any(marker in text for marker in personal_markers):
            return self.SENSITIVITY_PERSONAL

        return self.SENSITIVITY_NORMAL

    def _confidence_from_decision(self, decision: MemoryDecision) -> int:
        base = int(decision.importance or 5) * 10

        if decision.requires_review:
            base -= 10
        if decision.allow_vector:
            base += 5
        if "explicit_save" in (decision.tags or []):
            base += 10
        if decision.action == MemoryPolicy.ACTION_IGNORE:
            base = 95

        return max(0, min(100, base))

    def _expires_at(self, retention_days: int | None) -> str | None:
        if retention_days is None:
            return None
        if retention_days <= 0:
            return datetime.now().isoformat(timespec="seconds")
        return (datetime.now() + timedelta(days=retention_days)).isoformat(timespec="seconds")

    def _delete_id(self, user_msg: str, jarvis_msg: str, created_at: str, source: str) -> str:
        raw = f"{source}|{created_at}|{user_msg}|{jarvis_msg}".encode("utf-8", errors="ignore")
        return "md_" + hashlib.sha256(raw).hexdigest()[:16]


if __name__ == "__main__":
    mapper = MemorySchemaMapper()
    samples = [
        "tamam",
        "bunu hatırla: AC/DC ve rock müzik seviyorum",
        "bugün hava yağmurlu, motosiklete çıkmayacağım",
        "Jarvis C1 hafıza politikasına başladık",
        "telefon numaram 555 123 45 67 bunu kaydet",
    ]

    for sample in samples:
        route = mapper.route_exchange(sample)
        print("---")
        print(sample)
        print(route.to_dict())
