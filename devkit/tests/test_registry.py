import json

import pytest
from cli_web_devkit.matrix import build_matrix, render_matrix
from cli_web_devkit.paths import repo_root
from cli_web_devkit.registry import Registry, RegistryEntry, validate

ROOT = repo_root()


def _entry(**overrides):
    base = {
        "name": "cli-web-demo",
        "website": "demo.example",
        "protocol": "REST",
        "auth": "none",
        "directory": "demo/agent-harness",
        "namespace": "cli_web.demo",
        "commands": ["things list"],
        "install": "pip install -e demo/agent-harness",
    }
    base.update(overrides)
    return base


def test_real_registry_is_valid():
    assert validate(ROOT) == []


def test_real_registry_loads_all_entries():
    reg = Registry.load(ROOT / "registry.json")
    names = [e.name for e in reg.clis]
    assert len(names) == len(set(names)), "duplicate CLI names"
    assert "cli-web-hackernews" in names
    assert "cli-web-youtube" in names


def test_entry_helpers():
    e = RegistryEntry.from_dict(_entry())
    assert e.package == "demo"
    assert e.app_dir == "demo"


def test_entry_missing_field_raises():
    bad = _entry()
    del bad["namespace"]
    with pytest.raises(ValueError, match="missing fields"):
        RegistryEntry.from_dict(bad)


def test_registry_lookup():
    reg = Registry.load(ROOT / "registry.json")
    assert reg.entry("cli-web-gh-trending").package == "gh_trending"
    assert reg.entry("gh-trending").name == "cli-web-gh-trending"
    with pytest.raises(KeyError):
        reg.entry("nope")


def test_validate_detects_missing_directory(tmp_path):
    (tmp_path / "registry.json").write_text(json.dumps({"version": "1.0.0", "clis": [_entry()]}))
    problems = validate(tmp_path)
    assert any("does not exist" in p for p in problems)


def test_validate_detects_unregistered_cli(tmp_path):
    (tmp_path / "registry.json").write_text(json.dumps({"version": "1.0.0", "clis": []}))
    (tmp_path / "rogue" / "agent-harness").mkdir(parents=True)
    problems = validate(tmp_path)
    assert any("unregistered CLI: rogue" in p for p in problems)


def test_matrix_matches_registry():
    matrix = build_matrix(ROOT)
    reg = Registry.load(ROOT / "registry.json")
    assert len(matrix) == len(reg.clis)
    sample = {m["name"]: m for m in matrix}
    assert sample["gh-trending"] == {
        "name": "gh-trending",
        "dir": "gh-trending/agent-harness",
        "pkg": "gh_trending",
    }


def test_render_matrix_is_single_line_json():
    rendered = render_matrix(ROOT)
    assert "\n" not in rendered
    assert isinstance(json.loads(rendered), list)
