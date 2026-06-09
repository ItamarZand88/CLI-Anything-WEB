"""MCP server adapter — expose a cli-web-* Click CLI as MCP tools.

CANONICAL SOURCE: cli-web-core/cli_web_core/mcp_server.py
Vendored into every generated CLI at cli_web/<app>/utils/mcp_server.py by
`cli-web-devkit resync`. Do not edit vendored copies by hand.

Every cli-web-* command already speaks ``--json``, so the Click command
tree maps 1:1 onto MCP tools: tool names are ``group_subcommand``, input
schemas are derived from Click parameters, and calls run the command
in-process with ``--json`` forced, returning the JSON envelope as the tool
result. Transport: MCP stdio (newline-delimited JSON-RPC 2.0).

Usage (wired automatically into generated CLIs)::

    cli-web-<app> mcp-serve

Then point any MCP client at that command.
"""

from __future__ import annotations

import json
import sys
from typing import Any

PROTOCOL_VERSION = "2024-11-05"

_CLICK_TYPE_MAP = {
    "integer": "integer",
    "int": "integer",
    "float": "number",
    "boolean": "boolean",
    "bool": "boolean",
}


def _param_schema(param: Any) -> dict[str, Any]:
    type_name = getattr(param.type, "name", "text") or "text"
    json_type = _CLICK_TYPE_MAP.get(type_name.lower(), "string")
    schema: dict[str, Any] = {"type": json_type}
    help_text = getattr(param, "help", None)
    if help_text:
        schema["description"] = help_text
    choices = getattr(param.type, "choices", None)
    if choices:
        schema["enum"] = list(choices)
    return schema


def _iter_leaf_commands(
    group: Any, prefix: tuple[str, ...] = ()
) -> list[tuple[tuple[str, ...], Any]]:
    """Flatten a Click group into (path, command) leaves."""
    import click

    leaves: list[tuple[tuple[str, ...], Any]] = []
    for name in sorted(group.commands):
        cmd = group.commands[name]
        if getattr(cmd, "hidden", False) or name == "mcp-serve":
            continue
        path = (*prefix, name)
        if isinstance(cmd, click.Group):
            leaves.extend(_iter_leaf_commands(cmd, path))
        else:
            leaves.append((path, cmd))
    return leaves


def _is_json_flag(param: Any) -> bool:
    return "--json" in getattr(param, "opts", ()) or param.name in ("json_mode", "as_json")


def _tool_for(path: tuple[str, ...], cmd: Any) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for param in cmd.params:
        if _is_json_flag(param) or param.name == "help":
            continue
        properties[param.name] = _param_schema(param)
        if getattr(param, "required", False):
            required.append(param.name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return {
        "name": "_".join(path).replace("-", "_"),
        "description": (cmd.help or cmd.short_help or " ".join(path)).strip(),
        "inputSchema": schema,
    }


def _build_argv(
    path: tuple[str, ...], cmd: Any, arguments: dict[str, Any], json_flag: bool
) -> list[str]:
    """Translate MCP tool arguments back into a Click argv."""
    import click

    argv = list(path)
    for param in cmd.params:
        if _is_json_flag(param) or param.name not in arguments:
            continue
        value = arguments[param.name]
        if value is None:
            continue
        if isinstance(param, click.Argument):
            argv.append(str(value))
        elif getattr(param, "is_flag", False):
            if value:
                argv.append(param.opts[0])
        else:
            argv.extend([param.opts[0], str(value)])
    if json_flag:
        argv.append("--json")
    return argv


def _cmd_supports_json(cmd: Any) -> bool:
    return any(_is_json_flag(p) for p in cmd.params)


class McpServer:
    def __init__(self, cli: Any, app_name: str, version: str = "0.1.0"):
        self.cli = cli
        self.app_name = app_name
        self.version = version
        self._leaves: dict[str, tuple[tuple[str, ...], Any]] = {}
        for path, cmd in _iter_leaf_commands(cli):
            tool_name = "_".join(path).replace("-", "_")
            self._leaves[tool_name] = (path, cmd)

    # ── JSON-RPC handlers ────────────────────────────────────────────

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method", "")
        msg_id = message.get("id")
        if method == "initialize":
            return self._result(
                msg_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": f"cli-web-{self.app_name}",
                        "version": self.version,
                    },
                },
            )
        if method.startswith("notifications/"):
            return None
        if method == "tools/list":
            tools = [_tool_for(path, cmd) for path, cmd in self._leaves.values()]
            return self._result(msg_id, {"tools": tools})
        if method == "tools/call":
            return self._call_tool(msg_id, message.get("params") or {})
        if method == "ping":
            return self._result(msg_id, {})
        return self._error(msg_id, -32601, f"Method not found: {method}")

    def _call_tool(self, msg_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        if name not in self._leaves:
            return self._error(msg_id, -32602, f"Unknown tool: {name}")
        path, cmd = self._leaves[name]
        arguments = params.get("arguments") or {}
        argv = _build_argv(path, cmd, arguments, json_flag=_cmd_supports_json(cmd))

        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(self.cli, argv, catch_exceptions=True)
        text = result.output.strip() or (str(result.exception) if result.exception else "")
        return self._result(
            msg_id,
            {
                "content": [{"type": "text", "text": text}],
                "isError": result.exit_code != 0,
            },
        )

    @staticmethod
    def _result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    # ── stdio loop ───────────────────────────────────────────────────

    def serve_stdio(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                print(
                    json.dumps(self._error(None, -32700, "Parse error")),
                    flush=True,
                )
                continue
            response = self.handle(message)
            if response is not None:
                print(json.dumps(response), flush=True)


def register_mcp_command(cli: Any, app_name: str, version: str = "0.1.0") -> None:
    """Attach an ``mcp-serve`` command to a cli-web-* Click group."""
    import click

    @cli.command("mcp-serve", hidden=False)
    def mcp_serve() -> None:
        """Serve this CLI as an MCP server over stdio (newline JSON-RPC)."""
        McpServer(cli, app_name=app_name, version=version).serve_stdio()

    _ = click  # imported for parity with vendored runtime deps
