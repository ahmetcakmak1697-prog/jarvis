"""Task Executor - background task queue."""
import json
import threading
import queue
from pathlib import Path
from datetime import datetime
import traceback


class TaskExecutor:
    def __init__(self):
        self.queue_path = Path("memory/task_queue.json")
        self.history_path = Path("memory/task_history.json")
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.q = queue.Queue()
        self.running = False
        self.worker = None
        self._handlers = {}

    def register(self, task_type, handler):
        self._handlers[task_type] = handler

    def add(self, task_type, params, priority=5):
        task = {
            "id": f"t_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "type": task_type, "params": params,
            "priority": priority, "status": "pending",
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
                task["result"] = str(result)[:1000]
        except Exception as e:
            task["status"] = "failed"
            task["error"] = f"{e}\n{traceback.format_exc()[:500]}"
        task["finished"] = datetime.now().isoformat()
        self._save_history(task)
        self._remove_pending(task["id"])

    def _save_pending(self, task):
        ts = self._load_pending()
        ts.append(task)
        self.queue_path.write_text(
            json.dumps(ts, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load_pending(self):
        if self.queue_path.exists():
            try:
                return json.loads(self.queue_path.read_text(encoding='utf-8'))
            except:
                pass
        return []

    def _remove_pending(self, tid):
        ts = self._load_pending()
        ts = [t for t in ts if t.get("id") != tid]
        self.queue_path.write_text(
            json.dumps(ts, ensure_ascii=False, indent=2), encoding='utf-8')

    def _save_history(self, task):
        h = []
        if self.history_path.exists():
            try:
                h = json.loads(self.history_path.read_text(encoding='utf-8'))
            except:
                pass
        h.append(task)
        h = h[-200:]
        self.history_path.write_text(
            json.dumps(h, ensure_ascii=False, indent=2), encoding='utf-8')

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
                hist = json.loads(self.history_path.read_text(encoding='utf-8'))
            except:
                pass
        return {
            "pending": len(pend),
            "completed": sum(1 for t in hist if t.get("status") == "done"),
            "failed": sum(1 for t in hist if t.get("status") == "failed"),
            "recent": hist[-5:],
            "running": self.running
        }
