"""Tests for ProactiveTelegramAdapter seam - FAZ-3-E1-S3B."""

import ast

import pytest

from agents.proactive_delivery import create_delivery_plan
from agents.proactive_policy import ProactiveDecision
from agents.proactive_runtime import run_proactive_delivery
from agents.proactive_telegram_adapter import (
    make_static_chat_id_resolver,
    make_telegram_sender_factory,
)


def _ready_plan(user_id: str = "user1", task_id: str = "task1"):
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


# 1. module imports without error
def test_module_imports():
    from agents.proactive_telegram_adapter import (
        make_static_chat_id_resolver,
        make_telegram_sender_factory,
    )
    assert callable(make_static_chat_id_resolver)
    assert callable(make_telegram_sender_factory)


# 2. static resolver returns mapped chat_id
def test_static_resolver_returns_mapped_chat_id():
    resolver = make_static_chat_id_resolver({"ahmet": "12345"})
    assert resolver("ahmet") == "12345"


# 3. static resolver returns None for unknown user_id
def test_static_resolver_returns_none_for_missing():
    resolver = make_static_chat_id_resolver({"ahmet": "12345"})
    assert resolver("unknown_user") is None


# 4. static resolver returns None for empty mapping
def test_static_resolver_empty_mapping_returns_none():
    resolver = make_static_chat_id_resolver({})
    assert resolver("ahmet") is None


# 5. static resolver does not assume user_id == chat_id
def test_static_resolver_does_not_echo_user_id():
    resolver = make_static_chat_id_resolver({"ahmet": "99999"})
    result = resolver("ahmet")
    assert result != "ahmet"
    assert result == "99999"


# 6. sender factory calls injected send_message_fn with chat_id and text
def test_sender_factory_passes_chat_id_and_text():
    calls = []
    factory = make_telegram_sender_factory(lambda cid, txt: calls.append((cid, txt)))
    sender_fn = factory("42")
    sender_fn("user1", "hello")
    assert calls == [("42", "hello")]


# 7. sender_fn returns None (void); no error raised on success
def test_sender_fn_returns_none_on_success():
    factory = make_telegram_sender_factory(lambda cid, txt: None)
    sender_fn = factory("42")
    result = sender_fn("user1", "hello")
    assert result is None


# 8. sender_fn propagates exception (deliver() in proactive_delivery catches it)
def test_sender_fn_propagates_exception():
    def _bad(cid, txt):
        raise RuntimeError("network error")
    factory = make_telegram_sender_factory(_bad)
    sender_fn = factory("42")
    with pytest.raises(RuntimeError, match="network error"):
        sender_fn("user1", "hello")


# 9. no env read in adapter module
def test_no_env_read_in_module():
    with open("agents/proactive_telegram_adapter.py", encoding="utf-8") as f:
        source = f.read()
    assert "os.environ" not in source
    assert "load_env" not in source
    assert "dotenv" not in source


# 10. no real tools.telegram_agent import in adapter module
def test_no_telegram_agent_import_in_module():
    with open("agents/proactive_telegram_adapter.py", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "telegram" not in alias.name.lower(), f"forbidden import: {alias.name}"
                assert "tools" not in alias.name.lower(), f"forbidden import: {alias.name}"
        if isinstance(node, ast.ImportFrom):
            if node.module:
                assert "telegram" not in node.module.lower(), f"forbidden import from {node.module}"
                assert "tools" not in node.module.lower(), f"forbidden import from {node.module}"


# 11. integration: run_proactive_delivery with adapter primitives, fake send
def test_integration_run_proactive_delivery_with_adapter():
    plan = _ready_plan(user_id="ahmet")
    calls = []

    resolver = make_static_chat_id_resolver({"ahmet": "telegram_99"})
    factory = make_telegram_sender_factory(lambda cid, txt: calls.append((cid, txt)))

    result = run_proactive_delivery(plan, chat_id_resolver=resolver, sender_factory=factory)

    assert result is True
    assert len(calls) == 1
    assert calls[0][0] == "telegram_99"
    assert len(calls[0][1]) > 0


# 12. integration: resolver miss → run_proactive_delivery returns False, no send
def test_integration_resolver_miss_no_send():
    plan = _ready_plan(user_id="unknown_user")
    calls = []

    resolver = make_static_chat_id_resolver({"ahmet": "telegram_99"})
    factory = make_telegram_sender_factory(lambda cid, txt: calls.append((cid, txt)))

    result = run_proactive_delivery(plan, chat_id_resolver=resolver, sender_factory=factory)

    assert result is False
    assert calls == []
