from __future__ import annotations

import json
from pathlib import Path
from typing import Any


QUEUE_PATH = Path("memory/task_queue.json")
HISTORY_PATH = Path("memory/task_history.json")


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except Exception:
        pass
    return []


def get_task_snapshot() -> dict[str, Any]:
    pending_items = _read_json_list(QUEUE_PATH)
    history_items = _read_json_list(HISTORY_PATH)

    pending = [t for t in pending_items if t.get("status") in ("pending", "running", None)]
    running_pending = [t for t in pending_items if t.get("status") == "running"]

    completed_items = [t for t in history_items if t.get("status") in ("done", "completed")]
    failed_items = [t for t in history_items if t.get("status") == "failed"]

    recent = history_items[-5:]

    return {
        "pending": len(pending),
        "running": len(running_pending),
        "completed": len(completed_items),
        "failed": len(failed_items),
        "recent": recent,
        "queue_path": str(QUEUE_PATH),
        "history_path": str(HISTORY_PATH),
        "line": (
            f"Görev durumu: bekleyen {len(pending)}, çalışan {len(running_pending)}, "
            f"tamamlanan {len(completed_items)}, hatalı {len(failed_items)}."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(get_task_snapshot(), ensure_ascii=False, indent=2))
