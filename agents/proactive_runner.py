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
import sys
from datetime import datetime, timezone
from typing import Any

from agents.proactive_delivery import DeliveryPlan, create_delivery_plan, deliver
from agents.proactive_policy import ProactivePolicy

_LIVE_NOT_IMPLEMENTED = (
    "LIVE DELIVERY NOT IMPLEMENTED: complete E1-S4 live Telegram smoke first. "
    "Live send will be wired after E1-S4 sign-off."
)


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

    policy = ProactivePolicy()
    decision = policy.decide(state=state or {})

    plan: DeliveryPlan | None = None
    if decision.decision != "suppress":
        plan = create_delivery_plan(decision, user_id=user_id, task_id=task_id)

    # dry-run: DeliveryResult.sent is always False; structured result available for logging
    delivery = deliver(plan, sender_fn=None, dry_run=True) if plan is not None else None
    sent = delivery.sent if delivery is not None else False

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "decision": decision.decision,
        "reason": decision.reason,
        "priority": decision.priority,
        "plan_status": plan.status if plan is not None else None,
        "sent": sent,
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
