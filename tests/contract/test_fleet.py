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

import importlib
from importlib.metadata import entry_points

import click
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


def _installed_command_paths(entry_name: str) -> set[str]:
    """Return the installed Click leaf commands, excluding fleet utilities."""
    ep = next(ep for ep in entry_points(group="console_scripts") if ep.name == entry_name)
    module = importlib.import_module(ep.module)
    root = next(
        (
            candidate
            for attr in ("cli", "main")
            if isinstance((candidate := getattr(module, attr, None)), click.Group)
        ),
        None,
    )
    if root is None:
        loaded = ep.load()
        assert isinstance(loaded, click.Group), f"{entry_name}: Click root group not found"
        root = loaded

    paths: set[str] = set()

    def walk(command: click.Command, path: list[str]) -> None:
        if isinstance(command, click.Group):
            context = click.Context(command)
            for name in command.list_commands(context):
                child = command.get_command(context, name)
                if child is not None:
                    walk(child, [*path, name])
        elif path:
            paths.add(" ".join(path))

    walk(root, [])
    return paths - {"doctor", "mcp-serve"}


@pytest.mark.parametrize("entry", _params())
def test_registry_lists_every_installed_command(entry):
    """The README and registry site command lists must match the installed CLI."""
    installed = _installed_command_paths(entry.name)
    registered = set(entry.commands)
    assert registered == installed, (
        f"{entry.name}: registry command drift; "
        f"missing={sorted(installed - registered)}, stale={sorted(registered - installed)}"
    )
