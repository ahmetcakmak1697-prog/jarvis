"""C1.6 Telegram memory status command tests."""

from __future__ import annotations

from tools.telegram_agent import cmd_memory_status


def test_cmd_memory_status_output_shape():
    text = cmd_memory_status()

    assert "C1 Hafiza Sistem Durumu" in text
    assert "Vector memory:" in text
    assert "Candidate total:" in text
    assert "Pending:" in text
    assert "Stored:" in text
    assert "Rejected:" in text
    assert "Deferred:" in text
    assert "Expired:" in text
    assert "Moduller:" in text
    assert "MemoryPolicy" in text
    assert "MemorySchemaMapper" in text
    assert "MemoryRetrievalPolicy" in text
    assert "MemoryCandidateQueue" in text
    assert "Komutlar:" in text


def test_cmd_memory_status_mentions_memory_commands():
    text = cmd_memory_status()

    assert "/mem_candidates" in text
    assert "/mem_expire" in text
    assert "/mem_approve <id>" in text
