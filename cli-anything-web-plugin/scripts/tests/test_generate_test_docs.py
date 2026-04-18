"""Tests for generate-test-docs.py — AST-based test plan extraction.

Exercises parse_test_file() against synthetic test files and drives the
full `plan` subcommand via subprocess to verify end-to-end output.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
GEN_DOCS = SCRIPTS_DIR / "generate-test-docs.py"


@pytest.fixture(scope="module")
def gen_docs_mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_test_docs", GEN_DOCS)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["generate_test_docs"] = mod
    spec.loader.exec_module(mod)
    return mod


# --- parse_test_file ---

def test_parse_extracts_top_level_test_functions(gen_docs_mod, tmp_path):
    src = tmp_path / "test_core.py"
    src.write_text(
        "def test_one():\n    pass\n\n"
        "def test_two():\n    pass\n\n"
        "def not_a_test():\n    pass\n"
    )
    result = gen_docs_mod.parse_test_file(src)
    # Module-level funcs become the first entry
    assert result, "expected at least one result"
    module_entry = result[0]
    assert "test_one" in module_entry["methods"]
    assert "test_two" in module_entry["methods"]
    assert "not_a_test" not in module_entry["methods"]


def test_parse_extracts_test_classes_with_methods(gen_docs_mod, tmp_path):
    src = tmp_path / "test_core.py"
    src.write_text(
        "class TestFoo:\n"
        "    def test_a(self): pass\n"
        "    def test_b(self): pass\n"
        "    def helper(self): pass\n"
        "\n"
        "class NotATest:\n"
        "    def test_ignored(self): pass\n"
    )
    result = gen_docs_mod.parse_test_file(src)
    classes = [r["class"] for r in result]
    assert "TestFoo" in classes
    assert "NotATest" not in classes

    foo = next(r for r in result if r["class"] == "TestFoo")
    assert foo["methods"] == ["test_a", "test_b"]


def test_parse_classifies_e2e_layer_by_filename(gen_docs_mod, tmp_path):
    src = tmp_path / "test_e2e.py"
    src.write_text("def test_live(): pass\n")
    result = gen_docs_mod.parse_test_file(src)
    assert result[0]["layer"] == "E2E (live)"


def test_parse_classifies_unit_layer_by_filename(gen_docs_mod, tmp_path):
    src = tmp_path / "test_core.py"
    src.write_text("def test_mocked(): pass\n")
    result = gen_docs_mod.parse_test_file(src)
    assert "Unit" in result[0]["layer"]


def test_parse_class_name_overrides_default_layer(gen_docs_mod, tmp_path):
    """TestSubprocessFoo in test_e2e.py should be classified as Subprocess,
    not E2E, because the class name takes priority."""
    src = tmp_path / "test_e2e.py"
    src.write_text(
        "class TestSubprocessFoo:\n"
        "    def test_spawn(self): pass\n"
    )
    result = gen_docs_mod.parse_test_file(src)
    classes = {r["class"]: r["layer"] for r in result}
    assert classes["TestSubprocessFoo"] == "Subprocess"


def test_parse_ignores_syntax_errors(gen_docs_mod, tmp_path):
    """Malformed .py file should return [] rather than crash."""
    src = tmp_path / "broken.py"
    src.write_text("def test_broken(\n")
    assert gen_docs_mod.parse_test_file(src) == []


def test_parse_skips_classes_with_no_test_methods(gen_docs_mod, tmp_path):
    src = tmp_path / "test_core.py"
    src.write_text(
        "class TestEmpty:\n    pass\n\n"
        "class TestReal:\n    def test_x(self): pass\n"
    )
    result = gen_docs_mod.parse_test_file(src)
    class_names = [r["class"] for r in result]
    assert "TestEmpty" not in class_names
    assert "TestReal" in class_names


def test_parse_handles_empty_file(gen_docs_mod, tmp_path):
    src = tmp_path / "empty.py"
    src.write_text("")
    assert gen_docs_mod.parse_test_file(src) == []


# --- generate_plan via subprocess ---

def test_plan_subcommand_generates_markdown(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_core.py").write_text(
        "class TestClient:\n    def test_fetch(self): pass\n"
    )
    result = subprocess.run(
        [
            sys.executable, str(GEN_DOCS), "plan",
            str(tests_dir), "--app-name", "myapp",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    # Plan subcommand writes TEST.md next to tests/ (under the harness root).
    # Locate it: either in tests_dir, its parent, or stdout.
    for candidate in (tests_dir / "TEST.md", tests_dir.parent / "TEST.md"):
        if candidate.exists():
            markdown = candidate.read_text()
            break
    else:
        markdown = result.stdout
    assert "myapp" in markdown
    assert "TestClient" in markdown or "test_fetch" in markdown


def test_plan_handles_empty_tests_dir(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    result = subprocess.run(
        [
            sys.executable, str(GEN_DOCS), "plan",
            str(tests_dir), "--app-name", "empty",
        ],
        capture_output=True, text=True,
    )
    # Should not crash; output may be empty / minimal
    assert result.returncode == 0, result.stderr


def test_rejects_nonexistent_tests_dir():
    result = subprocess.run(
        [
            sys.executable, str(GEN_DOCS), "plan",
            "/nonexistent/path/xyz", "--app-name", "x",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
