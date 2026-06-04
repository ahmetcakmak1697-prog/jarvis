"""C3 reporting smoke suite.

Runs C3 reporting tests without requiring pytest.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


TEST_MODULES = [
    "tests/test_c3_1_reporting_state.py",
    "tests/test_c3_1_structured_output_guard.py",
    "tests/test_a6_mini_redaction_guard.py",
]


def _load_module(path: Path):
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module spec olusturulamadi: {path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_test(func) -> None:
    sig = inspect.signature(func)

    if not sig.parameters:
        func()
        return

    with tempfile.TemporaryDirectory() as tmp:
        kwargs = {}
        for name in sig.parameters:
            if name == "tmp_path":
                kwargs[name] = Path(tmp)
            else:
                raise RuntimeError(f"desteklenmeyen test fixture: {name}")
        func(**kwargs)


def _run_module(path: Path) -> int:
    mod = _load_module(path)

    tests = [
        name for name in dir(mod)
        if name.startswith("test_") and callable(getattr(mod, name))
    ]

    if not tests:
        raise RuntimeError(f"test fonksiyonu bulunamadi: {path}")

    for name in tests:
        _run_test(getattr(mod, name))
        print(f"OK: {path.name}::{name}")

    return len(tests)


def main() -> None:
    print("JARVIS C3 REPORTING SMOKE SUITE")

    total = 0
    for rel in TEST_MODULES:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"FAIL: test dosyasi yok: {rel}")

        total += _run_module(path)

    print(f"\nC3 reporting smoke OK: {total} tests")


if __name__ == "__main__":
    main()
