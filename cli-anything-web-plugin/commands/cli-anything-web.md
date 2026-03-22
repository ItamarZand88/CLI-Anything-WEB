---
name: cli-anything-web
description: Generate a complete agent-native CLI for any web app by recording and analyzing network traffic via playwright-cli. Runs the full pipeline with site assessment, capture, implementation, testing, and verification.
argument-hint: <url>
allowed-tools: Bash(*), Read, Write, Edit, mcp__chrome-devtools__*
---

# CLI-Anything-Web: Full Pipeline

Read the methodology overview:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target URL: $ARGUMENTS

## Prerequisites Check

### Step 1: Check playwright-cli availability
!`npx @playwright/cli@latest --version 2>&1 && echo "PLAYWRIGHT_OK" || echo "PLAYWRIGHT_FAIL"`

**If PLAYWRIGHT_OK** → use playwright-cli for all operations (primary path).

**If PLAYWRIGHT_FAIL** → If playwright-cli is not available, see HARNESS.md for the MCP fallback path.

### NEVER use `mcp__claude-in-chrome__*` tools -- blocked, cannot capture request bodies.

## Execution Plan

Run the full pipeline by invoking skills in sequence. **Each phase checks for
prior completion and skips if already done.**

1. Check playwright-cli availability (see Prerequisites above)
2. **Check pipeline state:** `python ${CLAUDE_PLUGIN_ROOT}/scripts/phase-state.py status <app>`
   - If a phase is already `done` → skip it and proceed to the next
   - If a phase `failed` with `retryable` → retry automatically
   - If a phase `failed` with `fatal` → report and ask user
3. For each phase, check before running:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/phase-state.py check <app> --phase <phase>
   # Exit 0 = skip (already done), Exit 1 = run
   ```
4. Invoke `capture` skill -- Phase 1 site assessment + traffic recording
   - Also check capture checkpoint: `python ${CLAUDE_PLUGIN_ROOT}/scripts/capture-checkpoint.py restore <app>`
5. Invoke `methodology` skill -- Phase 2 analyze/design/implement
   - Agent MUST read a reference CLI first (same protocol) — see methodology skill
6. Invoke `testing` skill -- Phase 3 test writing/documentation
7. Invoke `standards` skill -- Phase 4 publish and verify + generate Claude skill

After each phase completes, mark it:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/phase-state.py complete <app> --phase <phase> --output <output-path>
```

Each skill handles its phases completely and invokes the next when done.
See HARNESS.md for the pipeline overview and critical rules.

Extract the app name from the URL (e.g., `monday.com` → `monday`, `notion.so` → `notion`).

## Success Criteria

The command succeeds when:
1. All core modules are implemented and functional (`client.py`, `auth.py`, `session.py`, `models.py`)
2. CLI supports both one-shot commands and REPL mode
3. `--json` output mode works for all commands
4. All tests pass (100% pass rate)
5. Subprocess tests use `_resolve_cli()` and pass with `CLI_WEB_FORCE_INSTALLED=1`
6. TEST.md contains both plan (Part 1) and results (Part 2)
7. README.md documents installation and usage
8. `setup.py` is created and local installation works
9. CLI is available in PATH as `cli-web-<app>`
10. `.claude/skills/<app>-cli/SKILL.md` exists at the project root

## Output Structure

```
<app-name>/
└── agent-harness/
    ├── <APP>.md               # API map, data model, auth scheme
    ├── setup.py               # PyPI config (find_namespace_packages)
    └── cli_web/               # Namespace package (NO __init__.py)
        └── <app>/             # Sub-package
            ├── __init__.py    # Required — marks as sub-package
            ├── README.md
            ├── <app>_cli.py   # Main CLI entry point
            ├── __main__.py
            ├── core/
            │   ├── client.py
            │   ├── auth.py
            │   ├── session.py
            │   └── models.py
            ├── utils/
            │   ├── repl_skin.py
            │   ├── output.py
            │   └── config.py
            └── tests/
                ├── TEST.md
                ├── test_core.py
                └── test_e2e.py
```

**No-auth sites:** Remove `core/auth.py`, `core/session.py`, and auth commands
from the structure above. Only create what the CLI actually needs.

## Progress Tracking

After each phase, report status in this format:

```
┌─────────┬────────┬────────────────────────────────────────────┐
│ Phase   │ Status │ Description                                │
├─────────┼────────┼────────────────────────────────────────────┤
│ Phase 1 │ ...    │ Capture — Traffic Capture + Auth           │
│ Phase 2 │ ...    │ Methodology — Analyze + Design + Implement │
│ Phase 3 │ ...    │ Test — Write Tests + Document Results      │
│ Phase 4 │ ...    │ Standards — Publish + Smoke Test + Skill   │
└─────────┴────────┴────────────────────────────────────────────┘
```
