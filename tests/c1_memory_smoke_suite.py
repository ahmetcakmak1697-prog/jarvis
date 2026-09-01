"""C1 memory smoke suite.

Runs C1 memory test modules without requiring pytest.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_MODULES = [
    "tests/test_c1_1_memory_schema.py",
    "tests/test_c1_2_conversation_candidate_queue.py",
    "tests/test_c1_2_telegram_memory_display.py",
    "tests/test_c1_3_memory_candidate_expiry.py",
    "tests/test_c1_3_telegram_memory_expire.py",
    "tests/test_c1_4_memory_retrieval_policy.py",
    "tests/test_c1_4_jarvis_brain_retrieval_integration.py",
    "tests/test_c1_4_vector_memory_output.py",
    "tests/test_c1_5_memory_candidate_writer_route_guard.py",
    "tests/test_c1_6_telegram_memory_status.py",
]


def _load_module(path: Path):
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module spec olusturulamadi: {path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_module(path: Path) -> int:
    mod = _load_module(path)

    tests = [
        name for name in dir(mod)
        if name.startswith("test_") and callable(getattr(mod, name))
    ]

    if not tests:
        raise RuntimeError(f"test fonksiyonu bulunamadi: {path}")

    for name in tests:
        getattr(mod, name)()
        print(f"OK: {path.name}::{name}")

    return len(tests)


def main() -> None:
    print("JARVIS C1 MEMORY SMOKE SUITE")

    total = 0
    for rel in TEST_MODULES:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"FAIL: test dosyasi yok: {rel}")

        total += _run_module(path)

    print(f"\nC1 memory smoke OK: {total} tests")


if __name__ == "__main__":
    main()
