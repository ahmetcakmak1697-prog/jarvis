from agents.redaction_guard import RedactionGuard


def test_redacts_named_secret_assignment():
    guard = RedactionGuard()

    result = guard.sanitize_text("OPENAI_API_KEY=sk-test123")

    assert result.redacted is True
    assert "sk-test123" not in result.text
    assert "[REDACTED]" in result.text


def test_redacts_email():
    guard = RedactionGuard()

    result = guard.sanitize_text("mail: ahmetcakmak1697@gmail.com")

    assert result.redacted is True
    assert "gmail.com" not in result.text
    assert "[REDACTED_EMAIL]" in result.text


def test_redacts_windows_user_path():
    guard = RedactionGuard()

    result = guard.sanitize_text(r"C:\Users\Ahmedov\Desktop\Jarvis\jarvis")

    assert result.redacted is True
    assert "Ahmedov" not in result.text
    assert r"C:\Users\[REDACTED_USER]" in result.text


def test_redacts_private_key_block():
    guard = RedactionGuard()

    raw = """-----BEGIN PRIVATE KEY-----
abc123
-----END PRIVATE KEY-----"""

    result = guard.sanitize_text(raw)

    assert result.redacted is True
    assert "abc123" not in result.text
    assert "[REDACTED_PRIVATE_KEY]" in result.text


def test_contains_sensitive_data_with_hint():
    guard = RedactionGuard()

    assert guard.contains_sensitive_data("token burada olabilir") is True


def test_sanitize_dict_redacts_sensitive_keys():
    guard = RedactionGuard()

    data = {
        "token": "abc123",
        "safe": "hello",
        "nested": {
            "email": "user@example.com",
            "note": "ok",
        },
    }

    sanitized = guard.sanitize_dict(data)

    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["safe"] == "hello"
    assert sanitized["nested"]["email"] == "[REDACTED_EMAIL]"
    assert sanitized["nested"]["note"] == "ok"


def test_sanitize_list_values_inside_dict():
    guard = RedactionGuard()

    data = {
        "items": [
            "safe",
            "OPENAI_API_KEY=secret-value",
            "mail user@example.com",
        ]
    }

    sanitized = guard.sanitize_dict(data)

    assert sanitized["items"][0] == "safe"
    assert "secret-value" not in sanitized["items"][1]
    assert "[REDACTED_EMAIL]" in sanitized["items"][2]


def test_non_sensitive_text_is_unchanged():
    guard = RedactionGuard()

    result = guard.sanitize_text("Jarvis reporting state is stable.")

    assert result.redacted is False
    assert result.text == "Jarvis reporting state is stable."
