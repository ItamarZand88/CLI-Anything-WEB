# Contributing to CLI-Anything-Web

Thanks for your interest in contributing! CLI-Anything-Web is a Claude Code plugin that turns any website into a production-grade Python CLI. Whether you want to build a CLI for your favorite site, improve the plugin itself, or fix a broken scraper, there's a place for you.

---

## Ways to Contribute

### 1. Build a New CLI

The highest-impact contribution: generate a CLI for a website that doesn't have one yet.

1. Install the plugin in Claude Code
2. Run `/cli-anything-web <url>` on a site you use
3. The agent captures traffic, analyzes endpoints, and generates a complete CLI
4. Test it locally (see [Testing](#testing) below)
5. Submit a PR with the generated directory

Your CLI becomes a reference implementation shipped with the project. We currently have 7:
**futbin**, **notebooklm**, **gh-trending**, **producthunt**, **unsplash**, **booking**, **stitch**.

### 2. Improve the Plugin

The generation pipeline lives in `cli-anything-web-plugin/skills/` with 4 phases: capture, methodology, testing, and standards. Improvements here make every future CLI better.

Examples:
- Add a new protocol handler (WebSocket, Server-Sent Events)
- Improve the traffic analysis heuristics
- Add new reference patterns to `skills/methodology/references/`
- Enhance the 75-check validation in the standards phase

### 3. Fix a Broken CLI

Websites change their APIs, HTML structure, and anti-bot protections without notice. If a CLI stops working:

1. Identify what changed (new endpoints, different response format, added bot protection)
2. Update the client code in `<app>/agent-harness/cli_web/<app>/`
3. Run the tests to confirm the fix
4. Submit a PR

---

## Development Setup

```bash
# Clone the repo
git clone https://github.com/ItamarZand88/CLI-Anything-WEB.git
cd CLI-Anything-WEB

# Install a CLI to test (gh-trending is the simplest — no auth required)
pip install -e gh-trending/agent-harness
cli-web-gh-trending repos list --json
```

### Prerequisites

| Requirement | Version | Why |
|------------|---------|-----|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | With plugin support | Runs the generation pipeline |
| [Node.js](https://nodejs.org/) | 18+ | For Playwright traffic capture |
| [Python](https://python.org/) | 3.10+ | Generated CLIs are Python |

---

## Testing

Every generated CLI has tests under `cli_web/<app>/tests/`. To run them:

```bash
cd <app>/agent-harness
pip install -e .
python -m pytest cli_web/<app>/tests/ -v
```

Run a single test:

```bash
python -m pytest cli_web/<app>/tests/test_core.py::test_player_search -v -s
```

For subprocess tests (tests that invoke the CLI binary directly), set:

```bash
export CLI_WEB_FORCE_INSTALLED=1
```

---

## Code Style

Generated CLIs follow strict conventions. When modifying or creating CLI code:

- **Framework**: [Click](https://click.palletsprojects.com/) with `@click.group(invoke_without_command=True)`
- **`--json` on every command**: All commands must support `--json` for structured output, including errors: `{"error": true, "code": "AUTH_EXPIRED", "message": "..."}`
- **Typed exceptions**: Every CLI defines `AppError`, `AuthError`, `RateLimitError`, `NetworkError`, `ServerError`, `NotFoundError` in `core/exceptions.py`. No generic `RuntimeError`.
- **Namespace packages**: `cli_web/` has no `__init__.py`; sub-packages do
- **REPL default**: Running the CLI with no subcommand enters interactive REPL mode
- **Auth storage**: Credentials in `auth.json` with `chmod 600`, never hardcoded
- **Output**: Rich (`>=13.0`) for tables, spinners, and colored output

---

## Commit Messages

Use [conventional commits](https://www.conventionalcommits.org/):

```
feat: add cli-web-spotify with playlist and search commands
fix: update producthunt selectors after site redesign
docs: add WebSocket protocol to supported list
refactor: extract shared WAF bypass into plugin utility
test: add E2E tests for booking hotel detail endpoint
```

---

## PR Process

1. **Branch** from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make your changes** — follow the code style above

3. **Validate the plugin** (if you touched plugin code):
   ```bash
   bash cli-anything-web-plugin/verify-plugin.sh
   ```
   This runs 75 checks covering structure, naming, and conventions.

4. **Run tests** for any CLIs you modified:
   ```bash
   cd <app>/agent-harness
   python -m pytest cli_web/<app>/tests/ -v
   ```

5. **Open a PR** against `main` with:
   - A clear description of what changed and why
   - Test results (paste `--json` output for new commands)
   - Note if any website APIs changed

---

## Quality Standards

The plugin includes a 75-check validation suite (`/cli-anything-web:validate <path>`) that covers:

- Directory structure and namespace package layout
- Exception hierarchy completeness
- `--json` support on all commands
- Auth flow implementation (cookie storage, env var fallback)
- Test coverage (unit, E2E, subprocess)
- REPL mode configuration
- Output formatting (no raw protocol leaks)

PRs for new CLIs should pass this validation. PRs for plugin improvements should not break it.

---

## Questions?

- [Open an issue](https://github.com/ItamarZand88/CLI-Anything-WEB/issues) for bugs or feature requests
- [Request a CLI](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/new) for a specific website
