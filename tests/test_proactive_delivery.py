"""Tests for ProactiveDelivery planning layer - FAZ-3-E1."""

import ast
import sys
from datetime import datetime, timezone

import pytest

from agents.proactive_delivery import DeliveryPlan, create_delivery_plan
from agents.proactive_policy import ProactiveDecision


def _decision(
    decision: str = "deliver",
    reason: str = "policy_allows_delivery",
    priority: str = "normal",
    cooldown_seconds: int = 300,
    requires_user_opt_in: bool = False,
) -> ProactiveDecision:
    return ProactiveDecision(
        decision=decision,
        reason=reason,
        priority=priority,
        cooldown_seconds=cooldown_seconds,
        requires_user_opt_in=requires_user_opt_in,
    )


# 1. test_deliver_plan_created
def test_deliver_plan_created():
    d = _decision(decision="deliver")
    plan = create_delivery_plan(d, user_id="user1", task_id="task1")
    assert plan is not None
    assert plan.status == "ready"
    assert plan.user_id == "user1"
    assert plan.task_id == "task1"


# 2. test_suppress_returns_none
def test_suppress_returns_none():
    d = _decision(decision="suppress")
    plan = create_delivery_plan(d, user_id="user1", task_id="task1")
    assert plan is None


# 3. test_defer_creates_deferred_plan
def test_defer_creates_deferred_plan():
    d = _decision(decision="defer", reason="dnd_active")
    plan = create_delivery_plan(d, user_id="user1", task_id="task1")
    assert plan is not None
    assert plan.status == "deferred"
    assert plan.reason == "dnd_active"


# 4. test_delivery_plan_schema
def test_delivery_plan_schema():
    d = _decision(decision="deliver", reason="policy_allows_delivery", priority="high", cooldown_seconds=120)
    now = datetime(2025, 6, 22, 12, 0, 0, tzinfo=timezone.utc)
    plan = create_delivery_plan(d, user_id="user1", task_id="task1", now=now)
    assert plan is not None
    for attr in ("status", "channel", "user_id", "task_id", "reason", "priority", "created_at", "cooldown_seconds", "requires_user_opt_in"):
        assert hasattr(plan, attr)
    assert plan.status == "ready"
    assert plan.channel == "telegram"
    assert plan.user_id == "user1"
    assert plan.task_id == "task1"
    assert plan.reason == "policy_allows_delivery"
    assert plan.priority == "high"
    assert plan.created_at == "2025-06-22T12:00:00+00:00"
    assert plan.cooldown_seconds == 120
    assert plan.requires_user_opt_in is False


# 5. test_unknown_channel_fails_closed
def test_unknown_channel_fails_closed():
    d = _decision(decision="deliver")
    with pytest.raises(ValueError, match="unknown channel"):
        create_delivery_plan(d, user_id="user1", task_id="task1", channel="slack")


# 6. test_missing_user_id_fails_closed
def test_missing_user_id_fails_closed():
    d = _decision(decision="deliver")
    with pytest.raises(ValueError, match="user_id"):
        create_delivery_plan(d, user_id="", task_id="task1")


# 7. test_missing_task_id_fails_closed
def test_missing_task_id_fails_closed():
    d = _decision(decision="deliver")
    with pytest.raises(ValueError, match="task_id"):
        create_delivery_plan(d, user_id="user1", task_id="")


# 8. test_requires_user_opt_in_returns_none
def test_requires_user_opt_in_returns_none():
    d = _decision(decision="deliver", requires_user_opt_in=True)
    plan = create_delivery_plan(d, user_id="user1", task_id="task1")
    assert plan is None


# 9. test_no_network_imports_in_module
def test_no_network_imports_in_module():
    with open("agents/proactive_delivery.py", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                assert name not in ("requests", "urllib", "httpx", "telegram"), f"forbidden import: {name}"
        if isinstance(node, ast.ImportFrom):
            if node.module and any(x in node.module for x in ("requests", "urllib", "httpx", "telegram")):
                pytest.fail(f"forbidden import from {node.module}")


# 10. test_no_scheduler_or_background_imports_in_module
def test_no_scheduler_or_background_imports_in_module():
    with open("agents/proactive_delivery.py", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    _FORBIDDEN_MODULES = frozenset({"threading", "asyncio", "schedule"})
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in _FORBIDDEN_MODULES, f"forbidden import: {alias.name}"
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module in _FORBIDDEN_MODULES:
                pytest.fail(f"forbidden import from {node.module}")


# 11. test_module_has_no_send_function
def test_module_has_no_send_function():
    with open("agents/proactive_delivery.py", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if "send" in node.name.lower():
                pytest.fail(f"found send-related function: {node.name}")


# 12. test_created_at_is_deterministic_with_now
def test_created_at_is_deterministic_with_now():
    d = _decision(decision="deliver")
    now = datetime(2025, 6, 22, 12, 0, 0, tzinfo=timezone.utc)
    plan1 = create_delivery_plan(d, user_id="user1", task_id="task1", now=now)
    plan2 = create_delivery_plan(d, user_id="user1", task_id="task1", now=now)
    assert plan1 is not None
    assert plan2 is not None
    assert plan1.created_at == plan2.created_at
    assert plan1.created_at == "2025-06-22T12:00:00+00:00"
