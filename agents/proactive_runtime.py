"""ProactiveRuntime - FAZ-3-E1 runtime seam.

Connects ProactiveDelivery planning layer to an injected sender.
No network, no Telegram imports, no scheduler, no env reads.
"""

from __future__ import annotations

from datetime import datetime, timezone

from agents.proactive_delivery import DeliveryPlan, DeliveryResult, deliver


def run_proactive_delivery(
    plan: DeliveryPlan,
    chat_id_resolver=None,
    sender_factory=None,
) -> DeliveryResult:
    """Wire a ready DeliveryPlan to an injected sender.

    chat_id_resolver: callable(user_id: str) -> str | None
    sender_factory:   callable(chat_id: str) -> callable(user_id: str, text: str) -> None
    Never raises. Returns DeliveryResult with full status information.
    """
    ts = datetime.now(timezone.utc).isoformat()

    if not isinstance(plan, DeliveryPlan):
        return DeliveryResult(
            sent=False, dry_run=False, plan_status=None,
            reason="invalid_plan", error=None, ts=ts,
        )
    if plan.status != "ready":
        return DeliveryResult(
            sent=False, dry_run=False, plan_status=plan.status,
            reason="not_ready", error=None, ts=ts,
        )
    if chat_id_resolver is None:
        return DeliveryResult(
            sent=False, dry_run=False, plan_status=plan.status,
            reason="no_resolver", error=None, ts=ts,
        )
    if sender_factory is None:
        return DeliveryResult(
            sent=False, dry_run=False, plan_status=plan.status,
            reason="no_sender_factory", error=None, ts=ts,
        )

    try:
        chat_id = chat_id_resolver(plan.user_id)
    except Exception as exc:
        return DeliveryResult(
            sent=False, dry_run=False, plan_status=plan.status,
            reason="resolver_error", error=str(exc), ts=ts,
        )

    if not chat_id:
        return DeliveryResult(
            sent=False, dry_run=False, plan_status=plan.status,
            reason="no_chat_id", error=None, ts=ts,
        )

    try:
        sender_fn = sender_factory(chat_id)
    except Exception as exc:
        return DeliveryResult(
            sent=False, dry_run=False, plan_status=plan.status,
            reason="factory_error", error=str(exc), ts=ts,
        )

    return deliver(plan, sender_fn=sender_fn)
