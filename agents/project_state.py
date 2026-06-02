"""Project State - C2.1.

Small machine-readable project state model for Jarvis v5.

Purpose:
- keep track of the current project phase
- preserve the last completed checkpoint
- expose next steps to project intelligence modules
- avoid relying only on chat history
"""

from __future__ import annotations

import json
import subprocess

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = ROOT / "memory" / "project_state.json"


@dataclass
class ProjectState:
    project: str = "Jarvis v5"
    current_phase: str = "C2"
    last_completed_phase: str = "C1"
    status: str = "C1 completed; C2 Project Intelligence started"
    active_branch: str = "master"
    last_checkpoint: str = "docs/C1_MEMORY_CHECKPOINT.md"
    smoke_suite: str = "tests/run_smoke_suite.py"
    updated_at: str = ""
    last_commits: list[str] | None = None
    next_steps: list[str] | None = None
    risk_notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["last_commits"] = data["last_commits"] or []
        data["next_steps"] = data["next_steps"] or []
        data["risk_notes"] = data["risk_notes"] or []
        return data


class ProjectStateStore:
    """Read/write helper for memory/project_state.json."""

    def __init__(self, path: Path | str = DEFAULT_STATE_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def default_state(self) -> ProjectState:
        return ProjectState(
            updated_at=datetime.now().isoformat(timespec="seconds"),
            last_commits=self._last_commits(),
            next_steps=[
                "C2.1 project state model",
                "C2.2 repo/project summarizer",
                "C2.3 current roadmap detector",
                "C2.4 next-action planner",
                "C2.5 Telegram/project dashboard command",
                "C2.6 project intelligence smoke tests",
            ],
            risk_notes=[
                "Do not rely only on chat history for project continuity.",
                "Keep project state machine-readable and committed only if it is stable documentation, not volatile runtime.",
                "Avoid writing secrets or local-only paths beyond repo-relative references.",
            ],
        )

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            state = self.default_state().to_dict()
            self.save(state)
            return state

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("project_state root must be dict")
            return data
        except Exception:
            state = self.default_state().to_dict()
            self.save(state)
            return state

    def save(self, data: dict[str, Any]) -> dict[str, Any]:
        out = dict(data)
        out["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.path.write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return out

    def refresh(self) -> dict[str, Any]:
        data = self.load()
        data["active_branch"] = self._git(["rev-parse", "--abbrev-ref", "HEAD"]) or data.get("active_branch", "unknown")
        data["last_commits"] = self._last_commits()
        data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.save(data)
        return data

    def summary(self) -> str:
        data = self.load()
        lines = [
            f"Project: {data.get('project')}",
            f"Current phase: {data.get('current_phase')}",
            f"Last completed: {data.get('last_completed_phase')}",
            f"Status: {data.get('status')}",
            f"Branch: {data.get('active_branch')}",
            f"Checkpoint: {data.get('last_checkpoint')}",
            "",
            "Next steps:",
        ]

        for step in data.get("next_steps", [])[:8]:
            lines.append(f"- {step}")

        commits = data.get("last_commits", [])[:5]
        if commits:
            lines.extend(["", "Recent commits:"])
            lines.extend(f"- {c}" for c in commits)

        return "\n".join(lines)

    def _last_commits(self, limit: int = 8) -> list[str]:
        output = self._git(["log", "--oneline", f"-{limit}"])
        if not output:
            return []
        return [line.strip() for line in output.splitlines() if line.strip()]

    def _git(self, args: list[str]) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=ROOT,
                text=True,
                capture_output=True,
                shell=False,
                timeout=10,
            )
            if result.returncode != 0:
                return ""
            return result.stdout.strip()
        except Exception:
            return ""


if __name__ == "__main__":
    store = ProjectStateStore()
    state = store.refresh()
    print(json.dumps(state, ensure_ascii=False, indent=2))
    print()
    print(store.summary())
