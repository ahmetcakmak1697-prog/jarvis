"""OllamaExecutor tests ? Ollama calismadan yesil olmali (fake client)."""
from __future__ import annotations


class FakeOllamaClient:
    def __init__(self, response="Fake cevap.", fail=False):
        self.response = response
        self.fail = fail
        self.calls = []

    def generate(self, model, prompt, system=None, keep_alive=None, stream=False, **kw):
        self.calls.append({"model": model, "prompt": prompt})
        if self.fail:
            raise ConnectionError("Ollama bagli degil.")
        return {"response": self.response, "model": model, "done": True}


def test_executor_returns_response():
    from agents.ollama_executor import OllamaExecutor
    client = FakeOllamaClient(response="Test cevabi.")
    ex = OllamaExecutor(client=client)
    result = ex.generate("Test sorusu?")
    assert result["ok"] is True
    assert result["text"] == "Test cevabi."


def test_executor_uses_correct_model_for_level():
    from agents.ollama_executor import OllamaExecutor
    client = FakeOllamaClient()
    ex = OllamaExecutor(client=client)
    ex.generate("Soru?", level="L1")
    assert len(client.calls) == 1
    assert client.calls[0]["model"] is not None


def test_executor_handles_connection_error():
    from agents.ollama_executor import OllamaExecutor
    client = FakeOllamaClient(fail=True)
    ex = OllamaExecutor(client=client)
    result = ex.generate("Soru?")
    assert result["ok"] is False
    assert "error" in result
    assert result["text"] is None


def test_dry_run_returns_ok_without_call():
    from agents.ollama_executor import OllamaExecutor
    client = FakeOllamaClient()
    ex = OllamaExecutor(client=client)
    result = ex.generate("Soru?", dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert client.calls == []


def test_executor_passes_prompt_to_client():
    from agents.ollama_executor import OllamaExecutor
    client = FakeOllamaClient(response="Cevap.")
    ex = OllamaExecutor(client=client)
    ex.generate("RTX 3070 kac watt?")
    assert "RTX 3070" in client.calls[0]["prompt"]


def test_level_to_model_mapping():
    from agents.ollama_executor import OllamaExecutor
    ex = OllamaExecutor(client=FakeOllamaClient())
    assert ex.level_to_model("L1") is not None
    assert ex.level_to_model("L2") is not None
    assert ex.level_to_model("L3") is not None
    assert ex.level_to_model("L0") == "local_memory"


def test_executor_result_has_required_fields():
    from agents.ollama_executor import OllamaExecutor
    client = FakeOllamaClient(response="Cevap.")
    ex = OllamaExecutor(client=client)
    result = ex.generate("Soru?")
    assert "ok" in result
    assert "text" in result
    assert "model" in result
    assert "level" in result
    assert "latency_ms" in result
