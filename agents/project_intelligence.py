"""Project Intelligence - C2.1.

Read-only project status intelligence for JARVIS.

Goals:
- summarize git status
- summarize recent commits
- inspect important roadmap/runtime files
- inspect task history
- suggest next safe project step

No file writes. No arbitrary command execution beyond safe git reads.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ProjectSnapshot:
    ok: bool
    timestamp: str
    root: str
    git_status: list[str]
    recent_commits: list[str]
    important_files: dict[str, bool]
    task_summary: dict[str, Any]
    roadmap_hint: str
    next_step: str
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProjectIntelligence:
    """Read-only project state analyzer."""

    IMPORTANT_FILES = [
        "jarvis_server.py",
        "jarvis_brain.py",
        "README.md",
        "BOOT_CHECK.md",
        "start_jarvis_remote.ps1",
        "tools/telegram_agent.py",
        "agents/memory_policy.py",
        "agents/memory_scorer.py",
        "agents/daily_digest.py",
        "agents/task_executor.py",
        "memory/task_history.json",
        "memory/task_queue.json",
    ]

    def __init__(self, root: Path | str = ROOT):
        self.root = Path(root)

    def snapshot(self) -> dict[str, Any]:
        warnings: list[str] = []

        git_status = self._git(["status", "--short"])
        recent_commits = self._git(["log", "--oneline", "-12"])

        important_files = {
            file: (self.root / file).exists()
            for file in self.IMPORTANT_FILES
        }

        task_summary = self._task_summary()
        roadmap_hint = self._roadmap_hint(recent_commits)
        next_step = self._next_step(git_status, recent_commits, important_files)

        if git_status:
            warnings.append("Working tree temiz degil; commit veya revert gerekebilir.")

        missing = [name for name, exists in important_files.items() if not exists]
        if missing:
            warnings.append("Eksik onemli dosyalar: " + ", ".join(missing[:6]))

        snap = ProjectSnapshot(
            ok=True,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            root=str(self.root),
            git_status=git_status,
            recent_commits=recent_commits,
            important_files=important_files,
            task_summary=task_summary,
            roadmap_hint=roadmap_hint,
            next_step=next_step,
            warnings=warnings,
        )

        return snap.to_dict()

    def brief(self) -> str:
        s = self.snapshot()

        lines = [
            "JARVIS Project Intelligence",
            f"Zaman: {s['timestamp']}",
            f"Kok: {s['root']}",
            "",
            "Git:",
        ]

        if s["git_status"]:
            lines.extend("  " + item for item in s["git_status"])
        else:
            lines.append("  temiz")

        lines.append("")
        lines.append("Son commitler:")
        for item in s["recent_commits"][:6]:
            lines.append("  " + item)

        lines.append("")
        lines.append("Task ozeti:")
        ts = s["task_summary"]
        lines.append(f"  pending: {ts.get('pending', 0)}")
        lines.append(f"  done: {ts.get('done', 0)}")
        lines.append(f"  failed: {ts.get('failed', 0)}")
        lines.append(f"  recent: {ts.get('recent', '-')}")

        lines.append("")
        lines.append("Roadmap:")
        lines.append("  " + s["roadmap_hint"])
        lines.append("  Siradaki: " + s["next_step"])

        if s["warnings"]:
            lines.append("")
            lines.append("Uyarilar:")
            for w in s["warnings"]:
                lines.append("  - " + w)

        return "\n".join(lines)

    def _git(self, args: list[str]) -> list[str]:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
            )

            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()

            if result.returncode != 0:
                return [f"git hata: {err or out or result.returncode}"]

            if not out:
                return []

            return [line.strip() for line in out.splitlines() if line.strip()]
        except Exception as exc:
            return [f"git okunamadi: {exc}"]

    def _safe_json_list(self, rel_path: str) -> list[dict[str, Any]]:
        path = self.root / rel_path
        if not path.exists():
            return []

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
        except Exception:
            pass

        return []

    def _task_summary(self) -> dict[str, Any]:
        queue = self._safe_json_list("memory/task_queue.json")
        history = self._safe_json_list("memory/task_history.json")

        done = sum(1 for item in history if item.get("status") == "done")
        failed = sum(1 for item in history if item.get("status") == "failed")

        recent = "-"
        if history:
            last = history[-1]
            recent = f"{last.get('type', 'task')} | {last.get('status', '-')}"

        return {
            "pending": len(queue),
            "done": done,
            "failed": failed,
            "recent": recent,
            "history_count": len(history),
        }

    def _roadmap_hint(self, commits: list[str]) -> str:
        text = "\n".join(commits).lower()

        if "store memory policy metadata" in text or "filter daily digest" in text:
            return "C1 Hafiza politikasi tamamlandi; C2 Proje zekasi basliyor."

        if "telegram agent" in text:
            return "B2.7 Tailscale + Telegram tamamlandi; C1/C2 akisina devam."

        if "task api allowlist" in text:
            return "B2.6 task guvenligi tamamlandi."

        return "Roadmap durumu commit gecmisinden sinirli olarak cikarildi."

    def _next_step(
        self,
        git_status: list[str],
        commits: list[str],
        important_files: dict[str, bool],
    ) -> str:
        if git_status:
            return "Once working tree temizlenmeli: test et, commit at veya geri al."

        if not important_files.get("agents/project_intelligence.py", True):
            return "C2.1 ProjectIntelligence dosyasini ekle."

        text = "\n".join(commits).lower()

        if "project intelligence" not in text:
            return "C2.1 ProjectIntelligence testlerini calistir ve commit at."

        return "C2.2 ProjectIntelligence'i Telegram /status veya yeni /project komutuna bagla."


if __name__ == "__main__":
    pi = ProjectIntelligence()
    print(pi.brief())
