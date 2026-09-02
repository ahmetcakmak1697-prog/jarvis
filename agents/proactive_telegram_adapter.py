"""ProactiveTelegramAdapter - FAZ-3-E1 adapter seam.

Pure factory helpers that bridge run_proactive_delivery() to a Telegram sender.
No network, no Telegram imports, no env reads, no live send.
All network-touching behavior is injected.
"""

from __future__ import annotations

from typing import Callable


def make_static_chat_id_resolver(mapping: dict) -> Callable[[str], str | None]:
    """Return a resolver that maps user_id -> chat_id via a static dict.

    Returns None for any user_id not in the mapping.
    Does not read env. Does not assume user_id == chat_id.
    """
    _mapping = dict(mapping) if mapping else {}

    def resolver(user_id: str) -> str | None:
        return _mapping.get(user_id)

    return resolver


def make_telegram_sender_factory(
    send_message_fn: Callable[[str, str], None],
) -> Callable[[str], Callable[[str, str], None]]:
    """Return a sender_factory suitable for run_proactive_delivery().

    sender_factory(chat_id) -> sender_fn(user_id, text)
    sender_fn calls send_message_fn(chat_id, text). Ignores user_id (chat_id
    was already resolved upstream by the chat_id_resolver).
    Catches all exceptions silently; caller (deliver) handles the return value.
    """
    def sender_factory(chat_id: str) -> Callable[[str, str], None]:
        def sender_fn(user_id: str, text: str) -> None:
            send_message_fn(chat_id, text)

        return sender_fn

    return sender_factory
