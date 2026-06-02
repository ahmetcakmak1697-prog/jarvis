"""Project Summarizer - C2.2.

Creates a compact project summary from:
- project_state.json
- git status/log
- roadmap/checkpoint docs

This module is deterministic and does not call an LLM.
"""

from __future__ import annotations

import json
import subprocess
import sys

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.project_state import ProjectStateStore


@dataclass
class ProjectSummary:
    project: str
    current_phase: str
    last_completed_phase: str
    status: str
    branch: str
    git_clean: bool
    last_checkpoint: str
    next_steps: list[str]
    recent_commits: list[str]
    docs_present: dict[str, bool]
    risks: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProjectSummarizer:
    """Build a deterministic project intelligence summary."""

    ROADMAP = ROOT / "docs" / "JARVIS_v5_MASTER_ROADMAP.md"
    C1_CHECKPOINT = ROOT / "docs" / "C1_MEMORY_CHECKPOINT.md"

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.state_store = ProjectStateStore()

    def summarize(self) -> ProjectSummary:
        state = self.state_store.refresh()

        branch = self._git(["rev-parse", "--abbrev-ref", "HEAD"]) or state.get("active_branch", "unknown")
        status_text = self._git(["status", "--porcelain"])
        git_clean = status_text.strip() == ""

        docs_present = {
            "master_roadmap": self.ROADMAP.exists(),
            "c1_checkpoint": self.C1_CHECKPOINT.exists(),
            "engineering_standards": (self.root / "docs" / "ENGINEERING_STANDARDS.md").exists(),
        }

        risks = list(state.get("risk_notes", []) or [])

        if not git_clean:
            risks.append("Working tree has uncommitted changes.")

        if not docs_present["master_roadmap"]:
            risks.append("Master roadmap document is missing.")

        if not docs_present["c1_checkpoint"]:
            risks.append("C1 checkpoint document is missing.")

        return ProjectSummary(
            project=str(state.get("project") or "Jarvis v5"),
            current_phase=str(state.get("current_phase") or "unknown"),
            last_completed_phase=str(state.get("last_completed_phase") or "unknown"),
            status=str(state.get("status") or ""),
            branch=branch,
            git_clean=git_clean,
            last_checkpoint=str(state.get("last_checkpoint") or ""),
            next_steps=list(state.get("next_steps", []) or []),
            recent_commits=list(state.get("last_commits", []) or []),
            docs_present=docs_present,
            risks=risks,
        )

    def summary_text(self) -> str:
        s = self.summarize()

        lines = [
            "Project Intelligence Summary",
            "",
            f"Project: {s.project}",
            f"Current phase: {s.current_phase}",
            f"Last completed phase: {s.last_completed_phase}",
            f"Status: {s.status}",
            f"Branch: {s.branch}",
            f"Git clean: {'yes' if s.git_clean else 'no'}",
            f"Last checkpoint: {s.last_checkpoint}",
            "",
            "Documents:",
        ]

        for name, exists in s.docs_present.items():
            lines.append(f"- {name}: {'OK' if exists else 'MISSING'}")

        if s.next_steps:
            lines.extend(["", "Next steps:"])
            for step in s.next_steps[:8]:
                lines.append(f"- {step}")

        if s.recent_commits:
            lines.extend(["", "Recent commits:"])
            for commit in s.recent_commits[:6]:
                lines.append(f"- {commit}")

        if s.risks:
            lines.extend(["", "Risk notes:"])
            for risk in s.risks[:8]:
                lines.append(f"- {risk}")

        return "\n".join(lines)

    def _git(self, args: list[str]) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.root,
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
    summarizer = ProjectSummarizer()
    summary = summarizer.summarize()
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    print()
    print(summarizer.summary_text())
