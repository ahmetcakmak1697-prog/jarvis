"""C1.4 VectorMemory output contract tests."""

from __future__ import annotations

from tools.vector_memory import VectorMemory


class FakeCollection:
    def count(self):
        return 2

    def query(self, query_texts, n_results):
        return {
            "ids": [["c_good", "c_far"]],
            "documents": [["USER: test\nJARVIS: cevap", "USER: uzak\nJARVIS: uzak cevap"]],
            "metadatas": [[
                {
                    "user_msg": "test user",
                    "jarvis_msg": "test jarvis",
                    "ts": "2026-06-02T21:00:00",
                    "memory_action": "keep_long_term",
                    "memory_type": "semantic",
                    "storage_target": "vector",
                    "sensitivity": "normal",
                },
                {
                    "user_msg": "far user",
                    "jarvis_msg": "far jarvis",
                    "ts": "2026-06-02T21:00:01",
                    "memory_action": "keep_long_term",
                },
            ]],
            "distances": [[0.20, 0.90]],
        }


def _fake_vm():
    vm = object.__new__(VectorMemory)
    vm.col = FakeCollection()
    return vm


def test_find_similar_returns_metadata_id_similarity_and_document():
    vm = _fake_vm()

    results = vm.find_similar("test", n=2, threshold=0.7)

    assert len(results) == 1
    item = results[0]

    assert item["id"] == "c_good"
    assert item["distance"] == 0.20
    assert item["similarity"] == 0.80
    assert item["metadata"]["memory_action"] == "keep_long_term"
    assert item["metadata"]["memory_type"] == "semantic"
    assert item["metadata"]["storage_target"] == "vector"
    assert item["metadata"]["sensitivity"] == "normal"
    assert item["document"] == "USER: test\nJARVIS: cevap"
    assert item["user_msg"] == "test user"
    assert item["jarvis_msg"] == "test jarvis"


def test_find_similar_returns_empty_when_collection_empty():
    class EmptyCollection:
        def count(self):
            return 0

    vm = object.__new__(VectorMemory)
    vm.col = EmptyCollection()

    assert vm.find_similar("test") == []


def test_find_similar_handles_missing_metadata_safely():
    class MissingMetadataCollection:
        def count(self):
            return 1

        def query(self, query_texts, n_results):
            return {
                "ids": [["c_missing"]],
                "documents": [["USER: missing"]],
                "metadatas": [[None]],
                "distances": [[0.10]],
            }

    vm = object.__new__(VectorMemory)
    vm.col = MissingMetadataCollection()

    results = vm.find_similar("test", n=1, threshold=0.7)

    assert len(results) == 1
    assert results[0]["id"] == "c_missing"
    assert results[0]["metadata"] == {}
    assert results[0]["similarity"] == 0.90
