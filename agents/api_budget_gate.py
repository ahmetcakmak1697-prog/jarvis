"""APIBudgetGate - fail-closed budget gate for cloud API execution.

Purpose:
- Protect the real API execution path from uncontrolled spending.
- Keep AssistantExecutor unaware of daily limit details.
- Wrap CostLedger behind a small dependency-injected gate.
- Fail closed on ledger errors.

Scope:
- No API calls
- No router decisions
- No model selection
"""
from __future__ import annotations

import threading
from typing import Any


class APIBudgetGate:
    """Small fail-closed gate around a ledger-like object."""

    def __init__(
        self,
        *,
        ledger: Any | None = None,
        call_type: str = "api_call",
        fail_closed: bool = True,
    ) -> None:
        self._ledger = ledger
        self._call_type = str(call_type or "api_call")
        self._fail_closed = bool(fail_closed)
        self._lock = threading.RLock()

    def _get_ledger(self) -> Any:
        if self._ledger is not None:
            return self._ledger

        from agents.cost_ledger import CostLedger

        self._ledger = CostLedger()
        return self._ledger

    def check_and_consume(
        self,
        *,
        provider: str | None = None,
        level: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Check and consume one API call budget unit.

        Returns a normalized dict with allowed=True/False.
        Any ledger exception becomes a fail-closed deny by default.
        """
        with self._lock:
            try:
                ledger = self._get_ledger()
                raw = ledger.check_and_consume(self._call_type, dry_run=dry_run)
                allowed = bool(raw.get("allowed"))
                return {
                    "allowed": allowed,
                    "reason": raw.get("reason", "unknown"),
                    "provider": provider,
                    "level": level,
                    "call_type": self._call_type,
                    "ledger": raw,
                }
            except Exception as exc:
                return {
                    "allowed": not self._fail_closed,
                    "reason": "budget_gate_error",
                    "provider": provider,
                    "level": level,
                    "call_type": self._call_type,
                    "error": str(exc),
                }
