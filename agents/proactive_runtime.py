"""ProactiveRuntime - FAZ-3-E1 runtime seam.

Connects ProactiveDelivery planning layer to an injected sender.
No network, no Telegram imports, no scheduler, no env reads.
"""

from __future__ import annotations

from agents.proactive_delivery import DeliveryPlan, deliver


def run_proactive_delivery(
    plan: DeliveryPlan,
    chat_id_resolver=None,
    sender_factory=None,
) -> bool:
    """Wire a ready DeliveryPlan to an injected sender.

    chat_id_resolver: callable(user_id: str) -> str | None
    sender_factory:   callable(chat_id: str) -> callable(user_id: str, text: str) -> None
    Returns True if delivered, False otherwise. Never raises.
    """
    if plan.status != "ready":
        return False
    if chat_id_resolver is None:
        return False
    if sender_factory is None:
        return False
    try:
        chat_id = chat_id_resolver(plan.user_id)
    except Exception:
        return False
    if not chat_id:
        return False
    try:
        sender_fn = sender_factory(chat_id)
    except Exception:
        return False
    return deliver(plan, sender_fn=sender_fn)
