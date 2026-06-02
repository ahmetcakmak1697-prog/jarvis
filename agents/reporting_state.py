"""Reporting State - C3.1.

Machine-readable reporting state model for Jarvis v5.

Purpose:
- define project-aware report state
- summarize current project/reporting context
- provide a deterministic base for future report generation
"""

from __future__ import annotations

import json
import subprocess
import sys

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.project_summarizer import ProjectSummarizer
from agents.next_action_planner import NextActionPlanner


@dataclass
class ReportingState:
    project: str
    current_phase: str
    report_layer_phase: str
    status: str
    branch: str
    git_clean: bool
    last_checkpoint: str
    recommended_next_action: str
    available_report_types: list[str]
    recent_commits: list[str]
    smoke_commands: list[str]
    risks: list[str]
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReportingStateStore:
    """Build reporting state from C2 project intelligence modules."""

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.summarizer = ProjectSummarizer()
        self.planner = NextActionPlanner()

    def build(self) -> ReportingState:
        summary = self.summarizer.summarize()
        plan = self.planner.plan()

        risks = list(dict.fromkeys((summary.risks or []) + (plan.risks or [])))

        return ReportingState(
            project=summary.project,
            current_phase=summary.current_phase,
            report_layer_phase="C3",
            status="C2 completed; C3 reporting layer started",
            branch=summary.branch,
            git_clean=summary.git_clean,
            last_checkpoint="docs/C2_PROJECT_INTELLIGENCE_CHECKPOINT.md",
            recommended_next_action=plan.recommended_action,
            available_report_types=[
                "daily_project_summary",
                "weekly_project_summary",
                "checkpoint_summary",
                "smoke_test_summary",
                "next_action_summary",
            ],
            recent_commits=summary.recent_commits[:8],
            smoke_commands=[
                "python .\\tests\\c2_project_smoke_suite.py",
                "python .\\tests\\run_smoke_suite.py",
            ],
            risks=risks,
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )

    def summary_text(self) -> str:
        state = self.build()

        lines = [
            "Reporting State",
            "",
            f"Project: {state.project}",
            f"Current phase: {state.current_phase}",
            f"Reporting layer: {state.report_layer_phase}",
            f"Status: {state.status}",
            f"Branch: {state.branch}",
            f"Git clean: {'yes' if state.git_clean else 'no'}",
            f"Last checkpoint: {state.last_checkpoint}",
            f"Recommended next action: {state.recommended_next_action}",
            "",
            "Available report types:",
        ]

        lines.extend(f"- {item}" for item in state.available_report_types)

        if state.recent_commits:
            lines.extend(["", "Recent commits:"])
            lines.extend(f"- {commit}" for commit in state.recent_commits[:6])

        if state.smoke_commands:
            lines.extend(["", "Smoke commands:"])
            lines.extend(f"- {cmd}" for cmd in state.smoke_commands)

        if state.risks:
            lines.extend(["", "Risks:"])
            lines.extend(f"- {risk}" for risk in state.risks[:8])

        return "\n".join(lines)


if __name__ == "__main__":
    store = ReportingStateStore()
    state = store.build()
    print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))
    print()
    print(store.summary_text())
