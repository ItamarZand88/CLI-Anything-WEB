# cli-web-stitch

Command-line interface for Google Stitch, the AI-powered design tool. Create, manage, and modify app designs from your terminal using natural language prompts.

## Installation

```bash
cd stitch/agent-harness
pip install -e .
```

For browser-based authentication (Google login):

```bash
pip install -e ".[auth]"
```

## Authentication

Authenticate via Google SSO in a browser window:

```bash
cli-web-stitch auth login
```

This opens a Chromium browser for Google login, then saves session cookies to `~/.config/cli-web-stitch/auth.json`.

Check authentication status:

```bash
cli-web-stitch auth status
```

Import cookies from an existing session:

```bash
cli-web-stitch auth import <path-to-cookies>
```

For CI/CD, set the `CLI_WEB_STITCH_AUTH_JSON` environment variable with the contents of `auth.json`.

## Usage

### Projects

```bash
cli-web-stitch projects list                              # List all projects
cli-web-stitch projects get <project-id>                  # Get project details
cli-web-stitch projects create "A weather app" --wait     # Create and generate a project
cli-web-stitch projects create "Chat app" --device web    # Create with device target
cli-web-stitch projects rename <id> "New Name"            # Rename a project
cli-web-stitch projects duplicate <id>                    # Duplicate a project
cli-web-stitch projects delete <id> -y                    # Delete a project (skip confirmation)
cli-web-stitch projects download <id> --output ./export   # Download project HTML
```

### Active Project Context

```bash
cli-web-stitch use <project-id>    # Set the active project
cli-web-stitch status              # Show current active project
```

### Screens

```bash
cli-web-stitch screens list --project <id>               # List screens in a project
cli-web-stitch screens get <id> --project <pid>          # Get screen details
cli-web-stitch screens get <id> --output ./screen.html   # Get screen and save to file
cli-web-stitch screens download <id> --output ./screens  # Download screen assets
```

### Design Generation

```bash
cli-web-stitch design generate "Add dark mode" --wait                              # Modify active project design
cli-web-stitch design generate "Add dark mode" --model pro --device tablet --wait  # Use pro model, target tablet
cli-web-stitch design generate "Redesign nav" --model redesign --retry             # Redesign with retry on failure
cli-web-stitch design theme --project <id>                                         # Get project design theme
cli-web-stitch design theme --json                                                 # Get theme as JSON
cli-web-stitch design history --project <id>                                       # View design generation history
```

### REPL Mode

Run `cli-web-stitch` with no arguments to enter interactive REPL mode:

```bash
cli-web-stitch
```

## JSON Output

Add `--json` to any command for structured JSON output, suitable for scripting and agent integration:

```bash
cli-web-stitch projects list --json
cli-web-stitch design generate "Add a sidebar" --wait --json
cli-web-stitch design theme --json
```

Errors are also returned as JSON when this flag is set:

```json
{"error": true, "code": "AUTH_EXPIRED", "message": "Session expired, please re-authenticate"}
```
