# Quickstart

Get from zero to a working CLI in under 5 minutes.

## Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** (for Playwright traffic capture)
- **Claude Code** CLI installed and authenticated

## Install the Plugin

```bash
git clone https://github.com/AItamarZand/CLI-Anything-Web.git
cd CLI-Anything-Web
claude plugin install ./cli-anything-web-plugin
```

## Generate a CLI for Any Website

```bash
claude "/cli-anything-web https://example.com"
```

The plugin walks through 4 phases automatically: capture traffic, analyze APIs, generate code, and publish.

## Try an Existing CLI (No Auth Required)

The easiest way to see what gets generated — install and run `cli-web-gh-trending`:

```bash
pip install -e gh-trending/agent-harness
cli-web-gh-trending repos list
cli-web-gh-trending repos list --language python --since weekly --json
```

Or start the interactive REPL:

```bash
cli-web-gh-trending
```

## Next Steps

- See the full [README](README.md) for architecture details and all 7 generated CLIs
- Browse `registry.json` for a machine-readable index of every CLI
- Read `CLAUDE.md` for contributor conventions
