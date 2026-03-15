---
name: web-harness:refine
description: Refine an existing web-harness CLI by recording additional traffic and expanding command coverage. Performs gap analysis and implements missing endpoints.
argument-hint: <app-path> [focus-area]
allowed-tools: Bash(*), Read, Write, Edit, mcp__chrome-devtools__*
---

## CRITICAL: Read CLI-ANYTHING-WEB.md First

**Before refining, read `${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md`.** All new commands and tests must follow the same standards as the original build. CLI-ANYTHING-WEB.md is the single source of truth for architecture, patterns, and quality requirements.

# Web-Harness: Refine Existing Harness

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md

Target: $1
Focus area: $2

## Process

1. **Read existing SOP**: Load `<app>/agent-harness/<APP>.md`
2. **Read existing CLI**: Scan implemented commands in `cli_web/<app>/commands/`
3. **Gap analysis**:
   - Compare known endpoints vs implemented commands
   - If focus area specified, concentrate on that domain
   - If no focus, do broad gap analysis across all capabilities
4. **Record new traffic**: Open Chrome DevTools, navigate to underexplored areas
5. **Analyze new endpoints**: Add to API map in `<APP>.md`
6. **Implement new commands**: Add to existing command groups or create new ones
7. **Update tests**: Add unit + E2E tests for new commands
8. **Run full test suite**: Ensure no regressions
9. **Update TEST.md**: Document new coverage

## Rules

- NEVER break existing commands
- NEVER change existing command signatures
- ADD new commands and options only
- Run full test suite after changes
- Update `<APP>.md` with new endpoints
