---
name: boilerplate
version: 1.0.0
description: Procedural guide for scaffolding cli-web-* CLIs from the plugin's Jinja2 templates. Describes which template renders with which variables for each site profile. The scaffold-cli.py script (v2) is the primary path; this skill documents the template inventory and variable contract behind it.
user-invocable: false
---

# Boilerplate Generator (Template-Driven)

> **Primary method:** run the v2 scaffold script — it renders everything below
> deterministically and writes a `.manifest.json` provenance file:
> ```bash
> python ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold-cli.py <app>/agent-harness \
>   --app-name <app> \
>   --protocol <rest|graphql|html-scraping|batchexecute> \
>   --http-client <httpx|curl_cffi> \
>   --auth-type <none|cookie|api-key|google-sso> \
>   --resource <name> [--resource <name> ...] \
>   [--has-polling] [--has-context] [--has-partial-ids]
> ```
> Requires `pip install jinja2` (TEMPLATE_VERSION 2.0.0). Each repeatable
> `--resource` flag scaffolds a `commands/<resource>.py` module.
>
> **If the script is unavailable**, do NOT render templates by hand from
> memory — follow `skills/shared/RECOVERY.md` §scaffold-cli.py Unavailable
> (adapt from the newest generated CLI, e.g., `capitoltrades/agent-harness/`).

All templates live in `${CLAUDE_PLUGIN_ROOT}/templates/*.tpl` (Jinja2 syntax).
Generated code must satisfy `skills/shared/CONVENTIONS.md` — the templates
already encode those rules; never "simplify" them away.

---

## Step 1: Collect Template Variables

| Variable | Type | Source | Example |
|----------|------|--------|---------|
| `app_name` | str | CLI name (`cli-web-<app>` → `<app>`) | `hackernews` |
| `APP_NAME` | str | UPPER_SNAKE (hyphens → underscores first) | `HACKERNEWS` |
| `AppName` | str | PascalCase | `HackerNews` |
| `protocol` | enum | traffic-analysis.json: `rest`, `graphql`, `html-scraping`, `batchexecute` | `rest` |
| `http_client` | enum | protection detection: `httpx`, `curl_cffi` | `httpx` |
| `auth_type` | enum | site profile: `none`, `cookie`, `api-key`, `google-sso` | `cookie` |
| `resources` | list[str] | `<APP>.md` endpoint groups (one `--resource` flag each) | `stories users` |
| `has_polling` | bool | async/long-running operations exist | `false` |
| `has_context` | bool | CLI needs `use <id>` / `status` context | `false` |
| `has_partial_ids` | bool | resource IDs support prefix matching | `false` |

Casing is derived inside the templates via Jinja2 filters — you only supply
`--app-name`.

## Step 2: Template → Output Map

| Template (`templates/`) | Output | Rendered when |
|--------------------------|--------|---------------|
| `exceptions.py.tpl` | `core/exceptions.py` | always |
| `client_rest_httpx.py.tpl` | `core/client.py` | `http_client=httpx`, non-batchexecute (GraphQL/HTML variants are `{% if %}` blocks inside) |
| `client_rest_curl.py.tpl` | `core/client.py` | `http_client=curl_cffi`, non-batchexecute |
| `client_batchexecute.py.tpl` | `core/client.py` | `protocol=batchexecute` |
| `auth.py.tpl` (UNIFIED) | `core/auth.py` | `auth_type != none` — google-sso specifics (cookie domain priority, regional forcing) are a `{% if auth_type == "google_sso" %}` block; there is no separate Google template |
| `cli_entry.py.tpl` | `<app>_cli.py` (+ `__main__.py`) | always — REPL default, UTF-8 fix, `--json` propagation |
| `command_group.py.tpl` | `commands/<resource>.py` | once per `--resource` flag — Click group skeleton wired to the client |
| `helpers.py.tpl` | `utils/helpers.py` | always (`handle_errors`, `print_json`) |
| `helpers_polling.py.tpl` | appended to helpers | `--has-polling` |
| `helpers_context.py.tpl` | appended to helpers | `--has-context` |
| `helpers_partial_ids.py.tpl` | appended to helpers | `--has-partial-ids` |
| `output.py.tpl` | `utils/output.py` | always (`json_success`/`json_error`) |
| `setup.py.tpl` | `setup.py` | always — namespace packages, entry point, deps per `http_client`/`protocol` |
| `conftest.py.tpl` | `tests/conftest.py` | always |
| `test_e2e.py.tpl` | `tests/test_e2e.py` | always — `_resolve_cli` + `TestCLISubprocess` fixtures pre-wired |
| `rpc_types.py.tpl`, `rpc_encoder.py.tpl`, `rpc_decoder.py.tpl` | `core/rpc/` | `protocol=batchexecute` only |
| `README.md.tpl` | `cli_web/<app>/README.md` skeleton | always |
| `SKILL.md.tpl` | per-CLI skill skeleton | always (filled in during Phase 4) |

Also produced by the script (not templates): `__init__.py` files, vendored
`utils/repl_skin.py` (canonical source `cli-web-core/cli_web_core/repl_skin.py`,
synced by `cli-web-devkit resync`), `utils/config.py`, and **`.manifest.json`**
at the harness root recording `template_version`, profile
(protocol/http_client/auth), resources, and generation timestamp — fleet
tooling (`cli-web-devkit drift`) depends on it.

## Step 3: Profile Recipes

| Site profile | Flags |
|--------------|-------|
| No-auth + read-only (HN, gh-trending) | `--auth-type none` — NO auth.py, NO session.py, NO auth commands (dead code is a checklist FAIL) |
| No-auth + CRUD (Dev.to) | `--auth-type api-key` — minimal auth module, `auth set-key` |
| Cookie auth (reddit, linkedin) | `--auth-type cookie` + `--has-polling` if generation ops exist |
| Google SSO + RPC (notebooklm, stitch) | `--auth-type google-sso --protocol batchexecute` — renders `rpc/` subpackage + Google block in auth.py |
| Anti-bot protected (Cloudflare/WAF) | `--http-client curl_cffi` — see `capture/references/protection-detection.md` escalation ladder |
| Stateful apps (notebooks/projects) | add `--has-context`; UUID-keyed resources add `--has-partial-ids` |

## Step 4: Post-Scaffold Checklist

- [ ] `.manifest.json` exists at the harness root with `template_version: 2.0.0`
- [ ] `cli_web/` has NO `__init__.py`; `cli_web/<app>/` HAS one
- [ ] No unresolved Jinja2 markers (`{{`, `{%`) remain in any output file
- [ ] `FILL_IN_BASE_URL` markers noted — replace during implementation
- [ ] `auth_type=none` → no `core/auth.py`, no auth command group anywhere
- [ ] `protocol=batchexecute` → `core/rpc/` has types/encoder/decoder; otherwise `core/rpc/` does NOT exist
- [ ] One `commands/<resource>.py` exists per `--resource` flag, all registered on the CLI group
- [ ] All files pass `python -m py_compile`

Then continue with methodology/SKILL.md Step B: fill in endpoint methods in
`client.py` from `<APP>.md`, flesh out the scaffolded command modules, and
keep `_print_repl_help()` in sync (CONVENTIONS.md §REPL Rules).
