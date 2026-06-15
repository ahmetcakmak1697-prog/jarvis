from agents.execution_policy import ExecutionPolicy


def test_ask_external_l2_defaults_to_local_ollama():
    policy = ExecutionPolicy()
    router_decision = {
        "decision": "ask_external",
        "cascade": {"level": "L2"},
    }

    result = policy.choose(router_decision)

    assert result["level"] == "L2"
    assert result["destination"] == "local"
    assert result["primary_executor"] == "ollama"
    assert result["fallback_executor"] is None
    assert result["requires_approval"] is False


def test_ask_external_l3_level_is_not_forced_to_cloud():
    policy = ExecutionPolicy()
    router_decision = {
        "decision": "ask_external",
        "cascade": {"level": "L3"},
    }

    result = policy.choose(router_decision)

    assert result["level"] == "L3"
    assert result["destination"] == "local"
    assert result["primary_executor"] == "ollama"
    assert result["reason"] == "local_first_default"


def test_cloud_api_can_be_selected_without_changing_level():
    policy = ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3"})
    router_decision = {
        "decision": "ask_external",
        "cascade": {"level": "L3"},
    }

    result = policy.choose(router_decision)

    assert result["level"] == "L3"
    assert result["destination"] == "cloud_api"
    assert result["primary_executor"] == "api"
    assert result["fallback_executor"] == "ollama"
    assert result["requires_approval"] is False


def test_l4_requires_premium_gate_even_when_cloud_enabled():
    policy = ExecutionPolicy(cloud_api_enabled=True, cloud_levels={"L3", "L4"})
    router_decision = {
        "decision": "ask_external",
        "cascade": {"level": "L4"},
    }

    result = policy.choose(router_decision)

    assert result["level"] == "L4"
    assert result["destination"] == "premium_gate"
    assert result["primary_executor"] is None
    assert result["fallback_executor"] == "ollama"
    assert result["requires_approval"] is True


def test_blocked_router_decision_stays_blocked():
    policy = ExecutionPolicy()
    router_decision = {
        "decision": "redacted_blocked",
        "route": "blocked",
    }

    result = policy.choose(router_decision)

    assert result["destination"] == "blocked"
    assert result["primary_executor"] is None
    assert result["requires_approval"] is False


def test_local_answer_router_decision_stays_local_answer():
    policy = ExecutionPolicy()
    router_decision = {
        "decision": "answer_local",
        "route": "knowledge_card",
        "answer": "Kayitli cevap",
    }

    result = policy.choose(router_decision)

    assert result["destination"] == "local_answer"
    assert result["primary_executor"] is None
    assert result["level"] == "L0"
