"""Telegram HTML formatter for Jarvis.

Design:
- Split RAW text before HTML formatting.
- Each chunk rendered as independent valid HTML.
- Never blind-split already-rendered HTML.
- All model/user text escaped.
"""
from __future__ import annotations

import html
from typing import Any

TELEGRAM_LIMIT = 4096
_SAFE_BODY_BUDGET = 3400

_SOURCE_LABELS = {
    "knowledge_card": "Hafiza",
    "memory": "Hafiza",
    "cache": "Onbellek",
    "ollama": "Ollama",
    "redacted_blocked": "Guvenlik",
    "external_blocked": "Limit",
    "ollama_error": "Hata",
}


def escape_html(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def split_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    text = str(text or "")
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut < int(limit * 0.5):
            cut = limit
        parts.append(remaining[:cut])
        remaining = remaining[cut:]
    if remaining:
        parts.append(remaining)
    return parts


def _source_label(result: dict) -> str:
    source = str(result.get("source") or "unknown")
    label = _SOURCE_LABELS.get(source, source)
    if source == "ollama" and result.get("level"):
        return f"Ollama {result['level']}"
    return label


def _header_html(result: dict) -> str:
    label = escape_html(_source_label(result))
    latency = result.get("latency_ms")
    if result.get("ok"):
        h = f"<b>{label}</b>"
    elif result.get("blocked"):
        h = f"<b>{label}</b>"
    else:
        h = f"<b>{label}</b>"
    if latency is not None:
        try:
            h += f" ({int(latency)}ms)"
        except Exception:
            pass
    return h


def _parse_blocks(text: str) -> list[tuple[str, str]]:
    """Parse raw text into ('text'|'code', content) blocks."""
    text = str(text or "")
    blocks: list[tuple[str, str]] = []
    pos = 0
    while True:
        start = text.find("```", pos)
        if start == -1:
            if pos < len(text):
                blocks.append(("text", text[pos:]))
            break
        if start > pos:
            blocks.append(("text", text[pos:start]))
        code_start = start + 3
        first_nl = text.find("\n", code_start)
        close = text.find("```", code_start)
        if close == -1:
            code = text[first_nl + 1:] if first_nl != -1 else text[code_start:]
            blocks.append(("code", code))
            break
        if first_nl != -1 and first_nl < close:
            code = text[first_nl + 1:close]
        else:
            code = text[code_start:close]
        blocks.append(("code", code))
        pos = close + 3
    if not blocks:
        blocks.append(("text", ""))
    return blocks


def _render_inline(text: str) -> str:
    pieces: list[str] = []
    pos = 0
    while True:
        start = text.find("`", pos)
        if start == -1:
            pieces.append(escape_html(text[pos:]))
            break
        end = text.find("`", start + 1)
        if end == -1:
            pieces.append(escape_html(text[pos:]))
            break
        pieces.append(escape_html(text[pos:start]))
        pieces.append("<code>" + escape_html(text[start+1:end]) + "</code>")
        pos = end + 1
    return "".join(pieces)


def _render_block(kind: str, content: str) -> str:
    if kind == "code":
        return "<pre>" + escape_html(content.strip("\n")) + "</pre>"
    return _render_inline(content)


def _chunk_raw(kind: str, content: str, budget: int) -> list[str]:
    content = str(content or "")
    if not content:
        return [""]
    chunks: list[str] = []
    remaining = content
    while remaining:
        lo, hi, best = 1, len(remaining), 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if len(_render_block(kind, remaining[:mid])) <= budget:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        nl = remaining.rfind("\n", 0, best)
        if nl >= max(1, int(best * 0.5)):
            best = nl + 1
        chunks.append(remaining[:best])
        remaining = remaining[best:]
    return chunks


def format_ask_messages(result: dict[str, Any], limit: int = TELEGRAM_LIMIT) -> list[str]:
    header = _header_html(result)
    body_budget = max(200, min(_SAFE_BODY_BUDGET, limit - len(header) - 2))
    messages: list[str] = []

    if result.get("ok"):
        answer = str(result.get("answer") or "Cevap bos dondu.")
        current = header

        for kind, content in _parse_blocks(answer):
            for raw in _chunk_raw(kind, content, body_budget):
                rendered = _render_block(kind, raw)
                sep = "\n\n" if current == header else "\n"
                candidate = current + sep + rendered
                if len(candidate) <= limit:
                    current = candidate
                else:
                    if current != header:
                        messages.append(current)
                    current = header + "\n\n" + rendered
                    if len(current) > limit:
                        messages.append(current[:limit])
                        current = header

        if current and current != header:
            messages.append(current)
        if not messages:
            messages.append(header + "\n\nCevap bos dondu.")
        return messages

    if result.get("blocked"):
        body = escape_html(result.get("answer") or "Engellendi.")
        return [header + "\n\n" + body]

    body = escape_html(result.get("error") or result.get("answer") or "Hata.")
    return [header + "\n\n" + body]


def format_ask_response(result: dict[str, Any]) -> str:
    return format_ask_messages(result)[0]
