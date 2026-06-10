import json
import sys

import click
import pytest
from cli_web_core.mcp_server import McpServer, register_mcp_command


@pytest.fixture()
def demo_cli():
    @click.group()
    def cli():
        """Demo CLI."""

    @cli.group("things")
    def things():
        """Thing operations."""

    @things.command("list")
    @click.option("--limit", type=int, default=5, help="Max results")
    @click.option("--json", "json_mode", is_flag=True)
    def things_list(limit, json_mode):
        """List things."""
        payload = {"success": True, "data": [{"id": i} for i in range(limit)]}
        click.echo(json.dumps(payload) if json_mode else f"{limit} things")

    @things.command("get")
    @click.argument("thing_id")
    @click.option("--json", "json_mode", is_flag=True)
    def things_get(thing_id, json_mode):
        """Get one thing."""
        click.echo(json.dumps({"success": True, "data": {"id": thing_id}}))

    @cli.command("boom")
    def boom():
        """Always fails."""
        raise click.ClickException("kaput")

    @cli.command("search")
    @click.argument("query", nargs=-1, required=True)
    @click.option("--tag", multiple=True, help="Filter tag (repeatable)")
    @click.option("--json", "json_mode", is_flag=True)
    def search(query, tag, json_mode):
        """Search things."""
        click.echo(json.dumps({"success": True, "data": {"query": list(query), "tags": list(tag)}}))

    register_mcp_command(cli, app_name="demo", version="9.9.9")
    return cli


@pytest.fixture()
def server(demo_cli):
    """Server whose tool calls run the in-memory demo CLI via CliRunner.

    Production uses a fresh subprocess per call (see the subprocess tests
    below); the in-memory executor lets these protocol/argv/shaping tests
    exercise the demo group without an installed binary.
    """
    from click.testing import CliRunner

    def executor(argv):
        result = CliRunner().invoke(demo_cli, argv, catch_exceptions=True)
        text = result.output.strip() or (str(result.exception) if result.exception else "")
        return (text, result.exit_code != 0)

    return McpServer(demo_cli, app_name="demo", version="9.9.9", executor=executor)


def test_initialize_handshake(server):
    resp = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert resp["result"]["protocolVersion"]
    assert resp["result"]["serverInfo"]["name"] == "cli-web-demo"
    assert resp["result"]["serverInfo"]["version"] == "9.9.9"
    assert "tools" in resp["result"]["capabilities"]


def test_notifications_are_silent(server):
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_tools_list_derives_from_click_tree(server):
    resp = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = {t["name"]: t for t in resp["result"]["tools"]}
    assert set(tools) == {"things_list", "things_get", "boom", "search"}

    list_tool = tools["things_list"]
    assert list_tool["description"] == "List things."
    assert list_tool["inputSchema"]["properties"]["limit"] == {
        "type": "integer",
        "description": "Max results",
    }
    # --json is forced by the adapter, not exposed as a tool parameter
    assert "json_mode" not in list_tool["inputSchema"]["properties"]

    get_tool = tools["things_get"]
    assert get_tool["inputSchema"]["required"] == ["thing_id"]


def test_mcp_serve_not_exposed_as_tool(server):
    resp = server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
    assert all(t["name"] != "mcp_serve" for t in resp["result"]["tools"])


def test_tools_call_runs_command_with_json(server):
    resp = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "things_list", "arguments": {"limit": 2}},
        }
    )
    result = resp["result"]
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload == {"success": True, "data": [{"id": 0}, {"id": 1}]}


def test_tools_call_positional_argument(server):
    resp = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "things_get", "arguments": {"thing_id": "abc"}},
        }
    )
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["data"]["id"] == "abc"


def test_tools_call_failure_marks_error(server):
    resp = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "boom", "arguments": {}},
        }
    )
    assert resp["result"]["isError"] is True
    assert "kaput" in resp["result"]["content"][0]["text"]


def test_unknown_tool_and_method(server):
    resp = server.handle(
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "nope"}}
    )
    assert resp["error"]["code"] == -32602
    resp = server.handle({"jsonrpc": "2.0", "id": 8, "method": "bogus/method"})
    assert resp["error"]["code"] == -32601


def test_register_adds_command(demo_cli):
    assert "mcp-serve" in demo_cli.commands


def test_multi_value_params_schema(server):
    resp = server.handle({"jsonrpc": "2.0", "id": 8, "method": "tools/list"})
    search = next(t for t in resp["result"]["tools"] if t["name"] == "search")
    props = search["inputSchema"]["properties"]
    assert props["query"] == {"type": "array", "items": {"type": "string"}}
    assert props["tag"]["type"] == "array"


def test_multi_value_params_call(server):
    resp = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": ["python", "tutorial"], "tag": ["a", "b"]},
            },
        }
    )
    assert resp["result"]["isError"] is False
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["data"]["query"] == ["python", "tutorial"]
    assert payload["data"]["tags"] == ["a", "b"]


# ── subprocess-per-call execution (the production default) ───────────────────


def _call(server, name, arguments=None):
    return server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
    )


def test_default_execution_spawns_a_subprocess(demo_cli, monkeypatch):
    """With no executor injected, each tool call shells out to a fresh process."""
    import subprocess

    seen = {}

    class _Proc:
        stdout = '{"success": true, "data": []}'
        stderr = ""
        returncode = 0

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return _Proc()

    monkeypatch.setattr("shutil.which", lambda _name: None)  # force python -m
    monkeypatch.setattr(subprocess, "run", fake_run)

    server = McpServer(demo_cli, app_name="demo", pkg="demo_pkg")
    resp = _call(server, "things_list", {"limit": 2})

    # The whole command line is: python -m cli_web.demo_pkg things list --limit 2 --json
    assert seen["command"][:3] == [sys.executable, "-m", "cli_web.demo_pkg"]
    assert seen["command"][3:5] == ["things", "list"]
    assert "--json" in seen["command"]
    assert seen["kwargs"]["timeout"] == server.timeout
    assert resp["result"]["isError"] is False
    assert json.loads(resp["result"]["content"][0]["text"]) == {"success": True, "data": []}


def test_subprocess_prefers_installed_binary(demo_cli, monkeypatch):
    import subprocess

    seen = {}

    class _Proc:
        stdout = "{}"
        stderr = ""
        returncode = 0

    monkeypatch.setattr("shutil.which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(
        subprocess, "run", lambda command, **kw: seen.update(command=command) or _Proc()
    )

    McpServer(demo_cli, app_name="demo").handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "boom"}}
    )
    assert seen["command"][0] == "/usr/local/bin/cli-web-demo"
    assert "-m" not in seen["command"]


def test_subprocess_nonzero_exit_is_error_and_prefers_stderr(demo_cli, monkeypatch):
    import subprocess

    class _Proc:
        stdout = ""
        stderr = "Usage: ... \nError: no such option"
        returncode = 2

    monkeypatch.setattr("shutil.which", lambda _name: "/bin/cli-web-demo")
    monkeypatch.setattr(subprocess, "run", lambda command, **kw: _Proc())

    resp = _call(McpServer(demo_cli, app_name="demo"), "things_list")
    assert resp["result"]["isError"] is True
    assert "no such option" in resp["result"]["content"][0]["text"]


def test_subprocess_timeout_returns_error(demo_cli, monkeypatch):
    import subprocess

    def boom(command, **kwargs):
        raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs.get("timeout"))

    monkeypatch.setattr("shutil.which", lambda _name: "/bin/cli-web-demo")
    monkeypatch.setattr(subprocess, "run", boom)

    resp = _call(McpServer(demo_cli, app_name="demo", timeout=7.0), "things_list")
    assert resp["result"]["isError"] is True
    assert "timed out after 7.0s" in resp["result"]["content"][0]["text"]
