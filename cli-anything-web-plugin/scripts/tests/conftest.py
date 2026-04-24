"""Shared fixtures for plugin-script tests.

The scripts aren't a proper package (they use hyphenated filenames and are
invoked as CLI tools), so tests load them by absolute path via importlib.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent


def load_script(filename: str, module_name: str | None = None) -> ModuleType:
    """Load a hyphenated script file as an importable module.

    Args:
        filename: e.g. "scaffold-cli.py"
        module_name: optional override for sys.modules key
    """
    path = SCRIPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Script not found: {path}")
    name = module_name or filename.replace("-", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def scaffold_cli() -> ModuleType:
    return load_script("scaffold-cli.py", "scaffold_cli")


@pytest.fixture(scope="session")
def parse_trace() -> ModuleType:
    return load_script("parse-trace.py", "parse_trace")


@pytest.fixture(scope="session")
def analyze_traffic() -> ModuleType:
    return load_script("analyze-traffic.py", "analyze_traffic")
