# cli-web-${app_name}

FILL_IN: one-paragraph description of what this CLI does and which site it wraps.

## Installation

```bash
pip install -e ${app_name}/agent-harness
```
{%- if auth_type != "none" %}

## Authentication

```bash
cli-web-${app_name} auth login
cli-web-${app_name} auth status
```

For CI/CD, set the `CLI_WEB_${APP_NAME}_AUTH_JSON` environment variable.
{%- endif %}

## Usage

FILL_IN: document each command group with example commands.

```bash
cli-web-${app_name} --help
```

## JSON Output

Every command supports `--json` for structured output:

```bash
cli-web-${app_name} FILL_IN_PRIMARY_COMMAND --json
```

Errors in `--json` mode are structured too:
`{"error": true, "code": "...", "message": "..."}`

## REPL Mode

Run without arguments to enter interactive mode:

```bash
cli-web-${app_name}
```

## Testing

```bash
cd ${app_name}/agent-harness
pip install -e .
python -m pytest cli_web/${app_name_underscore}/tests/ -v
```

## Protocol

- **Website:** FILL_IN_WEBSITE_URL
- **Protocol:** ${protocol}
- **Auth:** ${auth_type}
