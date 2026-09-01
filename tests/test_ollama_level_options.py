"""OllamaExecutor level options (temperature + num_predict) tests."""
from __future__ import annotations


class CapturingClient:
    def __init__(self):
        self.last_call = None

    def generate(self, model, prompt, system=None, keep_alive=None, options=None, **kw):
        self.last_call = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "keep_alive": keep_alive,
            "options": options,
        }
        return {"response": "Test.", "model": model, "done": True}


def test_l1_has_options():
    from agents.ollama_executor import OllamaExecutor
    c = CapturingClient()
    OllamaExecutor(client=c).generate("merhaba", level="L1")
    assert c.last_call["options"] is not None


def test_l1_num_predict_small():
    from agents.ollama_executor import OllamaExecutor
    c = CapturingClient()
    OllamaExecutor(client=c).generate("merhaba", level="L1")
    assert c.last_call["options"]["num_predict"] <= 100


def test_l2_num_predict_medium():
    from agents.ollama_executor import OllamaExecutor
    c = CapturingClient()
    OllamaExecutor(client=c).generate("soru", level="L2")
    opts = c.last_call["options"]
    assert 200 <= opts["num_predict"] <= 500


def test_l3_num_predict_large():
    from agents.ollama_executor import OllamaExecutor
    c = CapturingClient()
    OllamaExecutor(client=c).generate("derin analiz", level="L3")
    assert c.last_call["options"]["num_predict"] >= 600


def test_l1_temperature_low():
    from agents.ollama_executor import OllamaExecutor
    c = CapturingClient()
    OllamaExecutor(client=c).generate("merhaba", level="L1")
    assert c.last_call["options"]["temperature"] <= 0.3


def test_levels_have_different_options():
    from agents.ollama_executor import OllamaExecutor
    c1, c3 = CapturingClient(), CapturingClient()
    OllamaExecutor(client=c1).generate("s", level="L1")
    OllamaExecutor(client=c3).generate("s", level="L3")
    assert c1.last_call["options"]["num_predict"] != c3.last_call["options"]["num_predict"]
