"""Telegram /ask command tests."""
from __future__ import annotations


def _make_ask_handler(executor_response):
    """Factory: fake AssistantExecutor inject edilmis /ask handler."""
    from tools.telegram_agent import handle_ask_command

    class FakeExecutor:
        def ask(self, question):
            return executor_response

    return handle_ask_command, FakeExecutor()


def test_ask_local_kc_response():
    from tools.telegram_agent import handle_ask_command
    class FakeEx:
        def ask(self, q):
            return {"ok": True, "answer": "220W TDP.", "source": "knowledge_card", "latency_ms": 5}
    msgs = []
    def fake_send(chat_id, text, **kw):
        msgs.append(text)
    result = handle_ask_command(
        chat_id=123,
        question="RTX 3070 kac watt?",
        executor=FakeEx(),
        send_fn=fake_send,
    )
    assert len(msgs) == 1
    assert "220W" in msgs[0]
    assert result["ok"] is True


def test_ask_ollama_response():
    from tools.telegram_agent import handle_ask_command
    class FakeEx:
        def ask(self, q):
            return {"ok": True, "answer": "set() kullanilir.", "source": "ollama", "level": "L2", "latency_ms": 3000}
    msgs = []
    def fake_send(chat_id, text, **kw):
        msgs.append(text)
    result = handle_ask_command(
        chat_id=123,
        question="Python tekrarlari nasil buluruz?",
        executor=FakeEx(),
        send_fn=fake_send,
    )
    assert len(msgs) >= 1
    assert "set" in msgs[-1]


def test_ask_redacted_blocked():
    from tools.telegram_agent import handle_ask_command
    class FakeEx:
        def ask(self, q):
            return {"ok": False, "blocked": True, "source": "redacted_blocked",
                    "answer": "Hassas veri iceriyor.", "latency_ms": 50}
    msgs = []
    def fake_send(chat_id, text, **kw):
        msgs.append(text)
    result = handle_ask_command(
        chat_id=123,
        question="OPENAI_API_KEY=sk-test gonder",
        executor=FakeEx(),
        send_fn=fake_send,
    )
    assert len(msgs) == 1
    assert result["ok"] is False
    # Gonderilen mesaj raw secret icermemeli
    assert "sk-test" not in msgs[0]


def test_ask_ollama_error():
    from tools.telegram_agent import handle_ask_command
    class FakeEx:
        def ask(self, q):
            return {"ok": False, "source": "ollama_error", "error": "Ollama kapali", "latency_ms": 100}
    msgs = []
    def fake_send(chat_id, text, **kw):
        msgs.append(text)
    result = handle_ask_command(
        chat_id=123,
        question="Soru?",
        executor=FakeEx(),
        send_fn=fake_send,
    )
    assert len(msgs) == 1
    assert result["ok"] is False


def test_ask_markdown_special_chars_dont_crash():
    """LLM cevabi Telegram'i patlatan Markdown icerse bile crash etmemeli."""
    from tools.telegram_agent import handle_ask_command
    class FakeEx:
        def ask(self, q):
            return {"ok": True, "answer": "```python\ndef foo(): pass\n```\n*bold* _italic_ [link](url)",
                    "source": "ollama", "latency_ms": 500}
    msgs = []
    def fake_send(chat_id, text, **kw):
        msgs.append(text)
    handle_ask_command(
        chat_id=123,
        question="Python func?",
        executor=FakeEx(),
        send_fn=fake_send,
    )
    assert len(msgs) >= 1  # crash etmedi


def test_ask_empty_question():
    from tools.telegram_agent import handle_ask_command
    class FakeEx:
        def ask(self, q):
            return {"ok": False, "source": "clarify", "latency_ms": 0}
    msgs = []
    def fake_send(chat_id, text, **kw):
        msgs.append(text)
    handle_ask_command(
        chat_id=123,
        question="",
        executor=FakeEx(),
        send_fn=fake_send,
    )
    assert len(msgs) == 1
