"""
j0_live_status.py — "Nerede kald\u0131k?" live status tool.

Read-only. Reads git log / git status / roadmap_state.json
at runtime. No RAG, no static snapshot, no web/API calls.

Inject git_runner and roadmap_loader for test isolation.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ROADMAP_PATH = _REPO_ROOT / "roadmap_state.json"


# ---------------------------------------------------------------------------
# Injectable interfaces
# ---------------------------------------------------------------------------

GitRunner = Callable[[List[str]], str]
"""Given git args, return stdout text. Raises on failure."""

RoadmapLoader = Callable[[], Any]
"""Return parsed roadmap_state.json dict. Raises on failure."""


def _default_git_runner(args: List[str]) -> str:
    # -c safe.directory per-command: avoids exit 128 when repo is owned by a different
    # user (Codex / CI / elevated shell). Does not mutate global git config.
    # .as_posix() is required: git rejects backslash paths on Windows (exit 128).
    cmd = ["git", "-c", f"safe.directory={_REPO_ROOT.as_posix()}"] + args
    return subprocess.check_output(
        cmd, cwd=str(_REPO_ROOT), text=True, encoding="utf-8", stderr=subprocess.STDOUT
    )


def _default_roadmap_loader() -> Any:
    if not _ROADMAP_PATH.is_file():
        raise FileNotFoundError(str(_ROADMAP_PATH))
    return json.loads(_ROADMAP_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class LiveStatus:
    head_commit_hash: str
    head_commit_title: str
    recent_commits: List[str]
    working_tree_clean: bool
    in_progress_steps: List[dict] = field(default_factory=list)
    todo_steps: List[dict] = field(default_factory=list)
    faz3e1: Optional[dict] = None
    # Human-readable summary parts
    summary_lines: List[str] = field(default_factory=list, init=False, repr=False)
    _roadmap_loaded: bool = field(default=False, repr=False)

    def _ensure_summary(self) -> None:
        if self.summary_lines:
            return
        lines: List[str] = []
        lines.append(f"HEAD: {self.head_commit_hash} - {self.head_commit_title}")
        lines.append("")
        if self.recent_commits:
            lines.append("Son commit'ler:")
            for c in self.recent_commits:
                lines.append(f"  {c}")
            lines.append("")
        status_label = "TEM\u0130Z" if self.working_tree_clean else "K\u0130RL\u0130"
        lines.append(f"\u00c7al\u0131\u015fma a\u011fac\u0131: {status_label}")
        lines.append("")
        if self.in_progress_steps:
            lines.append("\u015eu an devam eden:")
            for s in self.in_progress_steps:
                sid = s.get("id", "?")
                title = s.get("title", "?")
                lines.append(f"  {sid} - {title}")
            lines.append("")
        if self.todo_steps:
            lines.append("S\u0131ra bekleyen:")
            for s in self.todo_steps:
                sid = s.get("id", "?")
                title = s.get("title", "?")
                lines.append(f"  {sid} - {title}")
            lines.append("")
        if self.faz3e1 is not None:
            lines.append("FAZ-3-E1 durumu: in_progress")
            lines.append("  - Proaktif policy motoru tamam")
            lines.append("  - Runtime delivery / Telegram g\u00f6nderme / scheduler /")
            lines.append("    background loop hen\u00fcz devrede de\u011fil")
            lines.append("  - FAZ-3-E1 \u015fimdilik park edilmi\u015f durumda")
        lines.append("")
        lines.append("('nerede kald\u0131k' canl\u0131 ara\u00e7t\u0131r - RAG de\u011fil)")
        self.summary_lines = lines

    def text_summary(self) -> str:
        self._ensure_summary()
        return "\n".join(self.summary_lines)


# ---------------------------------------------------------------------------
# Core: collect status using injected dependencies
# ---------------------------------------------------------------------------


def collect_status(
    git_runner: GitRunner,
    roadmap_loader: RoadmapLoader,
) -> LiveStatus:
    git_log = git_runner(["log", "--oneline", "-6", "--no-decorate"]).strip().splitlines()
    head_commit_hash = ""
    head_commit_title = ""
    recent_commits: List[str] = []
    if git_log and git_log[0]:
        parts = git_log[0].split(" ", 1)
        head_commit_hash = parts[0]
        head_commit_title = parts[1] if len(parts) > 1 else ""
        recent_commits = git_log[1:]

    git_status_out = git_runner(["status", "--porcelain"]).strip()
    working_tree_clean = len(git_status_out) == 0

    in_progress_steps: List[dict] = []
    todo_steps: List[dict] = []
    faz3e1: Optional[dict] = None
    roadmap_loaded = False
    try:
        roadmap = roadmap_loader()
        steps: List[dict] = roadmap.get("steps", [])
        for s in steps:
            sid = s.get("id", "")
            status = s.get("status", "")
            if status == "in_progress":
                in_progress_steps.append(s)
                if sid == "FAZ-3-E1":
                    faz3e1 = s
            elif status == "todo":
                todo_steps.append(s)
        roadmap_loaded = True
    except Exception:
        pass

    return LiveStatus(
        head_commit_hash=head_commit_hash,
        head_commit_title=head_commit_title,
        recent_commits=recent_commits,
        working_tree_clean=working_tree_clean,
        in_progress_steps=in_progress_steps,
        todo_steps=todo_steps,
        faz3e1=faz3e1,
        _roadmap_loaded=roadmap_loaded,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    from _utf8io import configure_utf8_stdio

    configure_utf8_stdio()
    import traceback
    try:
        status = collect_status(
            git_runner=_default_git_runner,
            roadmap_loader=_default_roadmap_loader,
        )
        print(status.text_summary())
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
