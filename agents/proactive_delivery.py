"""ProactiveDelivery - FAZ-3-E1 planning layer.

Converts a ProactiveDecision into a safe DeliveryPlan object.
Pure and deterministic: no network, no Telegram, no scheduler, no runtime send.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from agents.proactive_policy import ProactiveDecision

_ALLOWED_CHANNELS = frozenset({"telegram"})


@dataclass(frozen=True)
class DeliveryPlan:
    status: str
    channel: str
    user_id: str
    task_id: str
    reason: str
    priority: str
    created_at: str
    cooldown_seconds: int
    requires_user_opt_in: bool


def create_delivery_plan(
    decision: ProactiveDecision,
    *,
    user_id: str,
    task_id: str,
    channel: str = "telegram",
    now: datetime | None = None,
) -> DeliveryPlan | None:
    if not user_id:
        raise ValueError("user_id must be non-empty")
    if not task_id:
        raise ValueError("task_id must be non-empty")
    if channel not in _ALLOWED_CHANNELS:
        raise ValueError(f"unknown channel: {channel!r}; allowed: {sorted(_ALLOWED_CHANNELS)}")
    if decision.requires_user_opt_in:
        return None
    if decision.decision == "suppress":
        return None

    created_at = (now if now is not None else datetime.now(timezone.utc)).isoformat()

    if decision.decision == "deliver":
        status = "ready"
    elif decision.decision == "defer":
        status = "deferred"
    else:
        return None

    return DeliveryPlan(
        status=status,
        channel=channel,
        user_id=user_id,
        task_id=task_id,
        reason=decision.reason,
        priority=decision.priority,
        created_at=created_at,
        cooldown_seconds=decision.cooldown_seconds,
        requires_user_opt_in=decision.requires_user_opt_in,
    )


def _format_delivery_message(plan: DeliveryPlan) -> str:
    return (
        f"JARVIS alert\n"
        f"task: {plan.task_id}\n"
        f"priority: {plan.priority}\n"
        f"reason: {plan.reason}"
    )


def deliver(plan: DeliveryPlan, sender_fn=None) -> bool:
    """Execute a ready DeliveryPlan via injected sender.

    sender_fn: callable(user_id: str, text: str) -> None, or None for noop.
    Returns True if sent, False otherwise. Never raises.
    """
    if not isinstance(plan, DeliveryPlan):
        return False
    if sender_fn is None:
        return False
    if plan.status != "ready":
        return False
    try:
        sender_fn(plan.user_id, _format_delivery_message(plan))
        return True
    except Exception:
        return False
