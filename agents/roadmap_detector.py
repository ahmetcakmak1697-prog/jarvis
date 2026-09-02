"""Roadmap Detector - C2.3.

Detects current roadmap position from project_state, checkpoint docs,
roadmap docs, and recent commits.

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
class RoadmapPosition:
    current_phase: str
    last_completed_phase: str
    next_phase: str
    roadmap_exists: bool
    c1_checkpoint_exists: bool
    project_state_exists: bool
    git_clean: bool
    confidence: int
    evidence: list[str]
    risks: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RoadmapDetector:
    """Detect the active Jarvis roadmap position."""

    ROADMAP = ROOT / "docs" / "JARVIS_v5_MASTER_ROADMAP.md"
    C1_CHECKPOINT = ROOT / "docs" / "C1_MEMORY_CHECKPOINT.md"
    PROJECT_STATE = ROOT / "memory" / "project_state.json"

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.state_store = ProjectStateStore()

    def detect(self) -> RoadmapPosition:
        state = self.state_store.load()

        current_phase = str(state.get("current_phase") or "unknown")
        last_completed = str(state.get("last_completed_phase") or "unknown")

        roadmap_exists = self.ROADMAP.exists()
        c1_exists = self.C1_CHECKPOINT.exists()
        state_exists = self.PROJECT_STATE.exists()

        status_text = self._git(["status", "--porcelain"])
        git_clean = status_text.strip() == ""

        commits = self._recent_commits(12)
        next_steps = list(state.get("next_steps", []) or [])

        next_phase = self._infer_next_phase(current_phase, next_steps, commits)

        evidence: list[str] = []
        risks: list[str] = []

        if state_exists:
            evidence.append("memory/project_state.json exists and is readable.")
        else:
            risks.append("project_state.json is missing; default state may be generated.")

        if roadmap_exists:
            evidence.append("Master roadmap document exists.")
        else:
            risks.append("Master roadmap document is missing.")

        if c1_exists:
            evidence.append("C1 checkpoint document exists.")
        else:
            risks.append("C1 checkpoint document is missing.")

        if commits:
            evidence.append(f"Recent HEAD commit: {commits[0]}")

        if not git_clean:
            risks.append("Working tree has uncommitted changes.")

        if current_phase == "C2" and last_completed == "C1":
            evidence.append("Project state indicates C1 completed and C2 active.")

        confidence = self._confidence(
            current_phase=current_phase,
            last_completed=last_completed,
            roadmap_exists=roadmap_exists,
            c1_exists=c1_exists,
            state_exists=state_exists,
            git_clean=git_clean,
            next_phase=next_phase,
        )

        return RoadmapPosition(
            current_phase=current_phase,
            last_completed_phase=last_completed,
            next_phase=next_phase,
            roadmap_exists=roadmap_exists,
            c1_checkpoint_exists=c1_exists,
            project_state_exists=state_exists,
            git_clean=git_clean,
            confidence=confidence,
            evidence=evidence,
            risks=risks,
        )

    def summary_text(self) -> str:
        pos = self.detect()

        lines = [
            "Roadmap Position",
            "",
            f"Current phase: {pos.current_phase}",
            f"Last completed phase: {pos.last_completed_phase}",
            f"Next phase: {pos.next_phase}",
            f"Confidence: {pos.confidence}/100",
            f"Git clean: {'yes' if pos.git_clean else 'no'}",
            "",
            "Evidence:",
        ]

        if pos.evidence:
            lines.extend(f"- {item}" for item in pos.evidence)
        else:
            lines.append("- No strong evidence found.")

        if pos.risks:
            lines.extend(["", "Risks:"])
            lines.extend(f"- {item}" for item in pos.risks)

        return "\n".join(lines)

    def _infer_next_phase(self, current_phase: str, next_steps: list[str], commits: list[str]) -> str:
        joined_commits = "\n".join(commits).lower()

        completed_markers = {
            "c2.1": (
                "project state model",
                "telegram project state command",
            ),
            "c2.2": (
                "project summarizer",
                "summarizer tests",
                "c2 summarizer tests",
            ),
            "c2.3": (
                "roadmap detector",
                "roadmap tests",
            ),
            "c2.4": (
                "next action planner",
                "planner tests",
            ),
            "c2.5": (
                "project intelligence command",
                "project intel",
            ),
        }

        completed_files = {
            "c2.1": [
                self.root / "agents" / "project_state.py",
                self.root / "tests" / "test_c2_1_project_state.py",
                self.root / "tests" / "test_c2_1_telegram_project_state.py",
            ],
            "c2.2": [
                self.root / "agents" / "project_summarizer.py",
                self.root / "tests" / "test_c2_2_project_summarizer.py",
            ],
            "c2.3": [
                self.root / "agents" / "roadmap_detector.py",
                self.root / "tests" / "test_c2_3_roadmap_detector.py",
            ],
            "c2.4": [
                self.root / "agents" / "next_action_planner.py",
                self.root / "tests" / "test_c2_4_next_action_planner.py",
            ],
            "c2.5": [
                self.root / "tests" / "test_c2_5_telegram_project_intel.py",
            ],
        }

        completed: set[str] = set()
        for phase, markers in completed_markers.items():
            commit_hit = any(marker in joined_commits for marker in markers)
            file_hit = all(path.exists() for path in completed_files.get(phase, []))
            if commit_hit or file_hit:
                completed.add(phase)

        if next_steps:
            for step in next_steps:
                text = str(step).strip()
                low = text.lower()
                if not text:
                    continue

                if low.startswith("c2.1") and "c2.1" in completed:
                    continue
                if low.startswith("c2.2") and "c2.2" in completed:
                    continue
                if low.startswith("c2.3") and "c2.3" in completed:
                    continue
                if low.startswith("c2.4") and "c2.4" in completed:
                    continue
                if low.startswith("c2.5") and "c2.5" in completed:
                    continue

                return text

        if "c2.5" in completed:
            return "C2.6 project intelligence smoke tests"
        if "c2.4" in completed:
            return "C2.5 Telegram/project dashboard command"
        if "c2.3" in completed:
            return "C2.4 next-action planner"
        if "c2.2" in completed:
            return "C2.3 current roadmap detector"
        if "c2.1" in completed:
            return "C2.2 repo/project summarizer"

        if current_phase == "C2":
            return "C2.3 current roadmap detector"

        return "unknown"

    def _confidence(
        self,
        current_phase: str,
        last_completed: str,
        roadmap_exists: bool,
        c1_exists: bool,
        state_exists: bool,
        git_clean: bool,
        next_phase: str,
    ) -> int:
        score = 0

        if current_phase != "unknown":
            score += 20
        if last_completed != "unknown":
            score += 15
        if roadmap_exists:
            score += 15
        if c1_exists:
            score += 15
        if state_exists:
            score += 15
        if next_phase != "unknown":
            score += 15
        if git_clean:
            score += 5

        return min(100, score)

    def _recent_commits(self, limit: int = 10) -> list[str]:
        output = self._git(["log", "--oneline", f"-{limit}"])
        if not output:
            return []
        return [line.strip() for line in output.splitlines() if line.strip()]

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
    detector = RoadmapDetector()
    pos = detector.detect()
    print(json.dumps(pos.to_dict(), ensure_ascii=False, indent=2))
    print()
    print(detector.summary_text())
