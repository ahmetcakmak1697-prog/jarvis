"""
Auto Updater - Git ile otomatik güncelleme
Sen onay verirsen JARVIS kendini günceller.

KULLANIM:
  from agents.auto_updater import AutoUpdater
  u = AutoUpdater()
  if u.has_updates():
      u.update()  # Sen onay verirsen
"""
import subprocess
from pathlib import Path
from datetime import datetime


class AutoUpdater:
    def __init__(self, repo_path: str = "."):
        self.repo = Path(repo_path).resolve()

    def _run_git(self, *args) -> dict:
        try:
            r = subprocess.run(
                ["git"] + list(args),
                cwd=self.repo, capture_output=True, text=True,
                timeout=30, encoding='utf-8', errors='replace')
            return {"out": r.stdout.strip(), "err": r.stderr.strip(),
                    "ok": r.returncode == 0}
        except Exception as e:
            return {"out": "", "err": str(e), "ok": False}

    def is_git_repo(self) -> bool:
        return (self.repo / ".git").exists()

    def current_branch(self) -> str:
        if not self.is_git_repo():
            return ""
        r = self._run_git("branch", "--show-current")
        return r["out"]

    def has_updates(self) -> dict:
        """Uzakta yeni commit var mı?"""
        if not self.is_git_repo():
            return {"available": False, "reason": "Git repo değil"}

        self._run_git("fetch", "--quiet")

        local = self._run_git("rev-parse", "HEAD")["out"]
        remote = self._run_git("rev-parse", "@{u}")["out"]

        if not local or not remote:
            return {"available": False, "reason": "Uzak takip yok"}

        if local == remote:
            return {"available": False, "reason": "Güncel"}

        log = self._run_git("log", "--oneline", f"{local}..{remote}")
        commits = log["out"].splitlines()[:10]

        return {
            "available": True,
            "local":     local[:8],
            "remote":    remote[:8],
            "commits":   commits,
            "count":     len(commits),
        }

    def update(self, restart_after: bool = False) -> dict:
        """Pull yap. restart_after=True ise sunucuyu yeniden başlat sinyali yolla."""
        if not self.is_git_repo():
            return {"ok": False, "reason": "Git repo değil"}

        # Yedek
        backup = self._run_git("stash", "push", "-m",
                               f"auto-{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        pull = self._run_git("pull", "--rebase")

        if not pull["ok"]:
            self._run_git("stash", "pop")  # geri al
            return {"ok": False, "error": pull["err"]}

        # requirements değişti mi?
        diff = self._run_git("diff", "HEAD@{1}", "HEAD", "--name-only")
        req_changed = "requirements.txt" in diff["out"]

        if restart_after:
            Path("RESTART_REQUESTED").write_text(
                datetime.now().isoformat(), encoding='utf-8')

        return {
            "ok": True,
            "output": pull["out"],
            "requirements_changed": req_changed,
            "restart_requested": restart_after,
        }


if __name__ == "__main__":
    u = AutoUpdater()
    print(f"Branch: {u.current_branch()}")
    status = u.has_updates()
    print(status)
