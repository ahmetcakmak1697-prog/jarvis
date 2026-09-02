"""C2 project intelligence smoke suite.

Runs C2 project intelligence tests without requiring pytest.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


TEST_MODULES = [
    "tests/test_c2_1_project_state.py",
    "tests/test_c2_1_telegram_project_state.py",
    "tests/test_c2_2_project_summarizer.py",
    "tests/test_c2_3_roadmap_detector.py",
    "tests/test_c2_4_next_action_planner.py",
    "tests/test_c2_5_telegram_project_intel.py",
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
    print("JARVIS C2 PROJECT SMOKE SUITE")

    total = 0
    for rel in TEST_MODULES:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"FAIL: test dosyasi yok: {rel}")

        total += _run_module(path)

    print(f"\nC2 project smoke OK: {total} tests")


if __name__ == "__main__":
    main()
