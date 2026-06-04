from agents.organ_base import (
    JarvisOrgan,
    OrganCapability,
    OrganHealth,
    OrganResult,
)


class MockOrgan(JarvisOrgan):
    name = "mock"
    permission_level = "read_only"

    def health(self):
        return OrganHealth(
            name=self.name,
            status="ok",
            message="mock organ ready",
        )

    def capabilities(self):
        return [
            OrganCapability(
                name="echo",
                description="Return payload",
                permission_level="read_only",
            )
        ]

    def invoke(self, action, payload=None):
        if action != "echo":
            return self.degrade_mode("unsupported action")

        return OrganResult(
            ok=True,
            data={"echo": payload or {}},
            message="ok",
        )


def test_mock_organ_health_shape():
    organ = MockOrgan()

    health = organ.health()

    assert health.name == "mock"
    assert health.status == "ok"
    assert health.to_dict()["message"] == "mock organ ready"


def test_mock_organ_capabilities_shape():
    organ = MockOrgan()

    caps = organ.capabilities()

    assert len(caps) == 1
    assert caps[0].name == "echo"
    assert caps[0].permission_level == "read_only"


def test_mock_organ_invoke_success():
    organ = MockOrgan()

    result = organ.invoke("echo", {"hello": "world"})

    assert result.ok is True
    assert result.data["echo"]["hello"] == "world"


def test_mock_organ_degrade_mode_for_unknown_action():
    organ = MockOrgan()

    result = organ.invoke("unknown", {})

    assert result.ok is False
    assert result.degraded is True
    assert "unsupported action" in result.message


def test_mock_organ_trace_hook_is_core_safe():
    organ = MockOrgan()
    result = organ.invoke("echo", {"secret": "not redacted here"})

    trace = organ.trace_hook("echo", result)

    assert trace["organ"] == "mock"
    assert trace["action"] == "echo"
    assert trace["ok"] is True
    assert trace["permission_level"] == "read_only"
    assert "secret" not in trace
