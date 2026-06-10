"""Fleet doctor contract: every CLI can self-diagnose, offline."""

from __future__ import annotations

import json

import pytest
from cli_web_core.testing import resolve_cli, run_cli
from cli_web_devkit.paths import repo_root
from cli_web_devkit.registry import Registry

ROOT = repo_root()
REGISTRY = Registry.load(ROOT / "registry.json")

pytestmark = pytest.mark.contract


@pytest.mark.parametrize("entry", [pytest.param(e, id=e.name) for e in REGISTRY.clis])
def test_doctor_json_contract(entry):
    proc = run_cli(resolve_cli(entry.name), "doctor", "--json")
    payload = json.loads(proc.stdout)
    assert payload["success"] in (True, False)
    checks = {c["name"]: c for c in payload["data"]["checks"]}
    assert checks["python"]["status"] == "ok"
    assert "entry point" in checks
    # doctor must never hard-fail merely because auth isn't configured
    auth_warns = [c for c in payload["data"]["checks"] if c["status"] == "fail"]
    assert not auth_warns, f"{entry.name}: doctor fail-level checks: {auth_warns}"
