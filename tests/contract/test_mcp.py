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
