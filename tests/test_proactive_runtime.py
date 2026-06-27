"""Tests for ProactiveRuntime wiring seam - FAZ-3-E1-S3A."""

import ast

import pytest

from agents.proactive_delivery import DeliveryPlan, DeliveryResult, create_delivery_plan
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


# 2. no resolver → DeliveryResult(sent=False, reason=no_resolver)
def test_no_resolver_returns_false():
    plan = _ready_plan()
    result = run_proactive_delivery(plan, chat_id_resolver=None, sender_factory=lambda cid: None)
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "no_resolver"


# 3. resolver returns None → DeliveryResult(sent=False, reason=no_chat_id)
def test_resolver_returns_none_returns_false():
    plan = _ready_plan()
    result = run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: None,
        sender_factory=lambda cid: lambda uid, txt: None,
    )
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "no_chat_id"


# 4. resolver returns empty string → DeliveryResult(sent=False, reason=no_chat_id)
def test_resolver_returns_empty_string_returns_false():
    plan = _ready_plan()
    result = run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "",
        sender_factory=lambda cid: lambda uid, txt: None,
    )
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "no_chat_id"


# 5. no sender_factory → DeliveryResult(sent=False, reason=no_sender_factory)
def test_no_sender_factory_returns_false():
    plan = _ready_plan()
    result = run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "42",
        sender_factory=None,
    )
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "no_sender_factory"


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
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "not_ready"
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


# 8. ready plan calls sender exactly once and returns sent=True
def test_ready_plan_calls_sender_once_and_returns_true():
    plan = _ready_plan()
    calls = []
    result = run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "42",
        sender_factory=lambda cid: lambda uid, txt: calls.append((uid, txt)),
    )
    assert isinstance(result, DeliveryResult)
    assert result.sent is True
    assert result.reason == "sent"
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


# 10. resolver exception → DeliveryResult(sent=False, reason=resolver_error)
def test_resolver_exception_returns_false():
    plan = _ready_plan()
    def _bad_resolver(uid):
        raise RuntimeError("lookup failed")
    result = run_proactive_delivery(
        plan,
        chat_id_resolver=_bad_resolver,
        sender_factory=lambda cid: lambda uid, txt: None,
    )
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "resolver_error"
    assert result.error is not None


# 11. sender_factory exception → DeliveryResult(sent=False, reason=factory_error)
def test_sender_factory_exception_returns_false():
    plan = _ready_plan()
    def _bad_factory(cid):
        raise RuntimeError("factory failed")
    result = run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "42",
        sender_factory=_bad_factory,
    )
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "factory_error"
    assert result.error is not None


# 12. sender exception → DeliveryResult(sent=False, reason=sender_error)
def test_sender_exception_returns_false():
    plan = _ready_plan()
    def _bad_sender(uid, txt):
        raise RuntimeError("send failed")
    result = run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "42",
        sender_factory=lambda cid: _bad_sender,
    )
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "sender_error"


# ---- invalid plan guard tests ----

# 14: run_proactive_delivery(None) → DeliveryResult(sent=False, reason=invalid_plan)
def test_run_none_plan_returns_false():
    result = run_proactive_delivery(
        None,
        chat_id_resolver=lambda uid: "42",
        sender_factory=lambda cid: lambda uid, txt: None,
    )
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "invalid_plan"
    assert result.plan_status is None


# 15: run_proactive_delivery(object()) → DeliveryResult(sent=False, reason=invalid_plan)
def test_run_invalid_plan_returns_false():
    result = run_proactive_delivery(
        object(),
        chat_id_resolver=lambda uid: "42",
        sender_factory=lambda cid: lambda uid, txt: None,
    )
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "invalid_plan"


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
