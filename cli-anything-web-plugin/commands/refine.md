---
name: cli-anything-web:refine
description: Refine an existing cli-anything-web CLI by recording additional traffic and expanding command coverage. Performs gap analysis and implements missing endpoints.
argument-hint: <app-path> [focus-area]
allowed-tools: Bash(*), Read, Write, Edit, mcp__chrome-devtools__*
---

## CRITICAL: Read HARNESS.md First

**Before refining, read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`.** All new commands and tests must follow the same standards as the original build. HARNESS.md is the single source of truth for architecture, patterns, and quality requirements.

# CLI-Anything-Web: Refine Existing Harness

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target: $1
Focus area: $2

## Process

> **Skills used:** `methodology` (pipeline), `capture` (if re-recording)

1. **Read existing SOP**: Load `<app>/agent-harness/<APP>.md`
2. **Read existing CLI**: Scan implemented commands in `cli_web/<app>/commands/`
3. **Gap analysis**: Read `${CLAUDE_PLUGIN_ROOT}/skills/gap-analyzer/SKILL.md` and
   follow its instructions to produce a structured gap report. If a focus area is
   specified, filter the report to that domain.
4. **Present gap report**: Show the user the gap analysis results and confirm which gaps to address before proceeding with any recording or implementation
5. **Record new traffic**: Use playwright-cli (see HARNESS.md Phase 1) or chrome-devtools-mcp fallback
6. **Analyze new endpoints**: Add to API map in `<APP>.md`
7. **Implement new commands**: Add to existing command groups or create new ones
8. **Update REPL help**: Edit `_print_repl_help()` in `<app>_cli.py` to reflect every new command and option added. The REPL help must stay in sync with the actual command surface — users typing `help` in the REPL must see all available filters and options.
9. **Update tests**: Add unit + E2E tests for new commands
10. **Run full test suite**: Ensure no regressions
11. **Update TEST.md**: Document new coverage

## Rules

- NEVER break existing commands
- NEVER change existing command signatures
- ADD new commands and options only
- Run full test suite after changes
- Update `<APP>.md` with new endpoints
- **Always update `_print_repl_help()` to match the actual command surface**

## Success Criteria

- All identified gaps have been addressed or explicitly deferred
- No existing commands are broken or have changed signatures
- New commands follow HARNESS.md standards
- Full test suite passes (including new tests)
- TEST.md updated with new test coverage
- `<APP>.md` updated with new endpoints
- **REPL `help` output reflects all new commands and key options**

## Notes

- Refine is **incremental** — it only adds, never removes commands
- Always **present the gap report** before implementing changes
- Run the full test suite after changes to ensure no regressions
