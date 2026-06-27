"""ProactiveRunner - E1-S6A one-shot dry-run CLI.

Triggered by Windows Task Scheduler or run manually from repo root.
Evaluates proactive policy and logs what would be delivered.

SUPPORTED INVOCATION (from repo root):
    py -3.11 -m agents.proactive_runner [--dry-run] [--live]

Direct file invocation (py agents/proactive_runner.py) is NOT supported
because 'agents' is not on sys.path without -m.

Default mode: --dry-run (no Telegram, no network, no .env needed).
--live mode:  NOT IMPLEMENTED until E1-S4 live Telegram smoke completes.
              Always raises RuntimeError in E1-S6A regardless of env vars.

Exit codes: 0 = success, 1 = error / not-implemented.
Output: single JSON line to stdout.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any

from agents.proactive_delivery import DeliveryPlan, create_delivery_plan, deliver
from agents.proactive_policy import ProactivePolicy

_LIVE_NOT_IMPLEMENTED = (
    "LIVE DELIVERY NOT IMPLEMENTED: complete E1-S4 live Telegram smoke first. "
    "Live send will be wired after E1-S4 sign-off."
)

_DEFAULT_COOLDOWN_SECONDS = 1800

_E1_S4_SMOKE_MESSAGE = (
    "JARVIS E1-S4 live Telegram smoke test. "
    "If you received this, live delivery path works."
)


def _check_throttle(state: dict[str, Any]) -> str | None:
    """Return a throttle reason if delivery should be suppressed, else None.

    Reasons:
      "cooldown_active"       — last_delivery_ts within cooldown window
      "throttle_state_invalid" — last_delivery_ts or cooldown_seconds is malformed
    Returns None when no throttle applies (no last_delivery_ts, or cooldown elapsed).
    """
    last_ts = state.get("last_delivery_ts")
    if last_ts is None:
        return None

    cooldown_raw = state.get("cooldown_seconds", _DEFAULT_COOLDOWN_SECONDS)
    try:
        cooldown = float(cooldown_raw)
        if not math.isfinite(cooldown) or cooldown < 0:
            raise ValueError("non-finite or negative")
    except (TypeError, ValueError):
        return "throttle_state_invalid"

    try:
        last_dt = datetime.fromisoformat(str(last_ts))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
        if elapsed < cooldown:
            return "cooldown_active"
    except (TypeError, ValueError, AttributeError):
        return "throttle_state_invalid"

    return None


def run_once(
    state: dict[str, Any] | None = None,
    *,
    dry_run: bool = True,
    user_id: str = "ahmet",
    task_id: str = "morning_brief",
) -> dict[str, Any]:
    """Evaluate policy, build delivery plan, and log result.

    dry_run=True  (default): no send, no network, no side effects. Always safe.
    dry_run=False: raises RuntimeError — live delivery not implemented until E1-S4.

    Does NOT use ProactiveCore.evaluate(); wires ProactivePolicy directly.
    ProactiveCore wiring is deferred to a later sub-task.

    Returns a JSON-serialisable result dict.
    """
    if not dry_run:
        raise RuntimeError(_LIVE_NOT_IMPLEMENTED)

    state = state or {}

    throttle_reason = _check_throttle(state)
    if throttle_reason is not None:
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "decision": "suppress",
            "reason": throttle_reason,
            "priority": "normal",
            "plan_status": None,
            "sent": False,
            "delivery": None,
        }

    policy = ProactivePolicy()
    decision = policy.decide(state=state)

    plan: DeliveryPlan | None = None
    if decision.decision != "suppress":
        plan = create_delivery_plan(decision, user_id=user_id, task_id=task_id)

    # dry-run: structured DeliveryResult preserved for logging; sent always False here
    delivery = deliver(plan, sender_fn=None, dry_run=True) if plan is not None else None

    delivery_dict = (
        {
            "sent": delivery.sent,
            "dry_run": delivery.dry_run,
            "plan_status": delivery.plan_status,
            "reason": delivery.reason,
            "error": delivery.error,
            "ts": delivery.ts,
        }
        if delivery is not None
        else None
    )

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "decision": decision.decision,
        "reason": decision.reason,
        "priority": decision.priority,
        "plan_status": plan.status if plan is not None else None,
        "sent": delivery.sent if delivery is not None else False,
        "delivery": delivery_dict,
    }


def run_e1_s4_smoke(
    send_fn=None,
    *,
    token: str | None = None,
    chat_id: str | None = None,
) -> dict[str, Any]:
    """Send exactly one E1-S4 smoke message via injected or env-configured sender.

    send_fn: callable(text: str) -> None. If None, built from token+chat_id via HTTP.
    token, chat_id: if None, read from TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID env vars.

    Never retries. Never raises. Returns structured result dict.
    Token and chat_id values are never included in the result — only SET/NOT SET hints.
    """
    if token is None:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if chat_id is None:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    token_hint = f"SET hidden length={len(token)}" if token else "NOT SET"
    chat_id_hint = f"SET hidden length={len(chat_id)}" if chat_id else "NOT SET"
    ts = datetime.now(timezone.utc).isoformat()

    if not token:
        return {
            "sent": False,
            "reason": "missing_token",
            "token": token_hint,
            "chat_id": chat_id_hint,
            "error": "TELEGRAM_BOT_TOKEN not set in environment",
            "ts": ts,
        }
    if not chat_id:
        return {
            "sent": False,
            "reason": "missing_chat_id",
            "token": token_hint,
            "chat_id": chat_id_hint,
            "error": "TELEGRAM_CHAT_ID not set in environment",
            "ts": ts,
        }

    if send_fn is None:
        from agents.e1_s4_smoke_sender import make_telegram_http_send_fn
        send_fn = make_telegram_http_send_fn(token, chat_id)

    try:
        send_fn(_E1_S4_SMOKE_MESSAGE)
        return {
            "sent": True,
            "reason": "sent",
            "token": token_hint,
            "chat_id": chat_id_hint,
            "message": _E1_S4_SMOKE_MESSAGE,
            "ts": ts,
        }
    except Exception as exc:
        return {
            "sent": False,
            "reason": "send_error",
            "token": token_hint,
            "chat_id": chat_id_hint,
            "error": str(exc),
            "ts": ts,
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py -3.11 -m agents.proactive_runner",
        description="JARVIS proactive runner — one-shot, dry-run by default.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Dry-run mode (default when no flag is given).",
    )
    group.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Live mode — NOT IMPLEMENTED until E1-S4.",
    )
    group.add_argument(
        "--e1-s4-smoke",
        action="store_true",
        default=False,
        help="E1-S4 one-off smoke: sends exactly one message if credentials set.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code (0 = success, 1 = error)."""
    if argv is None:
        argv = sys.argv[1:]

    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 1

    if args.e1_s4_smoke:
        result = run_e1_s4_smoke()
        if result["sent"]:
            print(json.dumps(result))
            return 0
        print(json.dumps(result), file=sys.stderr)
        return 1

    live = args.live
    dry_run = not live

    try:
        result = run_once(dry_run=dry_run)
        print(json.dumps(result))
        return 0
    except RuntimeError as exc:
        print(
            json.dumps({"error": str(exc), "dry_run": dry_run, "sent": False}),
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(
            json.dumps({"error": f"unexpected: {exc}", "dry_run": dry_run, "sent": False}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
