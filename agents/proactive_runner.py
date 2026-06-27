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
