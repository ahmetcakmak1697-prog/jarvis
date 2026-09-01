"""ExecutionPolicy - separates cognitive level from execution destination.

This module decides WHERE a routed task should run without changing the
ModelCascade level semantics.

Definitions:
- level: cognitive complexity from router/cascade, e.g. L1/L2/L3/L4
- destination: execution destination, e.g. local/cloud_api/premium_gate/blocked
- primary_executor: engine key, e.g. ollama/api
- fallback_executor: safe fallback engine, usually ollama

Scope:
- No model calls
- No API calls
- No LiteLLM
- No Ollama
- No cost ledger mutation
"""
from __future__ import annotations

from typing import Any, Iterable


_BLOCKED_DECISIONS = {"redacted_blocked", "external_blocked"}
_LOCAL_ROUTES = {"knowledge_card", "memory", "cache"}


class ExecutionPolicy:
    """Pure policy layer for executor destination decisions."""

    def __init__(
        self,
        *,
        cloud_api_enabled: bool = False,
        cloud_levels: Iterable[str] | None = None,
    ) -> None:
        self.cloud_api_enabled = bool(cloud_api_enabled)
        self.cloud_levels = {str(x).upper() for x in (cloud_levels or set())}

    def choose(self, router_decision: dict[str, Any] | None) -> dict[str, Any]:
        rd = router_decision or {}
        decision = str(rd.get("decision") or "")
        route = str(rd.get("route") or "")
        cascade = rd.get("cascade") or {}
        level = str(cascade.get("level") or "L2").upper()

        if decision == "answer_local" and route in _LOCAL_ROUTES:
            return {
                "level": "L0",
                "destination": "local_answer",
                "primary_executor": None,
                "fallback_executor": None,
                "requires_approval": False,
                "reason": "router_local_answer",
            }

        if decision in _BLOCKED_DECISIONS:
            return {
                "level": level,
                "destination": "blocked",
                "primary_executor": None,
                "fallback_executor": None,
                "requires_approval": False,
                "reason": decision,
            }

        if decision != "ask_external":
            return {
                "level": level,
                "destination": "no_execution",
                "primary_executor": None,
                "fallback_executor": None,
                "requires_approval": False,
                "reason": decision or "unknown_router_decision",
            }

        if level == "L4":
            return {
                "level": "L4",
                "destination": "premium_gate",
                "primary_executor": None,
                "fallback_executor": "ollama",
                "requires_approval": True,
                "reason": "premium_level_requires_approval",
            }

        if self.cloud_api_enabled and level in self.cloud_levels:
            return {
                "level": level,
                "destination": "cloud_api",
                "primary_executor": "api",
                "fallback_executor": "ollama",
                "requires_approval": False,
                "reason": "cloud_api_enabled_for_level",
            }

        return {
            "level": level,
            "destination": "local",
            "primary_executor": "ollama",
            "fallback_executor": None,
            "requires_approval": False,
            "reason": "local_first_default",
        }
