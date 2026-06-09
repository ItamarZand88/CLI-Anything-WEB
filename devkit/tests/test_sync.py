import json

from cli_web_devkit.paths import repo_root
from cli_web_devkit.registry import Registry
from cli_web_devkit.sync import MANIFEST_NAME, SHARED_FILES, drift, load_manifest, resync

ROOT = repo_root()


def _make_fleet(tmp_path, vendored_content: bytes | None, with_override: bool = False):
    """Build a minimal repo: canon files + one registered CLI."""
    pkg = tmp_path / "demo/agent-harness/cli_web/demo"
    (pkg / "utils").mkdir(parents=True)
    for canon_rel, vendored_rel in SHARED_FILES.items():
        canon = tmp_path / canon_rel
        canon.parent.mkdir(parents=True, exist_ok=True)
        canon.write_bytes(b"CANONICAL CONTENT v2\n")
        # All vendored copies except repl_skin start in sync; repl_skin
        # content is controlled by the test.
        if vendored_rel != "utils/repl_skin.py":
            target = pkg / vendored_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"CANONICAL CONTENT v2\n")
    if vendored_content is not None:
        (pkg / "utils/repl_skin.py").write_bytes(vendored_content)

    (tmp_path / "registry.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "clis": [
                    {
                        "name": "cli-web-demo",
                        "website": "demo.example",
                        "protocol": "REST",
                        "auth": "none",
                        "directory": "demo/agent-harness",
                        "namespace": "cli_web.demo",
                        "commands": ["x"],
                        "install": "pip install -e demo/agent-harness",
                    }
                ],
            }
        )
    )
    if with_override:
        (tmp_path / "demo/agent-harness" / MANIFEST_NAME).write_text(
            json.dumps(
                {
                    "manifest_version": 1,
                    "cli": "cli-web-demo",
                    "shared_files": {},
                    "overrides": [{"file": "utils/repl_skin.py", "reason": "custom prompt"}],
                }
            )
        )
    return tmp_path


def test_drift_detects_divergence(tmp_path):
    _make_fleet(tmp_path, b"OLD STALE COPY\n")
    statuses = {(i.cli, i.file): i.status for i in drift(tmp_path) if i.cli == "cli-web-demo"}
    assert statuses[("cli-web-demo", "utils/repl_skin.py")] == "drifted"


def test_drift_detects_missing(tmp_path):
    _make_fleet(tmp_path, None)
    statuses = [i.status for i in drift(tmp_path) if i.cli == "cli-web-demo"]
    assert "missing" in statuses


def test_drift_respects_overrides(tmp_path):
    _make_fleet(tmp_path, b"INTENTIONALLY DIFFERENT\n", with_override=True)
    items = {i.file: i for i in drift(tmp_path) if i.cli == "cli-web-demo"}
    assert items["utils/repl_skin.py"].status == "override"
    assert "custom prompt" in items["utils/repl_skin.py"].detail


def test_resync_fixes_drift_and_writes_manifest(tmp_path):
    root = _make_fleet(tmp_path, b"OLD STALE COPY\n")
    changed = resync(root)
    assert "demo/agent-harness/cli_web/demo/utils/repl_skin.py" in changed

    vendored = root / "demo/agent-harness/cli_web/demo/utils/repl_skin.py"
    assert vendored.read_bytes() == b"CANONICAL CONTENT v2\n"

    reg = Registry.load(root / "registry.json")
    manifest = load_manifest(root, reg.entry("cli-web-demo"))
    rec = manifest["shared_files"]["utils/repl_skin.py"]
    assert rec["source"] == next(iter(SHARED_FILES))
    assert len(rec["sha256"]) == 64

    # After resync, drift is clean for the CLI
    assert all(i.status == "ok" for i in drift(root) if i.cli == "cli-web-demo")


def test_resync_skips_overridden_files(tmp_path):
    root = _make_fleet(tmp_path, b"INTENTIONALLY DIFFERENT\n", with_override=True)
    resync(root)
    vendored = root / "demo/agent-harness/cli_web/demo/utils/repl_skin.py"
    assert vendored.read_bytes() == b"INTENTIONALLY DIFFERENT\n"


def test_real_fleet_has_no_unexplained_drift():
    """The actual repo must be in sync (run `cli-web-devkit resync` if this fails)."""
    bad = [i for i in drift(ROOT) if i.status in ("drifted", "missing")]
    assert not bad, f"fleet drift detected: {[(i.cli, i.file, i.status) for i in bad]}"
