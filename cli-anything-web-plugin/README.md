# CLI-Anything-Web — Agent-Native CLIs for Web Apps

**Build production-grade Python CLIs for closed-source web applications by capturing and analyzing their HTTP traffic.**

## How It Works

1. You point CLI-Anything-Web at a web app URL
2. playwright-cli opens a browser, runs reconnaissance, and captures API traffic
3. Claude systematically exercises the app, capturing all API traffic
4. Claude analyzes the traffic, maps the API, and generates a complete CLI
5. You get `cli-web-<app>` on your PATH — ready for agents

## Quick Start

### Step 1: Load the plugin

```bash
claude --plugin-dir /path/to/cli-anything-web-plugin
```

### Step 2: Generate a CLI

```bash
/cli-anything-web https://monday.com
```

playwright-cli auto-launches a browser. Log in when prompted. The agent captures
traffic, analyzes the API, and generates a complete CLI — all in one command.

## Commands

| Command | Description |
|---------|-------------|
| `/cli-anything-web <url>` | Full 8-phase pipeline — record, analyze, generate CLI |
| `/cli-anything-web:record <url>` | Record traffic only (Phase 1) |
| `/cli-anything-web:refine <path> [focus]` | Expand coverage of existing CLI |
| `/cli-anything-web:test <path>` | Run tests and update TEST.md |
| `/cli-anything-web:validate <path>` | Validate against HARNESS.md standards |
| `/cli-anything-web:list` | List all installed and generated `cli-web-*` CLIs |

## Prerequisites

- **Claude Code** with plugin support
- **Node.js** (for playwright-cli via npx; chrome-devtools-mcp as fallback)
- **Python 3.10+**

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

See [HARNESS.md](./HARNESS.md) for the complete methodology SOP.

## License

MIT
