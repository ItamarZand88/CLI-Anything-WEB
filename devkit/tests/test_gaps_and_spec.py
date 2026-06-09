import json

from cli_web_devkit.gaps import analyze
from cli_web_devkit.paths import repo_root
from cli_web_devkit.spec import SPEC_VERSION, validate_file, validate_spec

ROOT = repo_root()


# ── gaps ────────────────────────────────────────────────────────────────────


def _make_app(tmp_path):
    pkg = tmp_path / "demo/agent-harness/cli_web/demo"
    (pkg / "core").mkdir(parents=True)
    (pkg / "commands").mkdir()
    (pkg / "core/client.py").write_text(
        "class DemoClient:\n"
        "    def _request(self):\n        pass\n"
        "    def list_items(self):\n        pass\n"
        "    def get_item(self, item_id):\n        pass\n"
        "    def orphan_method(self):\n        pass\n"
        "    def close(self):\n        pass\n"
    )
    (pkg / "commands/items.py").write_text(
        "import click\n\n"
        "@click.group()\n"
        "def items():\n    pass\n\n"
        "@items.command('list')\n"
        "def items_list():\n    client.list_items()\n\n"
        "@items.command('get')\n"
        "def items_get():\n    client.get_item(1)\n"
    )
    capture = tmp_path / "demo/traffic-capture"
    capture.mkdir(parents=True)
    (capture / "traffic-analysis.json").write_text(
        json.dumps(
            {
                "endpoints": [
                    {"method": "GET", "path": "/api/list_items"},
                    {"method": "GET", "path": "/api/never_implemented"},
                ]
            }
        )
    )
    return tmp_path


def test_gap_report_detects_all_three_layers(tmp_path):
    report = analyze(_make_app(tmp_path), "demo")
    assert report.client_methods == ["get_item", "list_items", "orphan_method"]
    assert report.commands == ["get", "list"]
    assert report.unexposed_methods == ["orphan_method"]
    assert report.unimplemented_endpoints == ["GET /api/never_implemented"]


def test_gap_report_real_cli_parses():
    """The analyzer must run cleanly against a real fleet CLI."""
    report = analyze(ROOT, "hackernews")
    assert len(report.client_methods) >= 5
    assert len(report.commands) >= 5


# ── api-spec ────────────────────────────────────────────────────────────────


def _valid_spec():
    return {
        "spec_version": SPEC_VERSION,
        "app": "demo",
        "protocol": "rest",
        "auth": {"type": "none"},
        "endpoints": [
            {
                "id": "list_items",
                "method": "GET",
                "url": "https://api.demo.example/items",
                "params": {},
                "evidence": "raw-traffic.json#3",
            }
        ],
        "commands": [{"name": "items list", "endpoint": "list_items"}],
    }


def test_valid_spec_passes():
    assert validate_spec(_valid_spec()) == []


def test_spec_requires_evidence():
    spec = _valid_spec()
    del spec["endpoints"][0]["evidence"]
    problems = validate_spec(spec)
    assert any("evidence" in p and "never invent" in p for p in problems)


def test_spec_rejects_unknown_endpoint_reference():
    spec = _valid_spec()
    spec["commands"][0]["endpoint"] = "nope"
    assert any("unknown endpoint" in p for p in validate_spec(spec))


def test_spec_rejects_duplicate_ids_and_bad_method():
    spec = _valid_spec()
    spec["endpoints"].append(dict(spec["endpoints"][0], method="FETCH"))
    problems = validate_spec(spec)
    assert any("duplicate id" in p for p in problems)
    assert any("invalid method" in p for p in problems)


def test_spec_validate_file(tmp_path):
    path = tmp_path / "api-spec.json"
    path.write_text(json.dumps(_valid_spec()))
    assert validate_file(path) == []
    path.write_text("not json")
    assert any("unreadable" in p for p in validate_file(path))
