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


@dataclass(frozen=True)
class DeliveryResult:
    """Structured result from deliver() or run_proactive_delivery().

    Replaces bare bool return to enable debugging without silent failures.

    Reason codes:
      sent            — sender called successfully
      noop_dry_run    — dry_run=True; no sender attempted
      noop_no_sender  — sender_fn is None; no sender attempted
      not_ready       — plan.status != "ready"
      invalid_plan    — plan is not a DeliveryPlan
      sender_error    — sender raised an exception
    """

    sent: bool
    dry_run: bool
    plan_status: str | None
    reason: str
    error: str | None
    ts: str


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


def deliver(
    plan: DeliveryPlan,
    sender_fn=None,
    *,
    dry_run: bool = False,
) -> DeliveryResult:
    """Execute a ready DeliveryPlan via injected sender.

    sender_fn: callable(user_id: str, text: str) -> None, or None for noop.
    dry_run:   True to skip sender entirely and return noop result.
    Never raises. Returns DeliveryResult with full status information.
    """
    ts = datetime.now(timezone.utc).isoformat()

    if not isinstance(plan, DeliveryPlan):
        return DeliveryResult(
            sent=False, dry_run=dry_run, plan_status=None,
            reason="invalid_plan", error=None, ts=ts,
        )

    if dry_run:
        return DeliveryResult(
            sent=False, dry_run=True, plan_status=plan.status,
            reason="noop_dry_run", error=None, ts=ts,
        )

    # Readiness check before sender check: a not-ready plan is not_ready regardless
    # of whether a sender is provided.
    if plan.status != "ready":
        return DeliveryResult(
            sent=False, dry_run=False, plan_status=plan.status,
            reason="not_ready", error=None, ts=ts,
        )

    if sender_fn is None:
        return DeliveryResult(
            sent=False, dry_run=False, plan_status=plan.status,
            reason="noop_no_sender", error=None, ts=ts,
        )

    try:
        sender_fn(plan.user_id, _format_delivery_message(plan))
        return DeliveryResult(
            sent=True, dry_run=False, plan_status=plan.status,
            reason="sent", error=None, ts=ts,
        )
    except Exception as exc:
        return DeliveryResult(
            sent=False, dry_run=False, plan_status=plan.status,
            reason="sender_error", error=str(exc), ts=ts,
        )
