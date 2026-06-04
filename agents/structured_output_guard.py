"""Structured Output Guard - C3.1D.

Small defensive JSON/schema guard for report outputs.

Purpose:
- parse model/tool JSON safely
- validate required fields and simple field types
- return deterministic fallback instead of crashing
"""

from __future__ import annotations

import json

from dataclasses import dataclass
from typing import Any


SchemaSpec = dict[str, type | tuple[type, ...]]


@dataclass
class GuardResult:
    ok: bool
    data: dict[str, Any]
    errors: list[str]
    used_fallback: bool = False


class StructuredOutputGuard:
    """Minimal schema guard for machine-readable Jarvis outputs."""

    def parse_json(self, raw: str) -> GuardResult:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            return GuardResult(
                ok=False,
                data={},
                errors=[f"invalid_json: {exc.msg}"],
                used_fallback=False,
            )

        if not isinstance(data, dict):
            return GuardResult(
                ok=False,
                data={},
                errors=["json_root_not_object"],
                used_fallback=False,
            )

        return GuardResult(ok=True, data=data, errors=[])

    def validate(
        self,
        data: dict[str, Any],
        required: SchemaSpec,
        optional: SchemaSpec | None = None,
    ) -> GuardResult:
        errors: list[str] = []
        optional = optional or {}

        for key, expected_type in required.items():
            if key not in data:
                errors.append(f"missing_required:{key}")
                continue

            if not isinstance(data[key], expected_type):
                errors.append(f"invalid_type:{key}")

        for key, expected_type in optional.items():
            if key in data and not isinstance(data[key], expected_type):
                errors.append(f"invalid_type:{key}")

        return GuardResult(
            ok=not errors,
            data=data if not errors else {},
            errors=errors,
        )

    def parse_and_validate(
        self,
        raw: str,
        required: SchemaSpec,
        optional: SchemaSpec | None = None,
        fallback: dict[str, Any] | None = None,
    ) -> GuardResult:
        parsed = self.parse_json(raw)
        if not parsed.ok:
            return self._fallback(parsed.errors, fallback)

        validated = self.validate(parsed.data, required, optional)
        if not validated.ok:
            return self._fallback(validated.errors, fallback)

        return validated

    def _fallback(
        self,
        errors: list[str],
        fallback: dict[str, Any] | None,
    ) -> GuardResult:
        return GuardResult(
            ok=False,
            data=dict(fallback or {}),
            errors=errors,
            used_fallback=True,
        )


def reporting_summary_schema() -> tuple[SchemaSpec, SchemaSpec]:
    required: SchemaSpec = {
        "title": str,
        "summary": str,
        "next_action": str,
        "risks": list,
    }

    optional: SchemaSpec = {
        "confidence": (int, float),
        "sources": list,
    }

    return required, optional
