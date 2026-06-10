---
name: cross-cli-consistency-checker
version: 0.1.0
description: >
  Audit all cli-web-* CLIs for convention drift against
  skills/shared/CONVENTIONS.md, including repl_skin drift via
  `cli-web-devkit drift` and .manifest.json presence.
  Reports PASS/FAIL per check per CLI in a matrix format. Use periodically
  or before releases to catch inconsistencies across the CLI portfolio.
tools: [Read, Grep, Glob, Bash]
---

# Cross-CLI Consistency Checker

Audit all generated cli-web-* CLIs against the conventions defined in
`skills/shared/CONVENTIONS.md`.
This is a read-only audit — it reports findings but does not auto-fix.

---

## Step 1: Discover CLIs

Read `registry.json` at the repository root to get the list of all CLIs.
For each entry, note the `directory`, `namespace`, and `auth` fields.

**Fallback:** If `registry.json` doesn't exist, glob for
`*/agent-harness/cli_web/*/__init__.py` to find CLI packages.

## Step 2: Locate Reference Files

The canonical `repl_skin.py` lives in the shared runtime package:
`cli-web-core/cli_web_core/repl_skin.py` (the copy at
`cli-anything-web-plugin/scripts/repl_skin.py` is a vendored mirror synced by
`cli-web-devkit resync`). Drift detection against it is automated — see
Check 11. Also read `skills/shared/CONVENTIONS.md` for the rule definitions
behind the checks below.

## Step 3: Run Check Matrix

For each discovered CLI, run all applicable checks. Mark checks as N/A
when they don't apply (e.g., auth checks for no-auth CLIs).

### Check 1: Exception Hierarchy (Critical)

Read `core/exceptions.py` and verify:
- Base error class exists with `to_dict()` method
- All 5 subtypes present: AuthError, RateLimitError, NetworkError, ServerError, NotFoundError
- `RateLimitError` has `retry_after` field AND `to_dict()` includes it
- `ServerError` stores `status_code` as instance attribute
- `raise_for_status()` maps: 401/403→AuthError, 404→NotFoundError, 429→RateLimitError, 5xx→ServerError

**How to check:**
```
Grep for "def to_dict" in exceptions.py
Grep for "retry_after" in exceptions.py — must appear in both __init__ and to_dict
Grep for "status_code" in ServerError class
```

### Check 2: UTF-8 Fix (Critical)

Read `*_cli.py` and verify BOTH stdout AND stderr are reconfigured:
```
Grep for "stdout.reconfigure" and "stderr.reconfigure" in *_cli.py
Both must be present. Only stdout = FAIL.
```

### Check 3: REPL Parsing (Critical)

Read `*_cli.py` and verify `shlex.split` is used in the REPL loop:
```
Grep for "shlex.split" in *_cli.py — must be present
Grep for "line.split()" in *_cli.py — must NOT be present (or only in non-REPL context)
```

### Check 4: REPL Dispatch (Critical)

Read `*_cli.py` and verify REPL dispatch uses `standalone_mode=False`:
```
Grep for "standalone_mode=False" in *_cli.py
Grep for "**ctx.params" in *_cli.py — must NOT be present
```

### Check 5: Namespace Package (Critical)

Verify `cli_web/__init__.py` does NOT exist at the agent-harness level:
```
Check: {dir}/cli_web/__init__.py should NOT exist
Check: {dir}/cli_web/{app}/__init__.py SHOULD exist
```

### Check 6: handle_errors Usage (Important)

Read all `commands/*.py` files and verify they use `handle_errors()`:
```
Grep for "with handle_errors" in commands/*.py — should appear in every command function
Grep for "except.*Exception" in commands/*.py — should NOT appear (manual try/except)
```

### Check 7: No click.ClickException (Important)

```
Grep for "click.ClickException" in commands/*.py and *_cli.py
Any match = FAIL (bypasses handle_errors JSON output)
```

### Check 8: JSON Error Format (Important)

Read `core/exceptions.py` and verify `to_dict()` returns structured format:
```
Grep for '"error".*True' in exceptions.py
Grep for '"code"' in exceptions.py
```

### Check 9: Auth Env Var (Important, auth CLIs only)

```
Grep for "CLI_WEB_.*_AUTH_JSON" in config.py or auth.py
N/A for no-auth CLIs.
```

### Check 10: Auth chmod (Important, auth CLIs only)

```
Grep for "chmod" or "0o600" in auth.py
N/A for no-auth CLIs.
```

### Check 11: repl_skin.py Drift (Minor)

Use the devkit drift command — do NOT hand-diff or hash-compare files:
```bash
cli-web-devkit drift
```
Read the report: any CLI whose `utils/repl_skin.py` is flagged as diverged
from the canonical `cli-web-core/cli_web_core/repl_skin.py` = FAIL (stale
copy — remediation: `cli-web-devkit resync <app>`).

Fallback only if `cli-web-devkit` is not installed:
```bash
diff {cli_dir}/utils/repl_skin.py cli-web-core/cli_web_core/repl_skin.py
```

### Check 12: Google Cookie Domain Priority (Important, google-sso CLIs only)

For CLIs with Google SSO auth, verify that `.google.com` cookies take
priority over regional ccTLD duplicates (`.google.co.il`, `.google.de`, etc.):
```
Read core/auth.py
Look for cookie domain priority logic — sorting or filtering that prefers
.google.com over regional domains
If auth uses Google SSO but no domain priority logic exists → FAIL
N/A for non-Google-SSO CLIs.
```

### Check 13: setup.py Namespaces (Important)

```
Grep for 'find_namespace_packages' in setup.py
Grep for 'include=\["cli_web\.\*"\]' in setup.py
```

### Check 14: Manifest Presence (Important)

Every harness must carry generation provenance for fleet drift tooling:
```
Check: {dir}/.manifest.json exists
Parse it as JSON; it must include the template/generator version and the
profile fields (protocol, http_client, auth).
Missing or unparseable = FAIL — the CLI is invisible to cli-web-devkit drift.
Remediation: re-scaffold metadata via scaffold-cli.py (v2) or
cli-web-devkit resync <app>.
```

## Step 4: Output Report

Format as a matrix table:

```
Cross-CLI Consistency Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━
                  ExcH  UTF8  REPL  Disp  NS    HErr  NoClk JSON  Auth  Chmd  Cook  Skin  Setup Mnfst
futbin            PASS  FAIL  PASS  PASS  PASS  PASS  PASS  PASS  N/A   N/A   N/A   FAIL  PASS  PASS
reddit            PASS  PASS  PASS  PASS  PASS  FAIL  FAIL  PASS  PASS  PASS  N/A   PASS  PASS  FAIL
...

Legend: ExcH=Exception Hierarchy, UTF8=UTF-8 Fix, REPL=shlex.split, Disp=REPL Dispatch,
        NS=Namespace Package, HErr=handle_errors, NoClk=No click.ClickException,
        JSON=JSON Error Format, Auth=Auth Env Var, Chmd=Auth chmod, Cook=Cookie Domain Priority,
        Skin=repl_skin drift (devkit), Setup=setup.py namespaces, Mnfst=.manifest.json presence

Summary: X Critical, Y Important, Z Minor findings across N CLIs

Critical Issues:
  [CLI]: [check name] — [description] ([file:line])
  ...

Important Issues:
  [CLI]: [check name] — [description] ([file:line])
  ...

Minor Issues:
  [CLI]: [check name] — [description] ([file:line])
  ...
```
