"""Y0-3 - CostLedger.

Limits admitted API execution attempts per day, including failed attempts.
Counts calls, not tokens, currency, or provider billing; this is not a money cap.
Persists daily count to JSONL so it survives restarts.

daily_limit=0 means unlimited.

Scope (negative):
- No actual API calls
- No model selection
- No Telegram
- No token counting (placeholder for future)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILENAME = "cost_ledger.jsonl"


class CostLedger:
    """Simple daily-limit gate for external calls."""

    def __init__(
        self,
        daily_limit: int = 50,
        data_root: Path | str | None = None,
    ) -> None:
        self.daily_limit = max(0, int(daily_limit))
        root = Path(data_root) if data_root is not None else ROOT / "memory"
        root.mkdir(parents=True, exist_ok=True)
        self._path = root / DEFAULT_FILENAME

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _load_today(self) -> int:
        today = self._today()
        if not self._path.exists():
            return 0
        count = 0
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("date") == today:
                    count += int(entry.get("count", 0))
            except Exception:
                pass
        return count

    def _append(self, call_type: str) -> None:
        entry = {
            "date": self._today(),
            "count": 1,
            "call_type": call_type,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def check_and_consume(
        self,
        call_type: str = "external_call",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Check limit and optionally consume one unit."""
        today_count = self._load_today()

        # unlimited
        if self.daily_limit == 0:
            if not dry_run:
                self._append(call_type)
            return {
                "allowed": True,
                "reason": "unlimited",
                "today_count": today_count + (0 if dry_run else 1),
                "daily_limit": 0,
            }

        if today_count >= self.daily_limit:
            return {
                "allowed": False,
                "reason": "daily_limit_exceeded",
                "today_count": today_count,
                "daily_limit": self.daily_limit,
            }

        if not dry_run:
            self._append(call_type)
            today_count += 1

        return {
            "allowed": True,
            "reason": "within_limit",
            "today_count": today_count,
            "daily_limit": self.daily_limit,
        }

    def stats(self) -> dict[str, Any]:
        """Return current daily usage stats."""
        today_count = self._load_today()
        remaining = max(0, self.daily_limit - today_count) if self.daily_limit > 0 else -1
        return {
            "today_count": today_count,
            "daily_limit": self.daily_limit,
            "remaining": remaining,
            "unlimited": self.daily_limit == 0,
            "date": self._today(),
        }
