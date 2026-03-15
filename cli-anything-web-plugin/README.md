# Web-Harness — Agent-Native CLIs for Web Apps

**Build production-grade Python CLIs for closed-source web applications by capturing and analyzing their HTTP traffic.**

## How It Works

1. You point Web-Harness at a web app URL
2. Chrome DevTools MCP opens the app in your browser (with your login session)
3. Claude systematically exercises the app, capturing all API traffic
4. Claude analyzes the traffic, maps the API, and generates a complete CLI
5. You get `cli-web-<app>` on your PATH — ready for agents

## Quick Start

```bash
# Copy plugin to Claude Code plugins directory
cp -r /path/to/cli-anything-web-plugin ~/.claude/plugins/web-harness

# Reload plugins in Claude Code
/reload-plugins

# Verify installation
/help web-harness

# Generate a CLI for any web app
/web-harness https://monday.com
```

## Commands

| Command | Description |
|---------|-------------|
| `/web-harness <url>` | Full 7-phase pipeline — record, analyze, generate CLI |
| `/web-harness:record <url>` | Record traffic only (Phase 1) |
| `/web-harness:refine <path> [focus]` | Expand coverage of existing CLI |
| `/web-harness:test <path>` | Run tests and update TEST.md |
| `/web-harness:validate <path>` | Validate against CLI-ANYTHING-WEB.md standards |
| `/web-harness:list` | List all installed and generated `cli-web-*` CLIs |

## Prerequisites

- **Claude Code** with plugin support
- **Chrome DevTools MCP** (auto-configured by plugin via `.mcp.json`)
- **Python 3.10+**
- **Node.js** (for npx / Chrome DevTools MCP)

## Generated CLI Example

```bash
# Install
cd monday/agent-harness && pip install -e .

# Use
cli-web-monday --help
cli-web-monday auth login --email user@example.com
cli-web-monday boards list --json
cli-web-monday items create --board-id 123 --name "New Task"
cli-web-monday items update --id 456 --status done

# REPL mode
cli-web-monday
╔══════════════════════════════════════════╗
║       cli-web-monday v1.0.0             ║
║     Monday.com CLI for AI Agents        ║
╚══════════════════════════════════════════╝

monday> boards list
monday> items create --board-id 123 --name "Task"
monday[Board: Sprint 42]> exit
```

## Architecture

Generated package structure:

```
<app>/
└── agent-harness/
    ├── <APP>.md                    # Software-specific SOP
    ├── setup.py                    # PyPI config
    └── cli_web/                    # Namespace package
        └── <app>/
            ├── <app>_cli.py        # Main CLI
            ├── core/               # HTTP client, auth, session
            ├── commands/           # Click command groups
            ├── utils/              # REPL skin, formatters
            └── tests/              # Unit + E2E tests
```

## Methodology

See [CLI-ANYTHING-WEB.md](./CLI-ANYTHING-WEB.md) for the complete methodology SOP.

## License

MIT
