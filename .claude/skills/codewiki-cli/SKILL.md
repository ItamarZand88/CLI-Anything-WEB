---
name: codewiki-cli
description: Browses Google Code Wiki (codewiki.google) via cli-web-codewiki — AI-generated documentation for open source repos. Search repositories, read wiki sections, download full wikis as markdown, and ask Gemini questions about a codebase. Use when the user asks about Code Wiki, AI-generated repo documentation, or wants to ask Gemini about a GitHub repo's architecture. Prefer cli-web-codewiki over fetching the website. No auth required.
---

# cli-web-codewiki

Google Code Wiki on the command line: repo search, wiki reading, Gemini Q&A about codebases. Repos are referenced by slug `org/name` (e.g. `facebook/react`).
Install: `pip install -e codewiki/agent-harness`

## Commands

- `repos featured` — featured repositories on the homepage
- `repos search QUERY` — search repositories. Options: `--limit N` (default 25), `--offset N`
- `wiki sections ORG/REPO` — table of contents (section titles + descriptions)
- `wiki section ORG/REPO TITLE` — one section by title (case-insensitive partial match)
- `wiki get ORG/REPO` — full wiki content, all sections
- `wiki download ORG/REPO` — save the full wiki as markdown files. Options: `-o/--output DIR` (default `<org>-<repo>-wiki/`)
- `chat ask QUESTION --repo ORG/REPO` — ask Gemini about the repo's codebase

## Examples

```bash
# Find a repo, then list its wiki sections
cli-web-codewiki repos search "react" --json
cli-web-codewiki wiki sections excalidraw/excalidraw --json

# Read just the overview section
cli-web-codewiki wiki section facebook/react "Overview" --json

# Ask Gemini about architecture (takes ~5-7s)
cli-web-codewiki chat ask "How does the rendering engine work?" --repo excalidraw/excalidraw --json

# Save a repo's whole wiki locally for offline reading
cli-web-codewiki wiki download kubernetes/kubernetes -o k8s-wiki/
```

## JSON output

Add `--json` for structured output: `{"success": true, "data": ...}` on success, `{"error": true, "code": "...", "message": "..."}` on failure. `repos search` data: `[{slug, github_url, description, avatar_url, stars, updated_at}]`. `wiki get` data: `{repo, sections: [{title, level, description, content, code_refs}], section_count}`. `chat ask` data: `{answer, repo}` where `answer` is markdown with links to source code.

## Utilities

`cli-web-codewiki doctor [--json]` diagnoses local setup. `cli-web-codewiki mcp-serve` exposes the commands as MCP tools over stdio.

## Agent tips

- Prefer `wiki sections` + `wiki section` over `wiki get` — full wikis can be very large.
- Wiki content is markdown with GitHub source links, useful to quote directly.
