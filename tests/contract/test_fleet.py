"""Fleet-wide contract tests.

Every CLI in registry.json must honor the externally-observable contract
from HARNESS.md, regardless of target site, protocol, or auth state:

- the entry point installs and runs
- ``--help`` and ``--version`` work
- the bare command starts the REPL and ``exit`` leaves it cleanly
- output contains no raw protocol leaks

These tests require the CLIs to be installed (``pip install -e <dir>``);
they make no network calls and need no credentials.

Run: ``pytest tests/contract -m contract``
"""

from __future__ import annotations

import pytest
from cli_web_core.testing import (
    assert_help_works,
    assert_no_protocol_leaks,
    assert_repl_starts_and_exits,
    assert_version_works,
    resolve_cli,
)
from cli_web_devkit.paths import repo_root
from cli_web_devkit.registry import Registry

ROOT = repo_root()
REGISTRY = Registry.load(ROOT / "registry.json")

pytestmark = pytest.mark.contract


def _params():
    return [pytest.param(entry, id=entry.name) for entry in REGISTRY.clis]


@pytest.fixture(scope="module")
def cli_cmds():
    return {entry.name: resolve_cli(entry.name) for entry in REGISTRY.clis}


@pytest.mark.parametrize("entry", _params())
def test_help_contract(entry, cli_cmds):
    out = assert_help_works(cli_cmds[entry.name])
    assert_no_protocol_leaks(out)


@pytest.mark.parametrize("entry", _params())
def test_version_contract(entry, cli_cmds):
    assert_version_works(cli_cmds[entry.name])


@pytest.mark.parametrize("entry", _params())
def test_repl_default_contract(entry, cli_cmds):
    """REPL is the default mode; piping `exit` must terminate cleanly."""
    out = assert_repl_starts_and_exits(cli_cmds[entry.name])
    assert_no_protocol_leaks(out)


@pytest.mark.parametrize("entry", _params())
def test_registered_command_groups_in_help(entry, cli_cmds):
    """Every top-level command group in registry.json appears in --help."""
    help_text = assert_help_works(cli_cmds[entry.name])
    groups = {c.split()[0] for c in entry.commands}
    missing = [g for g in sorted(groups) if g not in help_text]
    assert not missing, f"{entry.name}: registry commands missing from --help: {missing}"
