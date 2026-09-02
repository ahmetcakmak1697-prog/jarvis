"""Next Action Planner - C2.4.

Deterministic next-action planner for Jarvis v5 project intelligence.

It combines:
- RoadmapDetector
- ProjectSummarizer
- project_state next_steps

No LLM call is made here.
"""

from __future__ import annotations

import json
import sys

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.project_summarizer import ProjectSummarizer
from agents.roadmap_detector import RoadmapDetector


@dataclass
class NextActionPlan:
    recommended_action: str
    reason: str
    current_phase: str
    next_phase: str
    confidence: int
    git_clean: bool
    acceptance_criteria: list[str]
    risks: list[str]
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NextActionPlanner:
    """Plan the next safe project action."""

    def __init__(self):
        self.detector = RoadmapDetector()
        self.summarizer = ProjectSummarizer()

    def plan(self) -> NextActionPlan:
        position = self.detector.detect()
        summary = self.summarizer.summarize()

        recommended = self._recommend(position.next_phase)

        reason = (
            f"{summary.project} is in {position.current_phase}; "
            f"{position.last_completed_phase} is completed; "
            f"roadmap confidence is {position.confidence}/100."
        )

        risks = list(dict.fromkeys((position.risks or []) + (summary.risks or [])))

        if not position.git_clean:
            risks.append("Commit or discard current working tree changes before starting the next patch.")

        acceptance = self._acceptance_for(recommended)

        return NextActionPlan(
            recommended_action=recommended,
            reason=reason,
            current_phase=position.current_phase,
            next_phase=position.next_phase,
            confidence=position.confidence,
            git_clean=position.git_clean,
            acceptance_criteria=acceptance,
            risks=risks,
            evidence=position.evidence,
        )

    def summary_text(self) -> str:
        plan = self.plan()

        lines = [
            "Next Action Plan",
            "",
            f"Recommended action: {plan.recommended_action}",
            f"Reason: {plan.reason}",
            f"Current phase: {plan.current_phase}",
            f"Next phase: {plan.next_phase}",
            f"Confidence: {plan.confidence}/100",
            f"Git clean: {'yes' if plan.git_clean else 'no'}",
            "",
            "Acceptance criteria:",
        ]

        lines.extend(f"- {item}" for item in plan.acceptance_criteria)

        if plan.risks:
            lines.extend(["", "Risks:"])
            lines.extend(f"- {item}" for item in plan.risks[:8])

        if plan.evidence:
            lines.extend(["", "Evidence:"])
            lines.extend(f"- {item}" for item in plan.evidence[:8])

        return "\n".join(lines)

    def _recommend(self, next_phase: str) -> str:
        low = str(next_phase or "").lower()

        if low.startswith("c2.3"):
            return "C2.4 next-action planner"
        if low.startswith("c2.4"):
            return "C2.4 next-action planner"
        if low.startswith("c2.5"):
            return "C2.5 Telegram/project dashboard command"
        if low.startswith("c2.6"):
            return "C2.6 project intelligence smoke tests"

        return next_phase or "unknown"

    def _acceptance_for(self, action: str) -> list[str]:
        low = str(action or "").lower()

        if low.startswith("c2.4"):
            return [
                "agents/next_action_planner.py exists.",
                "Planner returns recommended_action, reason, risks, evidence, and acceptance criteria.",
                "Planner is deterministic and makes no LLM call.",
                "Planner has tests.",
                "C2 smoke suite includes planner tests.",
            ]

        if low.startswith("c2.5"):
            return [
                "Telegram command exposes project intelligence summary.",
                "Command output includes current phase, next action, confidence, and risks.",
                "Command has tests.",
            ]

        if low.startswith("c2.6"):
            return [
                "Full C2 project smoke suite passes.",
                "Main smoke suite passes.",
                "Git status is clean.",
            ]

        return [
            "Action is defined.",
            "Tests are added.",
            "Smoke suite passes.",
            "Git status is clean.",
        ]


if __name__ == "__main__":
    planner = NextActionPlanner()
    plan = planner.plan()
    print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    print()
    print(planner.summary_text())
