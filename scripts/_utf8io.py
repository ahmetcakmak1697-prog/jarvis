"""
scripts/_utf8io.py — Shared UTF-8 I/O helpers for JARVIS CLI scripts.

Windows defaults stdout/stderr to the system codepage (e.g. CP1254/CP1252).
Any JARVIS CLI that prints Turkish text must call configure_utf8_stdio() before
writing anything. This module is the single source of that logic.

Usage in every CLI entrypoint:
    from _utf8io import configure_utf8_stdio, dump_json_to_stdout

    def main():
        configure_utf8_stdio()
        ...
        dump_json_to_stdout(result)
"""
from __future__ import annotations

import json
import sys
from typing import Any, TextIO


def configure_utf8_stdio() -> None:
    """Reconfigure stdout to UTF-8/strict and stderr to UTF-8/replace.

    Must be called at the top of every CLI main() before any print() or JSON
    output. No-op on streams that do not support reconfigure (BytesIO, etc.).
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def dump_json(payload: dict[str, Any], stream: TextIO | None = None) -> None:
    """Write payload as indented UTF-8 JSON followed by newline to stream.

    stream defaults to sys.stdout. ensure_ascii=False preserves Turkish and
    other non-ASCII codepoints as-is. Tests inject BytesIO+TextIOWrapper to
    capture bytes without subprocess.
    """
    out = stream if stream is not None else sys.stdout
    out.write(json.dumps(payload, ensure_ascii=False, indent=2))
    out.write("\n")


def dump_json_to_stdout(payload: dict[str, Any]) -> None:
    """Convenience wrapper: dump_json() to sys.stdout."""
    dump_json(payload, stream=None)
