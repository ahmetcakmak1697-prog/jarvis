"""E1-S6B: DeliveryResult struct regression tests.

Verifies that deliver() and run_proactive_delivery() return a structured
DeliveryResult instead of a bare bool, with all required fields populated.

Contract:
  DeliveryResult(sent, dry_run, plan_status, reason, error, ts)

Reason codes for deliver():
  sent            — sender called successfully
  noop_dry_run    — dry_run=True
  noop_no_sender  — sender_fn is None, dry_run=False
  not_ready       — plan.status != "ready"
  invalid_plan    — plan is not a DeliveryPlan instance
  sender_error    — sender raised

Reason codes for run_proactive_delivery():
  sent, sender_error  — from deliver()
  invalid_plan        — not a DeliveryPlan
  not_ready           — plan.status != "ready"
  no_resolver         — chat_id_resolver is None
  no_sender_factory   — sender_factory is None
  resolver_error      — resolver raised
  no_chat_id          — resolver returned falsy
  factory_error       — factory raised
"""
from __future__ import annotations

import dataclasses

import pytest

from agents.proactive_delivery import (
    DeliveryPlan,
    DeliveryResult,
    create_delivery_plan,
    deliver,
)
from agents.proactive_policy import ProactiveDecision
from agents.proactive_runtime import run_proactive_delivery


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ready_plan(user_id: str = "u1", task_id: str = "t1") -> DeliveryPlan:
    d = ProactiveDecision(
        decision="deliver", reason="policy_allows_delivery",
        priority="normal", cooldown_seconds=300, requires_user_opt_in=False,
    )
    plan = create_delivery_plan(d, user_id=user_id, task_id=task_id)
    assert plan is not None
    return plan


def _deferred_plan() -> DeliveryPlan:
    d = ProactiveDecision(
        decision="defer", reason="dnd_active",
        priority="normal", cooldown_seconds=300, requires_user_opt_in=False,
    )
    plan = create_delivery_plan(d, user_id="u1", task_id="t1")
    assert plan is not None
    return plan


_REQUIRED_FIELDS = frozenset({"sent", "dry_run", "plan_status", "reason", "error", "ts"})


# ---------------------------------------------------------------------------
# 1. DeliveryResult is a frozen dataclass
# ---------------------------------------------------------------------------

def test_delivery_result_is_dataclass():
    assert dataclasses.is_dataclass(DeliveryResult)


def test_delivery_result_is_frozen():
    result = DeliveryResult(
        sent=False, dry_run=True, plan_status=None,
        reason="noop_dry_run", error=None, ts="2026-01-01T00:00:00+00:00",
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        result.sent = True


def test_delivery_result_has_required_fields():
    result = DeliveryResult(
        sent=False, dry_run=True, plan_status=None,
        reason="noop_dry_run", error=None, ts="2026-01-01T00:00:00+00:00",
    )
    missing = _REQUIRED_FIELDS - {f.name for f in dataclasses.fields(result)}
    assert not missing, f"Missing fields: {missing}"


# ---------------------------------------------------------------------------
# 2. deliver() returns DeliveryResult in all paths
# ---------------------------------------------------------------------------

def test_deliver_returns_delivery_result_on_noop():
    plan = _ready_plan()
    result = deliver(plan, sender_fn=None)
    assert isinstance(result, DeliveryResult)


def test_deliver_noop_no_sender_fields():
    plan = _ready_plan()
    result = deliver(plan, sender_fn=None)
    assert result.sent is False
    assert result.dry_run is False
    assert result.reason == "noop_no_sender"
    assert result.plan_status == "ready"
    assert result.error is None
    assert result.ts  # non-empty


def test_deliver_dry_run_fields():
    plan = _ready_plan()
    result = deliver(plan, sender_fn=None, dry_run=True)
    assert result.sent is False
    assert result.dry_run is True
    assert result.reason == "noop_dry_run"
    assert result.plan_status == "ready"
    assert result.error is None


def test_deliver_dry_run_skips_sender():
    plan = _ready_plan()
    calls = []
    result = deliver(plan, sender_fn=lambda uid, txt: calls.append(1), dry_run=True)
    assert result.sent is False
    assert calls == [], "dry_run=True must not invoke sender_fn"


def test_deliver_sent_fields():
    plan = _ready_plan()
    result = deliver(plan, sender_fn=lambda uid, txt: None)
    assert result.sent is True
    assert result.dry_run is False
    assert result.reason == "sent"
    assert result.plan_status == "ready"
    assert result.error is None


def test_deliver_deferred_not_ready_fields():
    plan = _deferred_plan()
    result = deliver(plan, sender_fn=lambda uid, txt: None)
    assert result.sent is False
    assert result.reason == "not_ready"
    assert result.plan_status == "deferred"


def test_deliver_sender_error_fields():
    plan = _ready_plan()
    def _bad(uid, txt):
        raise RuntimeError("timeout")
    result = deliver(plan, sender_fn=_bad)
    assert result.sent is False
    assert result.reason == "sender_error"
    assert result.error == "timeout"
    assert result.plan_status == "ready"


def test_deliver_invalid_plan_fields():
    result = deliver(None, sender_fn=lambda uid, txt: None)
    assert result.sent is False
    assert result.reason == "invalid_plan"
    assert result.plan_status is None
    assert result.error is None


def test_deliver_ts_is_non_empty_string():
    plan = _ready_plan()
    result = deliver(plan, sender_fn=None)
    assert isinstance(result.ts, str)
    assert len(result.ts) > 10


# ---------------------------------------------------------------------------
# 3. run_proactive_delivery() returns DeliveryResult in all paths
# ---------------------------------------------------------------------------

def test_runtime_returns_delivery_result_on_success():
    plan = _ready_plan()
    result = run_proactive_delivery(
        plan,
        chat_id_resolver=lambda uid: "42",
        sender_factory=lambda cid: lambda uid, txt: None,
    )
    assert isinstance(result, DeliveryResult)
    assert result.sent is True
    assert result.reason == "sent"


def test_runtime_invalid_plan_fields():
    result = run_proactive_delivery(None, chat_id_resolver=lambda uid: "42",
                                    sender_factory=lambda cid: lambda uid, txt: None)
    assert isinstance(result, DeliveryResult)
    assert result.sent is False
    assert result.reason == "invalid_plan"
    assert result.plan_status is None


def test_runtime_no_resolver_fields():
    result = run_proactive_delivery(_ready_plan(), chat_id_resolver=None,
                                    sender_factory=lambda cid: lambda uid, txt: None)
    assert result.sent is False
    assert result.reason == "no_resolver"


def test_runtime_no_factory_fields():
    result = run_proactive_delivery(_ready_plan(),
                                    chat_id_resolver=lambda uid: "42",
                                    sender_factory=None)
    assert result.sent is False
    assert result.reason == "no_sender_factory"


def test_runtime_resolver_error_fields():
    def _bad(uid):
        raise ValueError("not found")
    result = run_proactive_delivery(_ready_plan(), chat_id_resolver=_bad,
                                    sender_factory=lambda cid: lambda uid, txt: None)
    assert result.sent is False
    assert result.reason == "resolver_error"
    assert result.error == "not found"


def test_runtime_factory_error_fields():
    def _bad(cid):
        raise RuntimeError("init failed")
    result = run_proactive_delivery(_ready_plan(),
                                    chat_id_resolver=lambda uid: "42",
                                    sender_factory=_bad)
    assert result.sent is False
    assert result.reason == "factory_error"
    assert result.error == "init failed"


def test_runtime_no_chat_id_fields():
    result = run_proactive_delivery(_ready_plan(),
                                    chat_id_resolver=lambda uid: None,
                                    sender_factory=lambda cid: lambda uid, txt: None)
    assert result.sent is False
    assert result.reason == "no_chat_id"


def test_runtime_deferred_not_ready_fields():
    result = run_proactive_delivery(_deferred_plan(),
                                    chat_id_resolver=lambda uid: "42",
                                    sender_factory=lambda cid: lambda uid, txt: None)
    assert result.sent is False
    assert result.reason == "not_ready"
    assert result.plan_status == "deferred"


# ---------------------------------------------------------------------------
# 4. Backward safety: None/invalid inputs never crash
# ---------------------------------------------------------------------------

def test_deliver_none_never_raises():
    result = deliver(None, sender_fn=None)
    assert isinstance(result, DeliveryResult)
    assert result.sent is False


def test_runtime_none_plan_never_raises():
    result = run_proactive_delivery(None, chat_id_resolver=None, sender_factory=None)
    assert isinstance(result, DeliveryResult)
    assert result.sent is False


def test_deliver_object_never_raises():
    result = deliver(object(), sender_fn=None)
    assert isinstance(result, DeliveryResult)
    assert result.sent is False


# ---------------------------------------------------------------------------
# 5. Precedence fix (Codex BLOCKER A): not_ready must take priority over
#    noop_no_sender so a deferred/not-ready plan is never mis-labelled.
# ---------------------------------------------------------------------------

def test_deliver_deferred_no_sender_reason_is_not_ready():
    """deferred plan + sender_fn=None must return not_ready, not noop_no_sender."""
    plan = _deferred_plan()
    result = deliver(plan, sender_fn=None)
    assert result.sent is False
    assert result.reason == "not_ready", (
        f"Expected 'not_ready', got {result.reason!r}. "
        "Precedence error: sender_fn check must come after status check."
    )
    assert result.plan_status == "deferred"


def test_deliver_ready_no_sender_reason_is_noop_no_sender():
    """ready plan + sender_fn=None must still return noop_no_sender."""
    plan = _ready_plan()
    result = deliver(plan, sender_fn=None)
    assert result.sent is False
    assert result.reason == "noop_no_sender"
    assert result.plan_status == "ready"
