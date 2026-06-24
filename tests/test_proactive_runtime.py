"""Tests for ProactiveRuntime wiring seam - FAZ-3-E1-S3A."""

import ast

import pytest

from agents.proactive_delivery import DeliveryPlan, create_delivery_plan
from agents.proactive_policy import ProactiveDecision
from agents.proactive_runtime import run_proactive_delivery


def _ready_plan(user_id: str = "user1", task_id: str = "task1") -> DeliveryPlan:
    d = ProactiveDecision(
        decision="deliver",
        reason="policy_allows_delivery",
        priority="normal",
        cooldown_seconds=300,
        requires_user_opt_in=False,
    )
    plan = create_delivery_plan(d, user_id=user_id, task_id=task_id)
    assert plan is not None
    return plan


def _deferred_plan() -> DeliveryPlan:
    d = ProactiveDecision(
        decision="defer",
        reason="dnd_active",
        priority="normal",
        cooldown_seconds=300,
        requires_user_opt_in=False,
    )
    plan = create_delivery_plan(d, user_id="user1", task_id="task1")
    assert plan is not None
    return plan


# 1. module imports without error
def test_module_imports():
    from agents.proactive_runtime import run_proactive_delivery as fn
    assert callable(fn)


# 2. no resolver → False
def test_no_resolver_returns_false():
    plan = _ready_plan()
    assert run_proactive_delivery(plan, chat_id_resolver=None, sender_factory=lambda cid: None) is False


# 3. resolver returns None → False
def test_resolver_returns_none_returns_false():
    plan = _ready_plan()
    assert run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: None,
        sender_factory=lambda cid: lambda uid, txt: None,
    ) is False


# 4. resolver returns empty string → False
def test_resolver_returns_empty_string_returns_false():
    plan = _ready_plan()
    assert run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "",
        sender_factory=lambda cid: lambda uid, txt: None,
    ) is False


# 5. no sender_factory → False
def test_no_sender_factory_returns_false():
    plan = _ready_plan()
    assert run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "42",
        sender_factory=None,
    ) is False


# 6. not-ready (deferred) plan does not call resolver or factory
def test_deferred_plan_does_not_call_resolver_or_factory():
    plan = _deferred_plan()
    resolver_calls = []
    factory_calls = []
    result = run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: resolver_calls.append(uid) or "42",
        sender_factory=lambda cid: factory_calls.append(cid) or (lambda uid, txt: None),
    )
    assert result is False
    assert resolver_calls == []
    assert factory_calls == []


# 7. ready plan calls resolver once with correct user_id
def test_ready_plan_calls_resolver_with_user_id():
    plan = _ready_plan(user_id="ahmet123")
    resolved = []
    sent = []
    run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: resolved.append(uid) or "99",
        sender_factory=lambda cid: lambda uid, txt: sent.append((uid, txt)),
    )
    assert resolved == ["ahmet123"]


# 8. ready plan calls sender exactly once and returns True
def test_ready_plan_calls_sender_once_and_returns_true():
    plan = _ready_plan()
    calls = []
    result = run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "42",
        sender_factory=lambda cid: lambda uid, txt: calls.append((uid, txt)),
    )
    assert result is True
    assert len(calls) == 1


# 9. sender_factory receives resolved chat_id
def test_sender_factory_receives_chat_id():
    plan = _ready_plan()
    factory_args = []
    run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "telegram_99",
        sender_factory=lambda cid: factory_args.append(cid) or (lambda uid, txt: None),
    )
    assert factory_args == ["telegram_99"]


# 10. resolver exception returns False
def test_resolver_exception_returns_false():
    plan = _ready_plan()
    def _bad_resolver(uid):
        raise RuntimeError("lookup failed")
    assert run_proactive_delivery(
        plan,
        chat_id_resolver=_bad_resolver,
        sender_factory=lambda cid: lambda uid, txt: None,
    ) is False


# 11. sender_factory exception returns False
def test_sender_factory_exception_returns_false():
    plan = _ready_plan()
    def _bad_factory(cid):
        raise RuntimeError("factory failed")
    assert run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "42",
        sender_factory=_bad_factory,
    ) is False


# 12. sender exception returns False
def test_sender_exception_returns_false():
    plan = _ready_plan()
    def _bad_sender(uid, txt):
        raise RuntimeError("send failed")
    assert run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "42",
        sender_factory=lambda cid: _bad_sender,
    ) is False


# 13. no real Telegram import / no tools.telegram_agent import
def test_no_telegram_import_in_module():
    with open("agents/proactive_runtime.py", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "telegram" not in alias.name.lower(), f"forbidden import: {alias.name}"
        if isinstance(node, ast.ImportFrom):
            if node.module:
                assert "telegram" not in node.module.lower(), f"forbidden import from {node.module}"
                assert "tools" not in node.module.lower(), f"forbidden import from {node.module}"
