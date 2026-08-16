import json

import click
from cli_web_core.json_group import JsonGroup
from click.testing import CliRunner


@click.group(cls=JsonGroup)
@click.option("--json", "json_mode", is_flag=True)
def cli(json_mode: bool) -> None:
    """Test CLI."""


@cli.command()
@click.argument("value")
def show(value: str) -> None:
    click.echo(value)


def test_json_usage_error_is_machine_readable() -> None:
    result = CliRunner().invoke(cli, ["--json", "missing"])
    assert result.exit_code == 2
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["code"] == "USAGE_ERROR"
    assert "No such command" in payload["message"]


def test_nested_missing_argument_is_machine_readable() -> None:
    result = CliRunner().invoke(cli, ["--json", "show"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["code"] == "USAGE_ERROR"
    assert "Missing argument" in payload["message"]


def test_plain_usage_error_keeps_click_help() -> None:
    result = CliRunner().invoke(cli, ["missing"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "No such command" in result.stderr


def test_success_path_is_unchanged() -> None:
    result = CliRunner().invoke(cli, ["show", "ok"])
    assert result.exit_code == 0
    assert result.stdout == "ok\n"
