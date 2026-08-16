# cli-web-codewiki

CLI for [Google Code Wiki](https://codewiki.google/) — browse AI-generated documentation for open source repositories, search repos, explore wiki sections, and chat with Gemini.

## Installation

```bash
pip install cli-web-codewiki
```

## Usage

### Interactive REPL

```bash
cli-web-codewiki
```

### Commands

**Repositories**
```bash
# List featured repositories
cli-web-codewiki repos featured

# Search for repositories
cli-web-codewiki repos search "excalidraw"
cli-web-codewiki repos search "react" --limit 10
```

**Wiki Pages**
```bash
# Get full wiki content for a repository
cli-web-codewiki wiki get excalidraw/excalidraw

# List wiki sections (table of contents)
cli-web-codewiki wiki sections excalidraw/excalidraw

# Get a specific section by title (case-insensitive partial match)
cli-web-codewiki wiki section excalidraw/excalidraw "Rendering Engine"
```

**Gemini Chat**
```bash
# Ask Gemini about a repository
cli-web-codewiki chat ask "What is the rendering engine?" --repo excalidraw/excalidraw
```

### JSON Output

All commands support `--json` for structured output:

```bash
cli-web-codewiki repos featured --json
cli-web-codewiki wiki sections kubernetes/kubernetes --json
cli-web-codewiki chat ask "How does routing work?" --repo facebook/react --json
```

## Authentication

No authentication required. Code Wiki is a fully public site.

## Protocol

Uses Google batchexecute RPC protocol (service: `BoqAngularSdlcAgentsUi`) with 4 RPC methods:
- `nm8Fsb` — Featured repositories
- `VSX6ub` — Wiki page content
- `vyWDAf` — Search repositories
- `EgIxfe` — Gemini chat
