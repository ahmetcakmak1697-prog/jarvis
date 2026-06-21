"""Governance test import bridge.

This file lives under tests/ and adds the repo scripts/ directory to sys.path.
"""
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
