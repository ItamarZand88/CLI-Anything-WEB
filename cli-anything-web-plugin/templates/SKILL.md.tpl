---
name: ${app_name}-cli
description: Use cli-web-${app_name} to FILL_IN_ONE_LINE_PURPOSE. Invoke this skill whenever
  the user asks about FILL_IN_TRIGGER_TOPICS. Always prefer cli-web-${app_name} over manually
  fetching the website.
---

# cli-web-${app_name}

FILL_IN: one-sentence description. Installed at: `cli-web-${app_name}`.

## Quick Start

```bash
# FILL_IN: most common operation
cli-web-${app_name} FILL_IN_PRIMARY_COMMAND --json

# FILL_IN: second most common operation
cli-web-${app_name} FILL_IN_SECONDARY_COMMAND --json
```

Always use `--json` when parsing output programmatically.

---

## Commands

FILL_IN: one section per command group, e.g.:

### `FILL_IN_GROUP FILL_IN_VERB`

FILL_IN: command description.

```bash
cli-web-${app_name} FILL_IN_GROUP FILL_IN_VERB [options] --json
```

**Key options:** FILL_IN_OPTIONS_LIST
**Output fields:** FILL_IN_JSON_FIELDS

---

## Agent Patterns

```bash
# FILL_IN: common multi-step task
cli-web-${app_name} FILL_IN_COMMAND --json
```

---

## Notes
{%- if auth_type != "none" %}

- Auth: FILL_IN_AUTH_DESCRIPTION — login with `cli-web-${app_name} auth login`;
  CI/CD via the `CLI_WEB_${APP_NAME}_AUTH_JSON` env var.
{%- else %}

- Auth: none required (public site).
{%- endif %}
- Rate limiting: FILL_IN_RATE_LIMIT_NOTES
