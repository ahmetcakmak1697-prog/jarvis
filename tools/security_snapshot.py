from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any


SECURITY_DB = Path("memory/jarvis_security.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(SECURITY_DB))
    conn.row_factory = sqlite3.Row
    return conn


def get_security_snapshot() -> dict[str, Any]:
    """
    Read-only security snapshot for ProactiveCore.
    This module intentionally does not import jarvis_server.py to avoid circular imports.
    """
    now = time.time()

    if not SECURITY_DB.exists():
        return {
            "level": "unknown",
            "shield": "missing-db",
            "failed_login_24h": 0,
            "failed_login_total": 0,
            "blocked_ips": 0,
            "active_sessions": 0,
            "last_fail": None,
            "last_external": None,
            "line": "Koruma veritabanı henüz oluşmadı.",
        }

    try:
        conn = _connect()

        failed_total = conn.execute(
            "SELECT COUNT(*) AS n FROM login_attempts WHERE success=0"
        ).fetchone()["n"]

        failed_24h = conn.execute(
            "SELECT COUNT(*) AS n FROM login_attempts WHERE success=0 AND ts>=?",
            (now - 86400,),
        ).fetchone()["n"]

        blocked_rows = conn.execute(
            "SELECT ip, blocked_until, reason, attempts FROM ip_blocks WHERE blocked_until>?",
            (now,),
        ).fetchall()

        sessions = conn.execute(
            "SELECT COUNT(*) AS n FROM sessions WHERE expires_at>?",
            (now,),
        ).fetchone()["n"]

        last_fail_row = conn.execute(
            "SELECT ts, ip, reason FROM login_attempts WHERE success=0 ORDER BY ts DESC LIMIT 1"
        ).fetchone()

        last_external_row = conn.execute(
            "SELECT ts, ip, path FROM access_logs WHERE external=1 ORDER BY ts DESC LIMIT 1"
        ).fetchone()

        conn.close()

        blocked_ips = [
            {
                "ip": row["ip"],
                "blocked_until": float(row["blocked_until"]),
                "reason": row["reason"],
                "attempts": int(row["attempts"] or 0),
            }
            for row in blocked_rows
        ]

        if blocked_ips:
            level = "alarm"
            line = f"Koruma Kalkanı alarmda. {len(blocked_ips)} IP geçici olarak kilitli."
        elif failed_24h >= 3:
            level = "warning"
            line = f"Koruma Kalkanı uyarıda. Son 24 saatte {failed_24h} hatalı giriş denemesi var."
        else:
            level = "normal"
            line = "Koruma Kalkanı aktif. Olağan dışı bir hareket saptanmadı."

        last_fail = None
        if last_fail_row:
            last_fail = {
                "ts": float(last_fail_row["ts"]),
                "ip": last_fail_row["ip"],
                "reason": last_fail_row["reason"],
            }

        last_external = None
        if last_external_row:
            last_external = {
                "ts": float(last_external_row["ts"]),
                "ip": last_external_row["ip"],
                "path": last_external_row["path"],
            }

        return {
            "level": level,
            "shield": "active",
            "failed_login_24h": int(failed_24h or 0),
            "failed_login_total": int(failed_total or 0),
            "blocked_ips": len(blocked_ips),
            "blocked_ip_list": blocked_ips,
            "active_sessions": int(sessions or 0),
            "last_fail": last_fail,
            "last_external": last_external,
            "line": line,
        }

    except Exception as e:
        return {
            "level": "unknown",
            "shield": "error",
            "failed_login_24h": 0,
            "failed_login_total": 0,
            "blocked_ips": 0,
            "active_sessions": 0,
            "last_fail": None,
            "last_external": None,
            "line": f"Koruma verisi okunamadı: {str(e)[:120]}",
        }


if __name__ == "__main__":
    import json
    print(json.dumps(get_security_snapshot(), ensure_ascii=False, indent=2))
