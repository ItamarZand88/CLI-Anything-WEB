---
name: testing
version: 0.3.0
description: >
  Writes and documents the test suite for a generated cli-web-* CLI (Phase 3): unit
  tests with mocked HTTP, live E2E tests, subprocess tests via _resolve_cli, and the
  TEST.md plan/results record. Use after the methodology skill completes
  implementation.
when_to_use: >
  Trigger phrases: "write tests for cli-web-*", "start Phase 3", "create TEST.md",
  "add E2E tests", "add subprocess tests", "test the CLI". Not for traffic capture,
  implementation, or quality validation (standards).
---

# CLI-Anything-Web Testing

Write and document tests for cli-web-* CLIs. This skill owns the full testing
lifecycle: test implementation and test documentation (plan + results).

Copy this checklist and check off items as you complete them:

```
Phase 3 Progress:
- [ ] Prerequisites: implementation complete, CLI installed, <APP>.md exists
- [ ] Auth verified working (auth login + status) — auth CLIs only
- [ ] Unit tests written (mocked HTTP, typed-exception + helper coverage)
- [ ] E2E tests written (live round-trips, FAIL not skip on missing auth)
- [ ] Subprocess tests written (_resolve_cli pattern)
- [ ] TEST.md Part 1 generated (generate-test-docs.py plan)
- [ ] Full suite green incl. CLI_WEB_FORCE_INSTALLED=1 subprocess run
- [ ] TEST.md Part 2 appended (generate-test-docs.py results)
- [ ] phase-state marked complete
```

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] Implementation is complete (all core modules + commands exist)
- [ ] `pip install -e .` succeeds and `cli-web-<app>` is on PATH
- [ ] `<APP>.md` exists with API map and auth scheme

If implementation is incomplete, invoke the `methodology` skill first. If the
methodology phase is marked `failed` in phase-state, follow
`skills/shared/RECOVERY.md` §phase-state Check Failures.

---

## Auth Must Be Working Before E2E Tests

For auth-required sites: run `cli-web-<app> auth login` then `auth status` (must show valid).
Tests that skip or catch auth errors are broken — use `pytest.fail()` if auth is missing
(CONVENTIONS.md §Auth Rules "Tests"). No-auth sites skip auth setup entirely.

---

## Write Tests

**Goal:** Comprehensive test suite. Document what you're testing as you write it —
TEST.md Part 1 (the plan) is written alongside the test code, not as a separate
gate before it.

### Testing Layer Strategy

The standard three-layer suite is: **unit tests (mocked HTTP)** + **live E2E tests** +
**subprocess tests**. This covers fast correctness, real integration, and installed CLI.

| Layer | File | Purpose |
|-------|------|---------|
| Unit | `test_core.py` | Core functions with mocked HTTP. No network. Fast. |
| E2E live | `test_e2e.py` | Real API calls. Require auth — FAIL (not skip) without it. |
| CLI subprocess | `test_e2e.py` | Installed `cli-web-<app>` via `_resolve_cli()`. Full end-to-end. |
| Integration (VCR) | `test_integration.py` | Recorded HTTP cassettes via VCR.py. Reproducible, no network. Recommended for RPC protocols. |

**Optional — fixture replay layer:** Only add this if the site has complex HTML
parsing or non-trivial response transformations worth preserving. For straightforward
JSON APIs, fixture replay adds maintenance cost without much benefit.

| Layer (optional) | File | Purpose |
|-----------------|------|---------|
| E2E fixture | `test_e2e.py` | Replay captured responses from `tests/fixtures/`. Verifies parsing logic. |

### Parallel Test Writing

Dispatch `test_core.py` and `test_e2e.py` writing as parallel subagents — they're
independent. Start unit tests during Phase 2 if possible (they don't depend on commands).

### Testing Rules

- Unit tests: `unittest.mock.patch` for HTTP, real CSS class names in HTML fixtures
- E2E: require auth (pytest.fail if missing), verify response body fields not just status
- Subprocess: `_resolve_cli("cli-web-<app>")` — see `references/resolve-cli-pattern.md`
- HTML scraper assertions: check actual fields (name, id, price), not just `isinstance(results, list)`
- See `references/test-code-examples.md` for patterns

### VCR.py Integration Tests (Recommended for RPC/GraphQL)

For complex protocols, add a recorded-cassette layer between unit and live
E2E — real responses, replayed offline. Setup, recording workflow, and the
marker convention: `references/vcr-testing.md`.

### Fixture Realism (for HTML scrapers)

If the CLI uses HTML scraping (BeautifulSoup, lxml), unit test fixtures must mirror
the real page's CSS class structure — not a generic simplified table.

A fixture like `<table><tr><td>GK</td><td>95</td></tr></table>` will pass even if
the real parser is completely broken against the live site's actual markup. The parser
was written to match specific CSS classes (`table-player-name`, `platform-ps-only`,
`table-pos-main`) — the fixture must have those same classes.

When to apply this: any CLI module that calls `.find(class_=...)` or `.find_all(...)`
on response HTML. If the module only parses JSON (`resp.json()`), skip this — JSON
fixtures are naturally structural.

Practical check: look at your parser's `.find(class_="...")` calls. If your fixture
HTML doesn't contain those exact class names, the fixture is not testing the parser.

### CLI Output Sanity Checks (Critical)

Every `--json` output must be checked for raw protocol leakage. These are bugs
the agent MUST catch before declaring tests pass:

```python
# In E2E tests, assert the output is real data, not raw RPC fragments:
def test_chat_returns_text_not_rpc(client, notebook_id):
    """Chat answer must be human-readable text, not raw batchexecute chunks."""
    result = client.chat_query(notebook_id, "What is this about?")
    # RED FLAGS — fail if any of these appear in the answer:
    assert "wrb.fr" not in result, "Raw RPC data leaked into chat output"
    assert "af.httprm" not in result, "Raw RPC data leaked into chat output"
    assert '"di"' not in result, "Raw RPC data leaked into chat output"
    assert len(result) > 50, "Answer too short — may be empty or error"

def test_sources_list_after_add(client, notebook_id):
    """Sources must appear in list after being added."""
    source = client.add_url_source(notebook_id, "https://example.com")
    import time; time.sleep(5)  # Wait for indexing
    sources = client.list_sources(notebook_id)
    assert len(sources) > 0, "Sources list empty after add — check GET_NOTEBOOK params"
    assert any(s.id == source.id for s in sources), "Added source not in list"
```

**Subprocess test equivalent:**
```python
def test_cli_chat_output_is_text(self):
    """CLI chat --json output must contain readable answer, not raw RPC."""
    result = subprocess.run(
        [cli, "chat", "ask", "--query", "test", "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    data = json.loads(result.stdout)
    assert "wrb.fr" not in data.get("answer", ""), "Raw RPC leaked"
    assert len(data.get("answer", "")) > 20, "Answer suspiciously short"
```

### Response Body Verification

Verify response bodies for every CRUD operation — status 200 alone is insufficient.
Create → check fields match, Read → check ID matches, Delete → verify 404 on re-read.

### Exception Testing

Unit tests MUST verify that the client raises the correct typed exceptions — without
these assertions, a client that always raises generic `Exception` would pass the suite:

```python
# test_core.py
def test_auth_error_on_401(mock_client):
    """Client raises AuthError on 401, not generic exception."""
    with pytest.raises(AuthError) as exc_info:
        mock_client.notebooks.list()  # mocked to return 401
    assert exc_info.value.recoverable is True

def test_rate_limit_error_on_429(mock_client):
    """Client raises RateLimitError with retry_after on 429."""
    with pytest.raises(RateLimitError) as exc_info:
        mock_client.notebooks.list()  # mocked to return 429
    assert exc_info.value.retry_after == 60

def test_json_error_output(cli_runner):
    """--json mode outputs structured error, not plain text."""
    result = cli_runner.invoke(cli, ["--json", "notebooks", "get", "nonexistent"])
    data = json.loads(result.output)
    assert data["error"] is True
    assert "code" in data
```

### Helper Function Testing

Unit tests cover the shared helpers in `utils/helpers.py` — every command
routes through them, so a bug here silently breaks the whole CLI. Required
coverage: partial-ID resolution (unique prefix, ambiguous raises), filename
sanitization, persistent context set/get, and `handle_errors` exit codes.
Complete code patterns: `references/test-code-examples.md` §Helper tests.

#### handle_errors exit codes (contract)

CLIs scaffolded from template v2.1+ map domain errors to the numeric
exit-code contract (CONVENTIONS.md §Exit Codes) — assert the contract:

```python
def test_handle_errors_auth_exit_code():
    with pytest.raises(SystemExit) as exc:
        with handle_errors():
            raise AuthError("expired")
    assert exc.value.code == 3      # EXIT_AUTH

def test_handle_errors_unknown_exit_code():
    with pytest.raises(SystemExit) as exc:
        with handle_errors():
            raise ValueError("bug")
    assert exc.value.code == 1      # EXIT_UNKNOWN
```

CLIs generated before template v2.1 use the legacy codes (domain=1,
unexpected=2) — assert whatever the CLI's own `helpers.py` implements; do
not change a legacy CLI's exit codes from a test.

### Round-Trip Test Requirement

Every E2E live test MUST include at minimum a create-read-verify round-trip —
a test that only creates without reading back cannot detect silent data loss or
malformed request bodies:

```
create entity -> read it back -> verify fields match -> update ->
verify update -> delete -> verify 404 on read
```

Tests that only create without reading back give false confidence.

**For read-only CLIs:** The round-trip becomes: list resources → get one by ID →
verify fields match between list and detail views. No create/update/delete
round-trip is needed.

### The `_resolve_cli` Pattern

The subprocess test rule is defined in
`skills/shared/CONVENTIONS.md` §Subprocess Test Rule (`_resolve_cli`, no `cwd`,
`CLI_WEB_FORCE_INSTALLED=1`, UTF-8 subprocess encoding). The complete helper
function and `TestCLISubprocess` class are in
`references/resolve-cli-pattern.md`.

### TEST.md Part 1 — Write As You Go

After writing all tests, generate the test plan automatically:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/generate-test-docs.py plan \
  <app>/agent-harness/cli_web/<app>/tests/ --app-name <app>
```

This parses test files via AST and creates TEST.md Part 1 with test inventory,
class breakdowns, and method listings. Review and enhance the generated plan
with additional context:

1. **Test Inventory** — List test files and actual test counts
2. **Unit Test Plan** — For each core module: functions tested, edge cases covered
3. **E2E Test Plan** — Live CRUD workflows and what is verified
4. **Realistic Workflow Scenarios** — Multi-step flows with verification criteria:
### Handling Client-Side Operations in E2E Tests

Some batchexecute/RPC operations are **client-side** — the browser generates
the ID and the API just acknowledges (returns null). Common for
project/document creation in Google apps.

- **Detect:** `create_X()` returned None during the methodology smoke check.
- **Test instead:** operations that work via RPC (delete with a safe target,
  list-diff create), and `pytest.skip` with the reason when create is
  browser-only. Code patterns: `references/test-code-examples.md`
  §Client-side operations.
- **Document in TEST.md** which operations are client-side and untestable
  via E2E.

---

## Run & Verify

1. **Verify auth is working FIRST:**
   ```bash
   cli-web-<app> auth login              # opens browser via Python playwright
   cli-web-<app> auth status             # must show live validation: OK
   ```
   If auth status fails, fix it before proceeding.

2. Run full test suite: `python -m pytest cli_web/<app>/tests/ -v --tb=short`

3. Run subprocess tests: `CLI_WEB_FORCE_INSTALLED=1 python -m pytest cli_web/<app>/tests/ -v -s -k subprocess`

4. **ALL tests must pass.** If E2E tests fail with auth errors, go back to step 1.
   Do NOT record "auth not configured" as a test result — that means auth is broken.

---

## Document Results in TEST.md

**Goal:** Append test results to TEST.md (Part 2).

Part 2 is **appended** to the existing Part 1. Never overwrite.

Generate Part 2 automatically after all tests pass:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/generate-test-docs.py results \
  <app>/agent-harness/cli_web/<app>/tests/ --app-name <app>
```

This runs pytest, captures output, and appends Part 2 with summary metrics and
raw output. Review the generated results for accuracy.

Include example CLI usage in README.md.

### Failure Handling

When tests fail:
1. Show failures with full pytest output
2. Do NOT update TEST.md — it should only contain passing results
3. Analyze and suggest specific fixes
4. Offer to re-run after fixes

---

## Next Step

When all tests pass, mark phase complete and invoke the `standards` skill:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/phase-state.py complete <app> --phase testing
```

References: `resolve-cli-pattern.md`, `test-code-examples.md`
