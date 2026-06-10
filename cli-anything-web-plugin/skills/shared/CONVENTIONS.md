# CONVENTIONS.md — Implementation Rules (Single Source of Truth)

This file is the ONLY place where cli-web-* implementation rules are *defined*.
HARNESS.md, the phase skills, the review agents, and the commands *reference*
these sections — they must never restate a rule with different wording.
Reference format: `CONVENTIONS.md §<section>` (e.g., "see CONVENTIONS.md §Auth Rules").

Machine enforcement: most rules here are checked by
`scripts/validate-checklist.py` (Tier 1 = blocks publish), the Phase 4 review
agents, and the fleet contract suite at `tests/contract/`.

---

## §Naming Conventions

| Convention | Value |
|-----------|-------|
| CLI command | `cli-web-<app>` |
| Python namespace | `cli_web.<app>` |
| App-specific SOP | `<APP>.md` (at `agent-harness/` root) |
| Plugin slash command | `/cli-anything-web` |
| Traffic capture dir | `<app>/traffic-capture/` |
| Auth config dir | `~/.config/cli-web-<app>/` |
| Auth env var | `CLI_WEB_<APP>_AUTH_JSON` (UPPER_SNAKE of app name) |
| App names | No hyphens. Underscores OK (`monday_com`) |
| Entry point | `cli-web-<app>=cli_web.<app>.<app>_cli:main` |

Namespace packaging: `cli_web/` has NO `__init__.py` (namespace package);
`cli_web/<app>/` HAS `__init__.py` (sub-package). `setup.py` uses
`find_namespace_packages(include=["cli_web.*"])` and `python_requires=">=3.10"`.

---

## §Exception Hierarchy

Every CLI MUST have `core/exceptions.py` with a typed domain hierarchy —
never generic `RuntimeError`/`Exception`:

```
<App>Error (base, has to_dict())
├── AuthError(recoverable: bool)        # 401/403
├── RateLimitError(retry_after: float)  # 429 — to_dict() includes retry_after
├── NetworkError                        # DNS / TCP / TLS / timeout
├── ServerError(status_code: int)       # 5xx
├── NotFoundError                       # 404
└── RPCError                            # non-REST decode failures
```

Rules:
- The base class has `to_dict()` returning the §JSON Error Envelope.
- `RateLimitError.to_dict()` includes `retry_after`; `ServerError` stores
  `status_code` as an instance attribute.
- A module-level `raise_for_status(response)` maps HTTP status → exception:
  401/403 → `AuthError(recoverable=True)`, 404 → `NotFoundError`,
  429 → `RateLimitError` (parse `Retry-After` header), 5xx → `ServerError`.
- Commands never raise `click.ClickException` — it bypasses `handle_errors()`
  and breaks `--json` error output.
- Rendered by `templates/exceptions.py.tpl`; full example in
  `skills/methodology/references/exception-hierarchy-example.py`.

### Error code mapping

| Exception | JSON `code` |
|-----------|-------------|
| `AuthError` | `AUTH_EXPIRED` |
| `RateLimitError` | `RATE_LIMITED` |
| `NotFoundError` | `NOT_FOUND` |
| `ServerError` | `SERVER_ERROR` |
| `NetworkError` | `NETWORK_ERROR` |
| `RPCError` | `RPC_ERROR` |
| anything else | `INTERNAL_ERROR` / `UNKNOWN_ERROR` |

---

## §JSON Envelope

Every command supports `--json` (on each command, not just the group).
Output in `--json` mode MUST be a single parseable JSON document:

```python
# Success:
{"success": true, "data": {...}}

# Error (yes — errors are JSON too, never plain text to stderr in --json mode):
{"error": true, "code": "AUTH_EXPIRED", "message": "Session expired. Run: cli-web-<app> auth login"}
{"error": true, "code": "RATE_LIMITED", "message": "Rate limited. Retry after 60s", "retry_after": 60}
{"error": true, "code": "NOT_FOUND", "message": "Notebook abc123 not found"}
```

Rules:
- `code` values come from the §Exception Hierarchy mapping table.
- Error messages include actionable guidance (what command to run next).
- All commands wrap their body in the `handle_errors(json_mode)` context
  manager (in `utils/helpers.py`) — no per-command try/except.
- Rich spinners/progress are suppressed in `--json` mode.
- Implemented via `utils/output.py` `json_success()` / `json_error()`
  (rendered by `templates/output.py.tpl`).
- **List commands also offer `--jsonl`** — one compact JSON object per
  line (no envelope) for `jq`/`grep`/agent-loop piping. Implemented via
  `utils/output.py` `json_lines()`; scaffolded by `command_group.py.tpl`.

---

## §Exit Codes

Numeric exit-code contract so scripts and agents can branch on `$?`
without parsing output (canonical map: `cli_web_core.exceptions`):

| Code | Meaning | Source |
|------|---------|--------|
| 0 | success | — |
| 1 | unknown / internal error | any unmapped exception |
| 2 | usage error | Click's own convention (bad flags/args) |
| 3 | auth failure | `AuthError` (after the 3-attempt refresh) |
| 4 | not found | `NotFoundError` |
| 5 | rate limited | `RateLimitError` |
| 6 | server error (5xx) | `ServerError` |
| 7 | network failure | `NetworkError` |
| 130 | interrupted | Ctrl-C |

`handle_errors()` (rendered by `templates/helpers.py.tpl`) applies the
mapping automatically — newly generated CLIs get this for free.

> **Fleet note:** CLIs generated before template v2.1 exit 1 for domain
> errors and 2 for unexpected errors. Changing their observable exit codes
> is a breaking change — they adopt this contract at their next
> coordinated major release, not via resync.

---

## §Auth Rules

Apply only when `auth_type != none`. No-auth sites must NOT have `auth.py`,
`session.py`, or auth command groups — they are dead code, not "optional".

### Storage
- Credentials live at `~/.config/cli-web-<app>/auth.json` with `chmod 600`
  (or `os.chmod(path, 0o600)`). Never hardcode tokens, API keys, session IDs,
  CSRF tokens, or build labels — extract dynamically at runtime.
- Env var fallback for CI/CD: `CLI_WEB_<APP>_AUTH_JSON` contains the auth JSON
  as a string; checked before reading the file.

### 3-Attempt Auto-Refresh (MANDATORY for auth-required CLIs)

Session cookies expire. On 401/403 the client (`client.py:_request()`) runs
exactly this sequence — never more attempts:

| Attempt | Action |
|---------|--------|
| 0 | Try with current in-memory cookies |
| 1 | Reload `auth.json` from disk (another process may have refreshed it) |
| 2 | Headless refresh via `auth.py:refresh_auth()` |

If all 3 fail → `AuthError("Session expired. Run: cli-web-<app> auth login")`.

Google SSO nuance: attempt 2 re-extracts rotated tokens (CSRF/session ID) over
HTTP using the existing cookies. When the *cookies themselves* have expired, no
headless re-login exists — Google blocks headless browsers — so attempt 2 fails
fast and the user is told to run `auth login` (headed browser). See
`skills/methodology/references/auth-strategies.md` "Auth refresh: two layers".

The unified `templates/auth.py.tpl` and `templates/client_rest_*.py.tpl`
generate this by default. Reference implementations: `reddit/core/auth.py`,
`linkedin/core/auth.py`.

### Browser Login
`login_browser()` MUST use Python `sync_playwright()` with
`launch_persistent_context()` — never `npx @playwright/cli` (interactive input
race on Windows). Include the Windows event-loop fix
(`asyncio.DefaultEventLoopPolicy()`), anti-automation args, and (for Google)
regional cookie forcing — navigate to `accounts.google.com` then back after
login. Full code: `auth-strategies.md` "Browser-Delegated Auth".

### Cookie Domain Priority (Google apps — #1 international-user bug)
`.google.com` cookies MUST take priority over regional duplicates
(`.google.co.il`, `.google.de`, ...). Naive `{c["name"]: c["value"]}`
flattening is BROKEN — the last (regional) value wins and auth fails outside
the US. Use the priority extractor in `auth-strategies.md` "Cookie domain
priority".

### Cookie Format Handling
`load_cookies()` must handle BOTH formats the auth file can contain:
- raw playwright list: `[{"name": ..., "value": ..., "domain": ...}, ...]`
- extracted dict: `{"SID": "...", ...}`

Check `isinstance(cookies, list)` and convert with domain priority.

### Tests
Tests FAIL (`pytest.fail()`) when auth is missing — never skip. "auth not
configured" is a broken test result, not a pass.

---

## §REPL Rules

REPL is the default mode: the group uses
`@click.group(invoke_without_command=True)` and drops into the REPL when no
subcommand is given. The REPL UI comes from `utils/repl_skin.py` — a vendored
copy whose canonical source is `cli-web-core/cli_web_core/repl_skin.py`
(synced by `cli-web-devkit resync`; do not hand-edit per-CLI copies).

1. **Parse lines with `shlex.split(line)`** — never `line.split()`. Quoted
   args must parse: `players search "lionel messi"` → `['players', 'search',
   'lionel messi']`.

2. **Propagate `--json` by PREPENDING it to the args list** — never pass
   `**ctx.params` to `cli.main()` (Click's `Context.__init__()` rejects
   unknown kwargs → `TypeError`):

   ```python
   repl_args = ["--json"] + args if ctx.obj.get("json") else args
   cli.main(args=repl_args, standalone_mode=False)
   ```

3. **Help-sync rule**: `_print_repl_help()` must mirror the real command
   surface, including key options. Every commit that adds a command or option
   updates `_print_repl_help()` in the same commit.

4. **Positional params use `@click.argument`**, not
   `@click.option("--x", required=True)`. Users type `players search messi`,
   not `players search --query messi`. Options are for optional/named
   parameters only.

Context commands for stateful apps (notebooks, projects, boards):
`use <id>` persists to `~/.config/cli-web-<app>/context.json`; `status` shows
the active context; resource-scoped flags (e.g., `--notebook`) become optional
when context is set (via `require_notebook()`).

---

## §Exponential Backoff & Polling

Operations taking >2 seconds MUST poll with exponential backoff — never fixed
`time.sleep()` loops:

- Polling: initial 2s → cap 10s, factor 1.5, total timeout 300s
  (`poll_until_complete()` in `utils/helpers.py`).
- Rate-limit retry: on 429 honor `Retry-After`, else back off 60s → 300s.
- Generation commands support `--wait` (poll until complete), `--retry N`
  (rate-limit retry budget), and `--output <path>` (save artifact to file).
- Show Rich progress feedback for long operations when not in `--json` mode.

Full patterns: `skills/methodology/references/polling-backoff-example.py`.

---

## §Windows UTF-8 Fix

`<app>_cli.py` forces UTF-8 on BOTH stdout AND stderr before any import that
prints (API responses contain emoji/non-ASCII that crash cp1252):

```python
import sys
for stream in (sys.stdout, sys.stderr):
    if stream.encoding and stream.encoding.lower() not in ("utf-8", "utf8"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
```

Stdout-only is a FAIL — error paths print to stderr. In subprocess tests,
always pass `encoding="utf-8", errors="replace"` to `subprocess.run()`.

---

## §Subprocess Test Rule

E2E suites include a `TestCLISubprocess` class that exercises the *installed*
CLI binary:

- Resolve the binary with `_resolve_cli("cli-web-<app>")` — never hardcode
  module paths. Pattern: `skills/testing/references/resolve-cli-pattern.md`.
- The `_run` helper must NOT set `cwd` — installed commands work from any
  directory.
- `CLI_WEB_FORCE_INSTALLED=1` forces resolution to the installed command
  (use in CI); the test fails if the binary is not on PATH.
- Verify the line `[_resolve_cli] Using installed command:` appears — it
  confirms the installed package was tested, not a source fallback.

---

## §Protocol-Leak Smoke Check

After implementing any command, run it with `--json` and inspect the output.
Red flags that mean the decoder/parser is broken — fix before proceeding:

| Symptom | Diagnosis |
|---------|-----------|
| `wrb.fr`, `af.httprm` in output | Raw batchexecute chunks leaked — decoder broken |
| `[]` / `null` where data expected | Wrong params, or operation is client-side |
| Wrong field values (e.g., `"3"` instead of prompt text) | Parser index mismatch |
| Empty fields the site visibly displays | Incomplete HTML parser — extract ALL visible columns |
| Plain-text error in `--json` mode | §JSON Envelope violated |

Automated check: `scripts/smoke-test.py cli-web-<app> --auth-type <type>`.
E2E tests assert these red flags never appear (see testing skill "CLI Output
Sanity Checks").

---

## §Generated CLI Structure (summary)

Canonical layout lives in HARNESS.md "Generated CLI Structure". Invariants:
`core/` (exceptions, client, auth*, session*, models, optional `rpc/`),
`commands/` (one file per resource group), `utils/` (helpers, repl_skin,
output, config), `tests/` (TEST.md, test_core.py, test_e2e.py), plus
`setup.py`, `<APP>.md`, `README.md` at the harness root and a `.manifest.json`
provenance file written by `scaffold-cli.py` (template version, profile,
generated-at — consumed by `cli-web-devkit drift`).

*Auth files only when `auth_type != none`; `session.py` only for stateful apps.
