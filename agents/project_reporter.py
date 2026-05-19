"""Project Reporter - C3.1.

Generates Markdown project status reports for JARVIS.

Inputs:
- ProjectIntelligence snapshot
- task history / queue
- memory files
- git status / recent commits

Safe behavior:
- no shell execution except ProjectIntelligence safe git reads
- writes reports only under reports/
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.project_intelligence import ProjectIntelligence
REPORT_DIR = ROOT / "reports"
MEMORY_DIR = ROOT / "memory"


class ProjectReporter:
    """Generate readable project reports."""

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)
        self.report_dir = self.root / "reports"

    def build_report(self) -> str:
        pi = ProjectIntelligence(self.root)
        snap = pi.snapshot()

        memory = self._memory_summary()
        tasks = snap.get("task_summary", {})
        warnings = snap.get("warnings", [])

        lines: list[str] = []

        lines.append("# JARVIS Project Report")
        lines.append("")
        lines.append(f"- Generated: `{datetime.now().isoformat(timespec='seconds')}`")
        lines.append(f"- Root: `{snap.get('root')}`")
        lines.append("")

        lines.append("## 1. Executive Summary")
        lines.append("")
        lines.append(f"- Roadmap: {snap.get('roadmap_hint', '-')}")
        lines.append(f"- Next step: {snap.get('next_step', '-')}")
        lines.append(f"- Git state: {'dirty' if snap.get('git_status') else 'clean'}")
        lines.append(f"- Task pending/done/failed: {tasks.get('pending', 0)} / {tasks.get('done', 0)} / {tasks.get('failed', 0)}")
        lines.append("")

        lines.append("## 2. Git Status")
        lines.append("")
        git_status = snap.get("git_status") or []
        if git_status:
            for item in git_status:
                lines.append(f"- `{item}`")
        else:
            lines.append("- Working tree clean.")
        lines.append("")

        lines.append("## 3. Recent Commits")
        lines.append("")
        for commit in (snap.get("recent_commits") or [])[:12]:
            lines.append(f"- `{commit}`")
        lines.append("")

        lines.append("## 4. Task Summary")
        lines.append("")
        lines.append(f"- Pending: `{tasks.get('pending', 0)}`")
        lines.append(f"- Done: `{tasks.get('done', 0)}`")
        lines.append(f"- Failed: `{tasks.get('failed', 0)}`")
        lines.append(f"- Recent: `{tasks.get('recent', '-')}`")
        lines.append(f"- History count: `{tasks.get('history_count', 0)}`")
        lines.append("")

        lines.append("## 5. Memory / Policy Summary")
        lines.append("")
        lines.append(f"- conversations.json entries: `{memory.get('conversations_count', 0)}`")
        lines.append(f"- vector memory present: `{memory.get('vector_memory_present', False)}`")
        lines.append(f"- policy metadata entries: `{memory.get('policy_metadata_count', 0)}`")
        lines.append(f"- sensitive review entries: `{memory.get('sensitive_review_count', 0)}`")
        lines.append(f"- daily-summary allowed entries: `{memory.get('daily_summary_allowed_count', 0)}`")
        lines.append("")

        lines.append("## 6. Important Files")
        lines.append("")
        for name, exists in (snap.get("important_files") or {}).items():
            mark = "OK" if exists else "MISSING"
            lines.append(f"- `{name}`: {mark}")
        lines.append("")

        lines.append("## 7. Warnings / Risks")
        lines.append("")
        if warnings:
            for warning in warnings:
                lines.append(f"- {warning}")
        else:
            lines.append("- No active warnings.")
        lines.append("")

        lines.append("## 8. Recommended Next Action")
        lines.append("")
        lines.append(snap.get("next_step", "-"))
        lines.append("")

        return "\n".join(lines)

    def save_report(self) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.report_dir / f"project_report_{stamp}.md"
        path.write_text(self.build_report(), encoding="utf-8")
        return path

    def _memory_summary(self) -> dict[str, Any]:
        conv_path = self.root / "memory" / "conversations.json"
        chroma_path = self.root / "memory" / "chroma_db"

        summary = {
            "conversations_count": 0,
            "vector_memory_present": chroma_path.exists(),
            "policy_metadata_count": 0,
            "sensitive_review_count": 0,
            "daily_summary_allowed_count": 0,
        }

        if not conv_path.exists():
            return summary

        try:
            data = json.loads(conv_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return summary

            summary["conversations_count"] = len(data)

            for item in data:
                meta = item.get("metadata", {}) if isinstance(item, dict) else {}
                if "memory_action" in meta:
                    summary["policy_metadata_count"] += 1
                if meta.get("memory_action") == "sensitive_review" or meta.get("requires_review") is True:
                    summary["sensitive_review_count"] += 1
                if meta.get("allow_daily_summary") is True:
                    summary["daily_summary_allowed_count"] += 1

        except Exception:
            pass

        return summary


if __name__ == "__main__":
    reporter = ProjectReporter()
    report = reporter.build_report()
    print(report)
