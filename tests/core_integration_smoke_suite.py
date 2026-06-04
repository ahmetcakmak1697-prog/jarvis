"""Core integration smoke suite.

Runs core integration tests without requiring pytest.
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
    "tests/test_c4_mini_internal_trace.py",
    "tests/test_h1_5_organ_contract.py",
    "tests/test_m0_world_model.py",
    "tests/test_m0_2_inventory_model.py",
    "tests/test_m0_3_world_inventory_linker.py",
    "tests/test_m0_4_project_workspace.py",
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
    print("JARVIS CORE INTEGRATION SMOKE SUITE")

    total = 0
    for rel in TEST_MODULES:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"FAIL: test dosyasi yok: {rel}")

        total += _run_module(path)

    print(f"\nCore integration smoke OK: {total} tests")


if __name__ == "__main__":
    main()
