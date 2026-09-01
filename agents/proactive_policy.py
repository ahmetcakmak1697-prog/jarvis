"""ProactivePolicy - FAZ-3-E1.

Decides whether a proactive state/event should be delivered, suppressed,
or deferred. Pure and deterministic: no network, no Telegram, no filesystem
writes, no scheduler, no background loop.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, asdict
from typing import Any


_DISABLED_VALUES = frozenset({"", "0", "false", "no", "off"})


@dataclass
class ProactiveDecision:
    decision: str          # "deliver" | "suppress" | "defer"
    reason: str
    priority: str          # "low" | "normal" | "high" | "critical"
    cooldown_seconds: int
    requires_user_opt_in: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProactivePolicy:
    """Rule-based proactive delivery policy."""

    def __init__(self, enabled: bool | None = None) -> None:
        self._enabled = enabled

    @staticmethod
    def is_feature_enabled() -> bool:
        raw = os.environ.get("JARVIS_PROACTIVE_ENABLED", "").strip().lower()
        if raw in _DISABLED_VALUES:
            return False
        return raw in {"1", "true", "yes", "on"}

    def _feature_enabled(self) -> bool:
        if self._enabled is not None:
            return self._enabled
        return self.is_feature_enabled()

    def decide(
        self,
        state: dict[str, Any] | None = None,
        now: float | None = None,
        user_settings: dict[str, Any] | None = None,
        last_delivery_at: float | None = None,
    ) -> ProactiveDecision:
        state = state or {}
        user_settings = user_settings or {}
        priority = str(state.get("priority", "normal")).lower()
        _now = now if now is not None else time.time()

        # 1. Feature flag disabled
        if not self._feature_enabled():
            return ProactiveDecision(
                decision="suppress",
                reason="proactive_disabled",
                priority=priority,
                cooldown_seconds=0,
                requires_user_opt_in=True,
            )

        # 2. Muted user
        if user_settings.get("muted"):
            return ProactiveDecision(
                decision="suppress",
                reason="user_muted",
                priority=priority,
                cooldown_seconds=0,
                requires_user_opt_in=True,
            )

        # 3. DND — defer unless critical
        in_dnd = bool(user_settings.get("dnd") or state.get("dnd"))
        if in_dnd and priority not in ("critical",):
            return ProactiveDecision(
                decision="defer",
                reason="dnd_active",
                priority=priority,
                cooldown_seconds=300,
                requires_user_opt_in=False,
            )

        # 4. Cooldown
        if last_delivery_at is not None:
            elapsed = _now - last_delivery_at
            cooldown = self._cooldown_for(priority)
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                action = "suppress" if priority in ("low", "normal") else "defer"
                return ProactiveDecision(
                    decision=action,
                    reason=f"cooldown_active_{remaining}s_remaining",
                    priority=priority,
                    cooldown_seconds=remaining,
                    requires_user_opt_in=False,
                )

        # 5. Deliver
        cooldown_sec = self._cooldown_for(priority)
        return ProactiveDecision(
            decision="deliver",
            reason="policy_allows_delivery",
            priority=priority,
            cooldown_seconds=cooldown_sec,
            requires_user_opt_in=False,
        )

    @staticmethod
    def _cooldown_for(priority: str) -> int:
        return {
            "low": 600,
            "normal": 300,
            "high": 120,
            "critical": 60,
        }.get(priority, 300)
