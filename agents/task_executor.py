"""Task Executor - background task queue."""
from __future__ import annotations

import json
import os
import platform
import queue
import subprocess
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


class TaskExecutor:
    def __init__(self):
        self.queue_path = Path("memory/task_queue.json")
        self.history_path = Path("memory/task_history.json")
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.q = queue.Queue()
        self.running = False
        self.worker = None
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register built-in safe task handlers.

        These handlers only read local project/runtime state.
        They do not execute arbitrary user commands.
        """
        self.register("health_check", self._handle_health_check)
        self.register("self_test", self._handle_self_test)
        self.register("project_status", self._handle_project_status)
        self.register("memory_summary", self._handle_memory_summary)

    def register(self, task_type, handler):
        self._handlers[task_type] = handler

    def add(self, task_type, params=None, priority=5):
        if params is None:
            params = {}

        task = {
            "id": f"t_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "type": task_type,
            "params": params,
            "priority": priority,
            "status": "pending",
            "created": datetime.now().isoformat()
        }
        self._save_pending(task)
        self.q.put((priority, task["created"], task))
        return task["id"]

    def start(self):
        if self.running:
            return
        self.running = True
        self._restore()
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                _, _, task = self.q.get(timeout=1)
            except queue.Empty:
                continue
            self._run_task(task)

    def _run_task(self, task):
        task["status"] = "running"
        task["started"] = datetime.now().isoformat()
        try:
            handler = self._handlers.get(task["type"])
            if not handler:
                task["status"] = "failed"
                task["error"] = f"Handler yok: {task['type']}"
            else:
                result = handler(**task.get("params", {}))
                task["status"] = "done"
                task["result"] = self._safe_result(result)
        except Exception as e:
            task["status"] = "failed"
            task["error"] = f"{e}\n{traceback.format_exc()[:500]}"
        task["finished"] = datetime.now().isoformat()
        self._save_history(task)
        self._remove_pending(task["id"])

    def _safe_result(self, result):
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)[:2000]
        except Exception:
            return str(result)[:2000]

    def _save_pending(self, task):
        ts = self._load_pending()
        ts.append(task)
        self.queue_path.write_text(
            json.dumps(ts, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_pending(self):
        if self.queue_path.exists():
            try:
                data = json.loads(self.queue_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return []

    def _remove_pending(self, tid):
        ts = self._load_pending()
        ts = [t for t in ts if t.get("id") != tid]
        self.queue_path.write_text(
            json.dumps(ts, ensure_ascii=False, indent=2), encoding="utf-8")

    def _save_history(self, task):
        h = []
        if self.history_path.exists():
            try:
                data = json.loads(self.history_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    h = data
            except Exception:
                pass
        h.append(task)
        h = h[-200:]
        self.history_path.write_text(
            json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")

    def _restore(self):
        for task in self._load_pending():
            if task.get("status") in ("pending", "running"):
                task["status"] = "pending"
                self.q.put((task.get("priority", 5),
                            task.get("created", ""), task))

    def status(self):
        pend = self._load_pending()
        hist = []
        if self.history_path.exists():
            try:
                data = json.loads(self.history_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    hist = data
            except Exception:
                pass
        return {
            "pending": len(pend),
            "completed": sum(1 for t in hist if t.get("status") == "done"),
            "failed": sum(1 for t in hist if t.get("status") == "failed"),
            "recent": hist[-5:],
            "running": self.running
        }

    # ---------------------------------------------------------------------
    # B2.4 built-in task handlers
    # ---------------------------------------------------------------------

    def _handle_health_check(self, **kwargs):
        """Return a safe local health summary."""
        memory_dir = Path("memory")
        queue_items = self._load_pending()
        history_items = self._load_history()

        return {
            "handler": "health_check",
            "ok": True,
            "timestamp": datetime.now().isoformat(),
            "runtime": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "cwd": str(Path.cwd()),
                "pid": os.getpid(),
            },
            "paths": {
                "memory_exists": memory_dir.exists(),
                "queue_path": str(self.queue_path),
                "queue_exists": self.queue_path.exists(),
                "history_path": str(self.history_path),
                "history_exists": self.history_path.exists(),
            },
            "tasks": {
                "pending": len(queue_items),
                "history": len(history_items),
                "done": sum(1 for t in history_items if t.get("status") == "done"),
                "failed": sum(1 for t in history_items if t.get("status") == "failed"),
            },
            "note": "Health check completed safely.",
        }

    def _handle_self_test(self, **kwargs):
        """Run safe internal checks without arbitrary command execution."""
        checks = []

        def add_check(name, passed, detail):
            checks.append({
                "name": name,
                "passed": bool(passed),
                "detail": detail,
            })

        add_check("memory_dir", Path("memory").exists(), "memory klasörü kontrol edildi")
        add_check("queue_json", isinstance(self._load_pending(), list), "task_queue.json okunabilir")
        add_check("history_json", isinstance(self._load_history(), list), "task_history.json okunabilir")
        add_check("handlers", all(
            name in self._handlers
            for name in ("health_check", "self_test", "project_status", "memory_summary")
        ), "B2.4 handler kayıtları kontrol edildi")

        ok = all(c["passed"] for c in checks)

        return {
            "handler": "self_test",
            "ok": ok,
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
        }

    def _handle_project_status(self, **kwargs):
        """Return safe project/git status summary."""
        git_info = self._safe_git_status()

        important_paths = [
            "jarvis_server.py",
            "jarvis_brain.py",
            "agents",
            "tools",
            "memory",
            "README.md",
            "BOOT_CHECK.md",
        ]

        return {
            "handler": "project_status",
            "ok": True,
            "timestamp": datetime.now().isoformat(),
            "project": {
                "cwd": str(Path.cwd()),
                "important_paths": {
                    p: Path(p).exists()
                    for p in important_paths
                },
            },
            "git": git_info,
            "tasks": self.status(),
        }

    def _handle_memory_summary(self, **kwargs):
        """Summarize safe local memory/task files."""
        memory_dir = Path("memory")
        files = []

        if memory_dir.exists():
            for path in sorted(memory_dir.glob("*.json")):
                item = {
                    "name": path.name,
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                }
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        item["type"] = "list"
                        item["items"] = len(data)
                    elif isinstance(data, dict):
                        item["type"] = "dict"
                        item["keys"] = len(data.keys())
                    else:
                        item["type"] = type(data).__name__
                except Exception as e:
                    item["type"] = "unreadable_json"
                    item["error"] = str(e)[:200]
                files.append(item)

        return {
            "handler": "memory_summary",
            "ok": True,
            "timestamp": datetime.now().isoformat(),
            "memory_exists": memory_dir.exists(),
            "files": files,
        }

    def _load_history(self):
        if self.history_path.exists():
            try:
                data = json.loads(self.history_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return []

    def _safe_git_status(self):
        result = {
            "available": False,
            "branch": None,
            "last_commit": None,
            "dirty": None,
            "error": None,
        }

        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="replace",
            )
            last_commit = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="replace",
            )
            status = subprocess.run(
                ["git", "status", "--short"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="replace",
            )

            if branch.returncode == 0 and last_commit.returncode == 0 and status.returncode == 0:
                result["available"] = True
                result["branch"] = branch.stdout.strip()
                result["last_commit"] = last_commit.stdout.strip()
                result["dirty"] = bool(status.stdout.strip())
            else:
                result["error"] = (
                    branch.stderr.strip()
                    or last_commit.stderr.strip()
                    or status.stderr.strip()
                    or "git bilgisi alınamadı"
                )[:300]
        except Exception as e:
            result["error"] = str(e)[:300]

        return result
