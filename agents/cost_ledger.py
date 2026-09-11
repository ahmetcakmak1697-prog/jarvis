"""Y0-3 - CostLedger.

Limits admitted API execution attempts per day, including failed attempts.
Counts calls, not currency or provider billing; this is not a money cap.
Persists daily count to JSONL so it survives restarts.

daily_limit=0 means unlimited.

Token totals were added by KART_SES_YOLU_DEEPSEEK ADIM 5 (2026-09-11):
`check_and_consume` is a *gate* and runs before a call, when the token
count is not known yet, so `record_usage` was added for the other half --
one line per completed external call, carrying its tokens. Same file,
same shape; "olculmeyen harcama, yonetilemeyen harcamadir."

Scope (negative):
- No actual API calls
- No model selection
- No Telegram
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

    def _today_totals(self) -> dict[str, int]:
        """Today's call count and token totals in one pass over the file.

        Token fields are optional: entries written before token counting
        existed simply contribute 0, so old ledgers stay readable.
        """
        today = self._today()
        totals = {
            "count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        if not self._path.exists():
            return totals
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("date") != today:
                    continue
                totals["count"] += int(entry.get("count", 0))
                for field in ("prompt_tokens", "completion_tokens",
                              "total_tokens"):
                    totals[field] += int(entry.get(field, 0) or 0)
            except Exception:
                pass
        return totals

    def _load_today(self) -> int:
        return self._today_totals()["count"]

    def _append(
        self,
        call_type: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        entry: dict[str, Any] = {
            "date": self._today(),
            "count": 1,
            "call_type": call_type,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        if prompt_tokens or completion_tokens:
            entry["prompt_tokens"] = int(prompt_tokens)
            entry["completion_tokens"] = int(completion_tokens)
            entry["total_tokens"] = int(prompt_tokens) + int(completion_tokens)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def record_usage(
        self,
        call_type: str = "external_call",
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> dict[str, Any]:
        """Record one external call that ALREADY happened, with its tokens.

        `check_and_consume` runs *before* a call, when the token count is
        still unknown. This runs *after* it and appends a single line to
        the same file, in the same shape. No new file, no new directory
        (KART_SES_YOLU_DEEPSEEK ADIM 5).

        Returns today's totals so the caller can show them.
        """
        self._append(call_type, prompt_tokens, completion_tokens)
        return self.stats()

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
        totals = self._today_totals()
        today_count = totals["count"]
        remaining = max(0, self.daily_limit - today_count) if self.daily_limit > 0 else -1
        return {
            "today_count": today_count,
            "daily_limit": self.daily_limit,
            "remaining": remaining,
            "unlimited": self.daily_limit == 0,
            "date": self._today(),
            "prompt_tokens": totals["prompt_tokens"],
            "completion_tokens": totals["completion_tokens"],
            "total_tokens": totals["total_tokens"],
        }
