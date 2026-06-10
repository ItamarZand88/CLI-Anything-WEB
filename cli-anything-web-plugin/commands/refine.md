---
name: cli-anything-web:refine
description: Refine an existing cli-anything-web CLI by recording additional traffic and expanding command coverage. Invokes the gap-analyzer skill as its first step, then implements missing endpoints.
argument-hint: <app-path> [focus-area]
allowed-tools: Bash(*), Read, Write, Edit, mcp__chrome-devtools__*
---

## CRITICAL: Read HARNESS.md First

**Before refining, read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`.** All new commands and tests must follow the same standards as the original build. HARNESS.md is the navigational overview; the rules themselves are defined in `${CLAUDE_PLUGIN_ROOT}/skills/shared/CONVENTIONS.md`.

# CLI-Anything-Web: Refine Existing Harness

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target: $1
Focus area: $2

## Process

> **Skills used:** `gap-analyzer` (mandatory FIRST step), `methodology`
> (pipeline), `capture` (if re-recording)

1. **Gap analysis (FIRST step — always)**: Invoke the `gap-analyzer` skill
   (`${CLAUDE_PLUGIN_ROOT}/skills/gap-analyzer/SKILL.md`) with
   `APP_PATH=<app>/agent-harness`. It diffs the captured/documented API surface
   against the implemented commands and client methods. Every reported gap must
   cite its evidence: the endpoint entry in `<APP>.md` and/or
   `traffic-capture/traffic-analysis.json` (with `raw-traffic.json` hit counts
   for priority). If a focus area is specified, filter the report to that domain.
2. **Present gap report**: Show the user the gap analysis results and confirm which gaps to address before proceeding with any recording or implementation
3. **Record new traffic**: Use playwright-cli (see HARNESS.md Phase 1) or chrome-devtools-mcp fallback
4. **Analyze new endpoints**: Add to API map in `<APP>.md`
5. **Implement new commands**: Add to existing command groups or create new ones
6. **Update REPL help**: Edit `_print_repl_help()` in `<app>_cli.py` to reflect every new command and option added (CONVENTIONS.md §REPL Rules help-sync rule). Users typing `help` in the REPL must see all available filters and options.
7. **Update tests**: Add unit + E2E tests for new commands
8. **Run full test suite**: Ensure no regressions
9. **Update TEST.md**: Document new coverage

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
- New commands follow CONVENTIONS.md (exceptions, --json envelope, REPL rules)
- Full test suite passes (including new tests)
- TEST.md updated with new test coverage
- `<APP>.md` updated with new endpoints
- **REPL `help` output reflects all new commands and key options**

## Notes

- Refine is **incremental** — it only adds, never removes commands
- Always **present the gap report** before implementing changes
- Run the full test suite after changes to ensure no regressions
