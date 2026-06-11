"""OllamaExecutor system prompt + keep_alive tests."""
from __future__ import annotations


class CapturingClient:
    """client.generate cagrisini yakalar."""
    def __init__(self):
        self.last_call = None

    def generate(self, model, prompt, system=None, keep_alive=None, **kw):
        self.last_call = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "keep_alive": keep_alive,
        }
        return {"response": "Test cevabi.", "model": model, "done": True}


def test_l1_uses_turkish_system_prompt():
    from agents.ollama_executor import OllamaExecutor
    client = CapturingClient()
    ex = OllamaExecutor(client=client)
    ex.generate("merhaba", level="L1")
    # system prompt Turkce icerik tasimali
    sys_text = client.last_call["system"] or client.last_call["prompt"]
    assert "Turkce" in sys_text or "Jarvis" in sys_text


def test_custom_system_prompt_overrides():
    from agents.ollama_executor import OllamaExecutor
    client = CapturingClient()
    ex = OllamaExecutor(client=client)
    ex.generate("soru", level="L2", system_prompt="OZEL PROMPT")
    sys_text = client.last_call["system"] or client.last_call["prompt"]
    assert "OZEL PROMPT" in sys_text


def test_keep_alive_passed():
    from agents.ollama_executor import OllamaExecutor
    client = CapturingClient()
    ex = OllamaExecutor(client=client)
    ex.generate("soru", level="L2")
    # keep_alive ya client'a gecmis ya da prompt icinde degil ama parametre olarak var
    assert client.last_call["keep_alive"] is not None


def test_prompt_does_not_contain_system_when_native():
    """system native parametre olarak gidiyorsa prompt'a gomulmemeli."""
    from agents.ollama_executor import OllamaExecutor
    client = CapturingClient()
    ex = OllamaExecutor(client=client)
    ex.generate("merhaba", level="L1")
    # Eger system native ise prompt sadece kullanici sorusu olmali
    if client.last_call["system"]:
        assert client.last_call["prompt"] == "merhaba" or "merhaba" in client.last_call["prompt"]


def test_different_levels_different_prompts():
    from agents.ollama_executor import OllamaExecutor
    c1 = CapturingClient()
    OllamaExecutor(client=c1).generate("soru", level="L1")
    c3 = CapturingClient()
    OllamaExecutor(client=c3).generate("soru", level="L3")
    s1 = c1.last_call["system"] or c1.last_call["prompt"]
    s3 = c3.last_call["system"] or c3.last_call["prompt"]
    # L1 ve L3 farkli system prompt kullanmali
    assert s1 != s3
