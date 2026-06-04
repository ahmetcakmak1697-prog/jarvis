"""Redaction Guard - A6-mini.

Central lightweight redaction utilities for Jarvis outputs/logs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RedactionResult:
    text: str
    redacted: bool
    hits: list[str]


class RedactionGuard:
    """Central redaction helper for text/dict outputs."""

    PATTERNS: list[tuple[str, str, str]] = [
        (
            "named_secret",
            r"(?i)\b(api[_-]?key|token|secret|password|passwd|parola|sifre|?ifre)\s*[:=]\s*['\"]?[^'\"\s,;]+",
            r"\1=[REDACTED]",
        ),
        (
            "known_api_key",
            r"(?i)\b(TELEGRAM_BOT_TOKEN|TAVILY_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY)\s*[:=]\s*['\"]?[^'\"\s,;]+",
            r"\1=[REDACTED]",
        ),
        (
            "private_key",
            r"(?is)-----BEGIN .*?PRIVATE KEY-----.*?-----END .*?PRIVATE KEY-----",
            "[REDACTED_PRIVATE_KEY]",
        ),
        (
            "email",
            r"(?i)\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b",
            "[REDACTED_EMAIL]",
        ),
        (
            "iban",
            r"(?i)\bTR\d{2}[\s\-]?(?:\d[\s\-]?){20,}\b",
            "[REDACTED_IBAN]",
        ),
        (
            "phone_tr",
            r"(?<!\d)(?:\+90|0)?\s?5\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)",
            "[REDACTED_PHONE]",
        ),
        (
            "windows_user_path",
            r"(?i)C:\\Users\\[^\\\s]+",
            r"C:\\Users\\[REDACTED_USER]",
        ),
        (
            "env_file_value",
            r"(?im)^([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*\s*=\s*).+$",
            r"\1[REDACTED]",
        ),
    ]

    SENSITIVE_HINTS = [
        "api_key",
        "apikey",
        "token",
        "secret",
        "password",
        "passwd",
        "parola",
        "sifre",
        "?ifre",
        "private key",
        ".env",
        "iban",
    ]

    def sanitize_text(self, text: str | None) -> RedactionResult:
        original = "" if text is None else str(text)
        sanitized = original
        hits: list[str] = []

        for label, pattern, repl in self.PATTERNS:
            try:
                sanitized_new, count = re.subn(pattern, repl, sanitized)
            except re.error:
                continue

            if count:
                hits.append(label)
                sanitized = sanitized_new

        return RedactionResult(
            text=sanitized,
            redacted=sanitized != original,
            hits=list(dict.fromkeys(hits)),
        )

    def contains_sensitive_data(self, text: str | None) -> bool:
        value = "" if text is None else str(text)
        low = value.lower()

        if any(hint in low for hint in self.SENSITIVE_HINTS):
            return True

        return self.sanitize_text(value).redacted

    def sanitize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        return {str(k): self._sanitize_value(k, v) for k, v in data.items()}

    def sanitize_path(self, path: str | Path) -> str:
        return self.sanitize_text(str(path)).text

    def _sanitize_value(self, key: Any, value: Any) -> Any:
        key_low = str(key).lower()

        if any(hint in key_low for hint in self.SENSITIVE_HINTS):
            return "[REDACTED]"

        if isinstance(value, str):
            return self.sanitize_text(value).text

        if isinstance(value, dict):
            return self.sanitize_dict(value)

        if isinstance(value, list):
            return [self._sanitize_value(key, item) for item in value]

        return value
