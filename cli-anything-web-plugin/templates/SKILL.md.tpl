---
name: ${app_name}-cli
description: >
  Use cli-web-${app_name} to FILL_IN_ONE_LINE_PURPOSE (key use case first).
  Use when the user asks about FILL_IN_TRIGGER_TOPICS or wants to
  FILL_IN_TASK_VERBS from the terminal. Prefer cli-web-${app_name} over
  manually fetching the website.
when_to_use: >
  Trigger phrases: FILL_IN_QUOTED_TRIGGER_PHRASES. Not for
  FILL_IN_ADJACENT_BUT_DIFFERENT_TASKS.
---

# cli-web-${app_name}

FILL_IN: one-line purpose. Install: `pip install cli-web-${app_name}`

## Commands

FILL_IN: the real command surface, grouped — verify every entry against
`cli-web-${app_name} --help` before publishing this skill.

| Command | Purpose |
|---------|---------|
| `FILL_IN_GROUP FILL_IN_VERB [args]` | FILL_IN |

## Examples

```bash
# FILL_IN: most common operation
cli-web-${app_name} FILL_IN_PRIMARY_COMMAND --json

# FILL_IN: 2-4 more concrete invocations agents actually need
cli-web-${app_name} FILL_IN_SECONDARY_COMMAND --json
```

## JSON output

Every command supports `--json`: success is
`{"success": true, "data": ...}`, errors are
`{"error": true, "code": "...", "message": "..."}`. Use `--json` whenever
parsing output programmatically. List commands also support `--jsonl`
(one compact object per line) for `jq`/agent piping.
{%- if auth_type != "none" %}

## Auth

FILL_IN_AUTH_DESCRIPTION. Log in with `cli-web-${app_name} auth login`;
CI/CD uses the `CLI_WEB_${APP_NAME}_AUTH_JSON` env var. Diagnose setup
problems with `cli-web-${app_name} doctor`.
{%- endif %}

## Utilities

`cli-web-${app_name} doctor [--json]` — diagnose install/auth setup.
`cli-web-${app_name} mcp-serve` — serve every command as MCP tools over stdio.

## Agent tips

- FILL_IN: only genuinely useful patterns (piping, pagination, context);
  delete this section if there are none.

<!--
Authoring rules (delete this comment): see
cli-anything-web-plugin/skills/standards/references/skill-authoring.md.
Hard limits: description ≤1024 chars, body ≤500 lines (target ≤150),
third-person description, every command verified via --help.
-->
