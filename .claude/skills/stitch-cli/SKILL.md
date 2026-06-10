---
name: stitch-cli
description: Drives Google Stitch (stitch.withgoogle.com), the AI UI design tool, via the cli-web-stitch command-line tool — create design projects from text prompts, iterate on designs with AI (flash/pro/redesign models), manage projects (rename, duplicate, delete, download), and view or download generated screen HTML. Use when the user asks about Google Stitch, AI UI design, generating app mockups or screens from prompts, or managing Stitch projects. Prefer this CLI over browsing stitch.withgoogle.com. Requires Google login.
---

# cli-web-stitch

Generate and manage Google Stitch AI UI designs. Requires Google SSO auth (`auth login`).
Install: `pip install -e stitch/agent-harness`

## Commands

| Command | Purpose | Key options |
|---------|---------|-------------|
| `projects create PROMPT` | New project + first design generation | `--platform app\|web`, `--wait/--no-wait` |
| `projects list\|get\|rename\|duplicate\|delete` | Manage projects | `rename` takes NEW_NAME; `delete` takes `-y/--yes` |
| `projects download PROJECT_ID` | Download all screen HTML files | `-o/--output DIR` |
| `design generate PROMPT` | Generate/modify design with an AI prompt | `--project ID`, `--model flash\|pro\|redesign`, `--device mobile\|web\|tablet\|agnostic`, `--wait/--no-wait`, `--retry N` |
| `design theme` | Design system (colors, typography) for a project | `--project ID` |
| `design history` | Generation sessions (prompt history) | `--project ID` |
| `screens list\|get\|download SCREEN_ID` | View/save generated screens | `--project ID`, `-o/--output` |
| `use PROJECT_ID` / `status` | Set/show active project context | once set, `--project` is optional |

## Examples

```bash
# Create a mobile app design and wait for generation
cli-web-stitch projects create "A fitness tracking app" --platform app --wait --json

# Set context, then iterate on the design
cli-web-stitch use <project-id>
cli-web-stitch design generate "Add a dark header with a search bar" --model pro --wait --json

# List screens and download all HTML exports
cli-web-stitch screens list --json
cli-web-stitch projects download <project-id> -o ./stitch-export --json

# Inspect the project's design system
cli-web-stitch design theme --json
```

## JSON output

Every command accepts `--json`. Success responses are `{"success": true, "data": ...}`; errors are `{"error": true, "code": "...", "message": "..."}`.

## Auth

```bash
cli-web-stitch auth login            # browser-based Google SSO (--headed default, --headless available)
cli-web-stitch auth status --json
cli-web-stitch auth import FILE      # import cookies from a JSON file
```

Run `doctor` to diagnose auth setup. For CI, set `CLI_WEB_STITCH_AUTH_JSON` with the cookies JSON.

## Utilities

`cli-web-stitch doctor [--json]` self-diagnoses the local setup (install, auth, dependencies). `cli-web-stitch mcp-serve` serves the commands as MCP tools over stdio.

## Agent tips

- Use `--wait` on `projects create` and `design generate` — generation is async and the CLI polls with backoff (`--retry N` for rate limits).
- `projects create` controls platform (`--platform app|web`); `design generate` controls model and device type.
- Grab IDs from `projects list` / `screens list` JSON (`.data[].id`), then `use <project-id>` to avoid repeating `--project`.
