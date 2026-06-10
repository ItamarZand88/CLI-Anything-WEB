"""Fleet MCP contract: every CLI serves its commands as MCP tools.

``cli-web-<app> mcp-serve`` must complete the MCP stdio handshake and list
at least one tool derived from the Click command tree. Offline — no network.
"""

from __future__ import annotations

import json
import subprocess

import pytest
from cli_web_core.testing import resolve_cli
from cli_web_devkit.paths import repo_root
from cli_web_devkit.registry import Registry

ROOT = repo_root()
REGISTRY = Registry.load(ROOT / "registry.json")

pytestmark = pytest.mark.contract

_HANDSHAKE = (
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
    '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
    '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
)


@pytest.mark.parametrize("entry", [pytest.param(e, id=e.name) for e in REGISTRY.clis])
def test_mcp_serve_handshake(entry):
    cmd = resolve_cli(entry.name)
    proc = subprocess.run(
        [*cmd, "mcp-serve"],
        input=_HANDSHAKE,
        capture_output=True,
        text=True,
        timeout=60,
    )
    lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    assert len(lines) >= 2, (
        f"expected 2 responses, got: {proc.stdout[:200]!r} / {proc.stderr[:200]!r}"
    )

    init, tools = lines[0], lines[1]
    assert init["id"] == 1 and init["result"]["serverInfo"]["name"] == entry.name
    assert "tools" in init["result"]["capabilities"]

    tool_list = tools["result"]["tools"]
    assert len(tool_list) >= 1, f"{entry.name}: no MCP tools derived"
    for tool in tool_list:
        assert tool["name"] != "mcp_serve"
        assert tool["inputSchema"]["type"] == "object"
        # json flag is forced by the adapter, never exposed
        assert "json_mode" not in tool["inputSchema"]["properties"]


# Drive a real tools/call: every CLI registers the offline `doctor` command,
# so calling it exercises the full subprocess-per-call path end to end without
# touching the network. id=2 calls doctor; id=3 calls a bogus tool.
_TOOLS_CALL = (
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
    '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
    '{"jsonrpc":"2.0","id":2,"method":"tools/call",'
    '"params":{"name":"doctor","arguments":{}}}\n'
    '{"jsonrpc":"2.0","id":3,"method":"tools/call",'
    '"params":{"name":"no_such_tool_xyz","arguments":{}}}\n'
)


@pytest.mark.parametrize("entry", [pytest.param(e, id=e.name) for e in REGISTRY.clis])
def test_mcp_tools_call_spawns_subprocess(entry):
    cmd = resolve_cli(entry.name)
    proc = subprocess.run(
        [*cmd, "mcp-serve"],
        input=_TOOLS_CALL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    by_id = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        msg = json.loads(line)
        if msg.get("id") is not None:
            by_id[msg["id"]] = msg

    # The `doctor` tool ran (as a fresh subprocess) and returned its --json envelope.
    assert 2 in by_id, (
        f"{entry.name}: no doctor response: {proc.stdout[:300]!r} / {proc.stderr[:300]!r}"
    )
    result = by_id[2]["result"]
    assert "content" in result and result["content"][0]["type"] == "text"
    payload = json.loads(result["content"][0]["text"])
    assert "data" in payload and "checks" in payload["data"], f"{entry.name}: not a doctor envelope"

    # An unknown tool is a JSON-RPC error, not a crash.
    assert 3 in by_id and by_id[3]["error"]["code"] == -32602
