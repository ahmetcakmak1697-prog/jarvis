"""ProactiveRunner - E1-S6A one-shot dry-run CLI.

Triggered by Windows Task Scheduler or run manually.
Evaluates proactive policy and optionally delivers an alert.

Default mode: dry-run (no Telegram send, no network, no .env needed).
--live mode:  requires JARVIS_PROACTIVE_ENABLED=1 (guard only in E1-S6A;
              actual live send wired in E1-S4 after smoke test).

Exit codes: 0 = success, 1 = error.
Output: single JSON line to stdout.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

from agents.proactive_delivery import DeliveryPlan, create_delivery_plan, deliver
from agents.proactive_policy import ProactivePolicy


def _check_live_gate() -> None:
    """Raise RuntimeError if JARVIS_PROACTIVE_ENABLED is not set to '1'."""
    val = os.environ.get("JARVIS_PROACTIVE_ENABLED", "").strip()
    if val != "1":
        raise RuntimeError(
            "LIVE MODE BLOCKED: set JARVIS_PROACTIVE_ENABLED=1 and complete "
            f"E1-S4 live Telegram smoke first. Current value: {val!r}"
        )


def run_once(
    state: dict[str, Any] | None = None,
    *,
    dry_run: bool = True,
    user_id: str = "ahmet",
    task_id: str = "morning_brief",
) -> dict[str, Any]:
    """Evaluate policy, build delivery plan, and optionally deliver.

    Always safe to call: no network, no .env reads, no side effects in dry-run.
    Returns a result dict suitable for JSON serialisation.
    """
    policy = ProactivePolicy()
    decision = policy.decide(state=state or {})

    plan: DeliveryPlan | None = None
    if decision.decision != "suppress":
        plan = create_delivery_plan(decision, user_id=user_id, task_id=task_id)

    sent = False
    if not dry_run and plan is not None:
        # Live sender not wired in E1-S6A. Wired in E1-S4 after smoke.
        # Guard already passed (_check_live_gate) so env is set, but no-op here.
        sent = deliver(plan, sender_fn=None)

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "decision": decision.decision,
        "reason": decision.reason,
        "priority": decision.priority,
        "plan_status": plan.status if plan is not None else None,
        "sent": sent,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code."""
    if argv is None:
        argv = sys.argv[1:]

    live = "--live" in argv
    dry_run = not live

    try:
        if live:
            _check_live_gate()
        result = run_once(dry_run=dry_run)
        print(json.dumps(result))
        return 0
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc), "dry_run": dry_run, "sent": False}),
              file=sys.stderr)
        return 1
    except Exception as exc:
        print(json.dumps({"error": f"unexpected: {exc}", "dry_run": dry_run, "sent": False}),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
