"""Jarvis Organ Contract - H1.5.

Single adapter contract for future Jarvis organs.

Rule:
Jarvis Core must not depend on vendor/project-specific APIs directly.
Every external/internal organ is wrapped behind this contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Literal


PermissionLevel = Literal["read_only", "write_limited", "write_sensitive", "system_control"]
OrganStatus = Literal["ok", "degraded", "offline", "error"]


@dataclass
class OrganHealth:
    name: str
    status: OrganStatus
    message: str = ""
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrganCapability:
    name: str
    description: str
    permission_level: PermissionLevel = "read_only"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrganResult:
    ok: bool
    data: dict[str, Any]
    message: str = ""
    errors: list[str] | None = None
    degraded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JarvisOrgan(ABC):
    """Base contract every Jarvis organ adapter must implement."""

    name: str = "unknown"
    permission_level: PermissionLevel = "read_only"

    @abstractmethod
    def health(self) -> OrganHealth:
        """Return current organ health without causing side effects."""

    @abstractmethod
    def capabilities(self) -> list[OrganCapability]:
        """Return supported actions/capabilities."""

    @abstractmethod
    def invoke(self, action: str, payload: dict[str, Any] | None = None) -> OrganResult:
        """Run an organ action through a controlled adapter boundary."""

    def trace_hook(self, action: str, result: OrganResult) -> dict[str, Any]:
        """Return a trace-safe summary of an organ call."""
        return {
            "organ": self.name,
            "action": action,
            "ok": result.ok,
            "degraded": result.degraded,
            "message": result.message,
            "errors": result.errors or [],
            "permission_level": self.permission_level,
        }

    def degrade_mode(self, reason: str = "") -> OrganResult:
        """Return a deterministic degraded response instead of crashing Core."""
        return OrganResult(
            ok=False,
            data={},
            message=reason or f"{self.name} organ is degraded",
            errors=[reason] if reason else [],
            degraded=True,
        )
