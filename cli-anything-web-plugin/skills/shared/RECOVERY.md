# RECOVERY.md — Failure Decision Trees for Pipeline Gates

When a hard gate fails, come here. Each section is a decision tree: identify
the failure signature, apply the targeted remediation, and bound your retries.
Never improvise retry loops — every tree below has an explicit retry budget.

## Contents

- §tracing-stop Failure
- §parse-trace Failure
- §validate-capture Non-Zero Exit
- §phase-state Check Failures
- §scaffold-cli.py Unavailable

---

## §tracing-stop Failure

```
tracing-stop fails
├── 1st failure → retry ONCE with a 15s timeout
├── 2nd failure → the trace is LOST (session reconnected and dropped state)
│     ├── Do NOT retry again (budget: 2 attempts total)
│     ├── Do NOT try to parse partial files in .playwright-cli/traces/
│     └── Restart the trace at capture/SKILL.md Step 3:
│           tracing-start → re-do the exploration actions → tracing-stop
└── tracing-stop HANGS → browser process died:
      npx @playwright/cli@latest kill-all → reopen session → fresh trace
```

Common error signatures and causes:
`"Cannot read properties of undefined (reading 'tracesDir')"` = session
reconnected, lost trace state → start new trace. Full table:
`skills/capture/references/playwright-cli-tracing.md` "Trace Recovery Protocol".

---

## §parse-trace Failure

```
parse-trace.py exits non-zero or produces empty raw-traffic.json
├── ".network file missing" → trace never completed → restart trace (Step 3)
├── ".network file empty" → trace too short / no API activity
│     └── Re-trace with MORE interactions (clicks, form submits, navigation)
├── "no traces found" → wrong directory — pass `.playwright-cli/traces/ --latest`
│     (relative to where the browser session was opened)
└── Parses but raw-traffic.json has only static assets (no JSON/API entries)
      └── The app may render server-side or in an iframe:
          re-run the site fingerprint, check `iframeCount`, and use the
          SPA-navigation trick (capture/SKILL.md Step 2c) to force API calls
```

If the trace is unrecoverable twice in a row, switch capture method:
`--mitmproxy` mode (no truncation, proxy-level capture) or the
chrome-devtools-mcp fallback (HARNESS.md Tool Hierarchy).

---

## §validate-capture Non-Zero Exit

`validate-capture.py` prints per-gate results. Map each FAILED gate to its
remediation, re-open the browser (capture Step 1), fill the gap, then re-run
Step 4. Do NOT proceed to Phase 2 with a failing validator.

| Gate | Failure | Targeted remediation |
|------|---------|---------------------|
| `entry_count` | < 15 entries | Browsing too shallow — capture MORE pages: navigate every main section, paginate lists, open detail views |
| `endpoint_diversity` | < 3 distinct URL paths | Exercise more FEATURES, not more of the same page: search, filters, detail pages, settings — each feature = new endpoints |
| `protocol` | `unknown` | Analyzer couldn't classify — check API traffic visibility: is the app SSR-only (use SPA-navigation trick, Step 2c)? In an iframe (re-run fingerprint inside it)? Bodies truncated (switch to `--mitmproxy`)? |
| `write_ops` | no POST/PUT/PATCH/DELETE | Perform an actual create/update/delete IN THE UI (submit a form, rename an item, delete a test item). If the site is genuinely read-only, re-run with `--read-only` — but only after confirming the UI truly has no write actions |
| `error_rate` | > 50% responses 4xx/5xx | Capture was broken — check auth: did the session expire mid-capture? Re-login, `state-save` again, re-trace. If errors are 429s, slow down (1–2 s between clicks) |
| `body_fidelity` | WARN: < 30% of API responses have bodies | Likely truncation — re-capture with `--mitmproxy` mode (no body truncation) |

WARN-level results don't block, but each warning needs your explicit sign-off
before marking Phase 1 complete.

---

## §phase-state Check Failures

`phase-state.py check <app> --phase <phase>` exits 0 = skip (done), 1 = run.
When `status` shows a phase as `failed`, branch on `error_type`:

```
phase failed
├── error_type == "retryable" (flaky network, rate limit, transient test fail)
│     └── Retry the phase automatically — ONCE. If it fails again with the
│         same error, escalate to fatal handling.
├── error_type == "fatal" (missing prerequisite, auth broken, site blocked)
│     └── Do NOT auto-retry. Report the recorded error to the user and ask
│         how to proceed. Fix the root cause, then:
│         python ${CLAUDE_PLUGIN_ROOT}/scripts/phase-state.py reset <app> --phase <phase>
└── state file corrupt / inconsistent with reality (e.g., says capture done
    but raw-traffic.json is missing)
      └── Trust the filesystem, not the state: reset the phase and re-run.
```

Use `run-pipeline.py status <app-dir>` for human-facing next-action guidance;
mutate state only via `phase-state.py complete|fail|reset`.

For interrupted *capture sessions* specifically, also check
`capture-checkpoint.py restore <app>` and resume from the last completed step
rather than restarting Phase 1.

---

## §scaffold-cli.py Unavailable

If `scaffold-cli.py` cannot run (missing jinja2 after an install attempt,
plugin scripts inaccessible, irrecoverable error):

1. **Do NOT reconstruct files from memory or from a boilerplate dump.**
2. **Fallback: adapt from the NEWEST generated CLI** — currently
   `capitoltrades/agent-harness/` — it matches the current templates. Copy its
   `core/exceptions.py`, `core/client.py`, `utils/helpers.py`,
   `utils/output.py`, `<app>_cli.py`, and `setup.py`, then rename
   app identifiers and strip endpoint methods.
3. Pick the closest protocol match for `client.py` if capitoltrades doesn't
   fit (see methodology/SKILL.md "Study Existing CLIs First" table).
4. Copy `utils/repl_skin.py` verbatim from any current CLI (canonical source:
   `cli-web-core/cli_web_core/repl_skin.py`).
5. Verify the result against CONVENTIONS.md (exceptions, JSON envelope, REPL
   rules) and note in `<APP>.md` that the CLI was scaffolded manually —
   no `.manifest.json` will exist, so flag it for later
   `cli-web-devkit resync`.

First, though, try to fix the script itself: `pip install jinja2`, and check
`python ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold-cli.py --help` for the actual
error before falling back.
