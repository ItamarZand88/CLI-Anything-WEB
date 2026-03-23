---
name: stitch-cli
description: Use cli-web-stitch to interact with Google Stitch AI design tool — create UI designs from text prompts, list and manage design projects (rename, duplicate, download), view and download generated screens, choose AI models (flash/pro/redesign), browse design themes, and iterate on designs with AI. Invoke this skill whenever the user asks about Google Stitch, AI UI design, vibe design, generating app mockups, creating UI from prompts, Stitch design projects, screen layouts, design themes, model selection, or wants to generate mobile or web app designs programmatically. Also trigger for Stitch project management (create, list, rename, duplicate, delete, download). Always prefer cli-web-stitch over manually browsing stitch.withgoogle.com.
---

# cli-web-stitch

CLI for Google Stitch (stitch.withgoogle.com) — an AI-native UI design canvas by Google Labs. Installed at: `cli-web-stitch`.

## Quick Start

```bash
# List all design projects
cli-web-stitch projects list --json

# List screens in a project
cli-web-stitch screens list --project <project-id> --json

# Modify an existing design
cli-web-stitch design generate "Add a dark header" --project <id> --wait --json
```

Always use `--json` when parsing output programmatically.

---

## Commands

### `projects list`
List all design projects.

```bash
cli-web-stitch projects list --json
```

**Output fields:** `id`, `resource_name`, `title`, `created_at`, `modified_at`, `status`

### `projects get <project-id>`
Get project details.

```bash
cli-web-stitch projects get <project-id> --json
```

### `projects create <prompt>`
Create a new project from a text prompt.

```bash
cli-web-stitch projects create "A fitness tracking app" --device mobile --wait --json
```

**Key options:** `--device mobile|web|tablet|agnostic`, `--wait` (poll until complete), `--no-wait`

### `projects rename <project-id> <new-name>`
Rename a project.

```bash
cli-web-stitch projects rename <project-id> "My New Name" --json
```

### `projects duplicate <project-id>`
Duplicate a project.

```bash
cli-web-stitch projects duplicate <project-id> --json
```

### `projects download <project-id>`
Download all screen HTML files from a project.

```bash
cli-web-stitch projects download <project-id> --output ./export --json
```

**Key options:** `--output DIR` (save directory)

### `projects delete <project-id>`
Delete a project.

```bash
cli-web-stitch projects delete <project-id> -y --json
```

**Key options:** `-y` (skip confirmation)

### `screens list`
List all screens in the active project.

```bash
cli-web-stitch screens list --project <project-id> --json
```

**Output fields:** `id`, `name`, `description`, `width`, `height`, `html_url`, `agent_name`

### `screens get <screen-id>`
Get screen details and optionally download HTML.

```bash
cli-web-stitch screens get <screen-id> --project <id> --output screen.html --json
```

### `screens download <screen-id>`
Download a screen's HTML file.

```bash
cli-web-stitch screens download <screen-id> --project <id> --output ./export --json
```

**Key options:** `--project ID`, `--output DIR`

### `design generate <prompt>`
Send an AI prompt to modify/generate design in a project.

```bash
cli-web-stitch design generate "Add dark mode" --project <id> --wait --json
```

**Key options:** `--device mobile|web|tablet|agnostic`, `--model flash|pro|redesign`, `--wait` (poll until complete), `--no-wait`, `--retry N`

### `design theme`
List available design themes for a project.

```bash
cli-web-stitch design theme --project <project-id> --json
```

### `design history`
List generation sessions (prompt history) for a project.

```bash
cli-web-stitch design history --project <project-id> --json
```

**Output fields:** `id`, `resource_name`, `prompt`, `status`

### `use <project-id>`
Set active project context (avoids passing `--project` every time).

```bash
cli-web-stitch use <project-id> --json
cli-web-stitch screens list --json  # uses active project
```

### `status`
Show current active project context.

```bash
cli-web-stitch status --json
```

### `auth login`
Login via Google SSO (opens browser).

```bash
cli-web-stitch auth login --headed --json
```

**Key options:** `--headed` (visible browser, default), `--headless`

### `auth status`
Check current authentication status.

```bash
cli-web-stitch auth status --json
```

### `auth import <file>`
Import auth cookies from a file.

```bash
cli-web-stitch auth import cookies.json --json
```

---

## Agent Patterns

```bash
# List all projects and get the first one's screens
PROJECT_ID=$(cli-web-stitch projects list --json | python -c "import json,sys; print(json.load(sys.stdin)['data'][0]['id'])")
cli-web-stitch screens list --project $PROJECT_ID --json

# Download all HTML exports from a project
cli-web-stitch projects download $PROJECT_ID --output ./stitch-export

# Modify a design and wait for completion
cli-web-stitch design generate "Make the header blue" --project $PROJECT_ID --wait --json
```

---

## Notes

- Auth: Required (Google SSO). Run `cli-web-stitch auth login` first.
- Protocol: Google batchexecute RPC (service: Nemo)
- Projects can be created from the CLI via `projects create <prompt>`.
- The `design generate` command works for both new and existing projects.
- Rate limiting: Exponential backoff on 429 responses.
