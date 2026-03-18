---
name: testing
description: >
  Write and document tests for cli-web-* CLIs. Covers writing the test suite
  (unit + E2E + subprocess), documenting what is tested as you go, and recording
  results in TEST.md. Use when writing tests for web API wrappers, setting up
  pytest for HTTP-based CLIs, creating TEST.md files, writing E2E tests, implementing
  subprocess tests with _resolve_cli, or when working on the testing phase of the
  cli-anything-web pipeline.
version: 0.2.0
---

# CLI-Anything-Web Testing

Write and document tests for cli-web-* CLIs. This skill owns the full testing
lifecycle: test implementation and test documentation (plan + results).

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] Implementation is complete (all core modules + commands exist)
- [ ] `pip install -e .` succeeds and `cli-web-<app>` is on PATH
- [ ] `<APP>.md` exists with API map and auth scheme

If implementation is incomplete, invoke the `methodology` skill first.

---

## Auth MUST Be Working Before Any E2E Test

This is the #1 rule for web CLI testing. Before writing or running any E2E test:

1. Ensure playwright-cli is available (`npx @playwright/cli@latest --version`)
2. Run `cli-web-<app> auth login` (playwright-cli state-save)
3. Run `cli-web-<app> auth status` — must show valid
4. If auth fails, STOP and fix it. Do NOT write tests that catch auth errors.

Tests that output "auth not configured" or skip on missing auth are **broken tests**.
The web app requires authentication — the tests must authenticate. This is the web
equivalent of CLI-Anything's rule that the real software must be installed.

If a test cannot authenticate, it must call `pytest.fail()` with a message telling
the user to run `auth login`, not silently skip or catch the error.

---

## Write Tests

**Goal:** Comprehensive test suite. Document what you're testing as you write it —
TEST.md Part 1 (the plan) is written alongside the test code, not as a separate
gate before it.

### Testing Layer Strategy

The standard two-layer suite is: **unit tests (mocked HTTP)** + **live E2E tests** +
**subprocess tests**. This covers fast correctness, real integration, and installed CLI.

| Layer | File | Purpose |
|-------|------|---------|
| Unit | `test_core.py` | Core functions with mocked HTTP. No network. Fast. |
| E2E live | `test_e2e.py` | Real API calls. Require auth — FAIL (not skip) without it. |
| CLI subprocess | `test_e2e.py` | Installed `cli-web-<app>` via `_resolve_cli()`. Full end-to-end. |

**Optional — fixture replay layer:** Only add this if the site has complex HTML
parsing or non-trivial response transformations worth preserving. For straightforward
JSON APIs, fixture replay adds maintenance cost without much benefit.

| Layer (optional) | File | Purpose |
|-----------------|------|---------|
| E2E fixture | `test_e2e.py` | Replay captured responses from `tests/fixtures/`. Verifies parsing logic. |

### Parallel Test Writing (dispatch independent test files as subagents)

Test files are independent and can be written in parallel:

| Test file | Scope | Independent? |
|-----------|-------|-------------|
| `test_core.py` — client tests | Mock HTTP, test `client.py` | Yes |
| `test_core.py` — auth tests | Mock filesystem, test `auth.py` | Yes |
| `test_core.py` — RPC codec tests | Test encoder/decoder with fixtures | Yes |
| `test_e2e.py` — live tests | Real API calls | Depends on auth working |
| `test_e2e.py` — subprocess tests | `_resolve_cli()` | Depends on `pip install -e .` |

Dispatch strategy:
```
Agent 1 -> "Write unit tests for core/client.py and core/auth.py in test_core.py"
Agent 2 -> "Write RPC encoder/decoder unit tests (if applicable) in test_core.py"
Agent 3 -> "Write live E2E CRUD tests and subprocess tests in test_e2e.py"
# After all return, integrate into final test files and run
```

Each agent receives: the module it's testing, and sample API responses if available.
Agents must NOT depend on each other's output.

### Testing Rules

- Use `unittest.mock.patch` for HTTP in unit tests
- Store captured responses in `tests/fixtures/` for replay (if using fixture layer)
- E2E live tests require auth — **FAIL (not skip, not catch, not "auth not configured")**
- If a test cannot authenticate, it must `pytest.fail("Auth not configured. Run: cli-web-<app> auth login")`
- `TestCLISubprocess` using `_resolve_cli("cli-web-<app>")`
- Target: >80% coverage on core modules
- **HTML scrapers:** unit test fixtures must use the real CSS class names the parser targets, not generic simplified markup. If the fixture doesn't have the classes, it's not testing the parser. See `references/test-code-examples.md`.
- **List/search assertions:** `assert isinstance(results, list)` doesn't catch broken parsers. When results have fields (name, id, price), assert on at least one field of the first result. Apply when the endpoint is HTML-scraped; JSON APIs that deserialize cleanly need less scrutiny. See `references/test-code-examples.md`.

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

### Response Body Verification

Never trust status 200 alone. For every API response:

- **Create**: verify returned entity has the submitted field values
- **Read**: verify entity ID matches what was requested
- **Update**: verify changed fields reflect new values
- **Delete**: verify subsequent read returns 404
- **List**: verify count, verify each item has required fields

Print entity IDs for manual verification:
```python
print(f"[verify] Created board id={data['id']} name={data['name']}")
```

### Round-Trip Test Requirement

Every E2E live test MUST include at minimum a create-read-verify round-trip:

```
create entity -> read it back -> verify fields match -> update ->
verify update -> delete -> verify 404 on read
```

Tests that only create without reading back give false confidence.

### The `_resolve_cli` Pattern

See `references/resolve-cli-pattern.md` for the complete helper function and
`TestCLISubprocess` class. Key rules:
- Always use `_resolve_cli("cli-web-<app>")` — never hardcode module paths
- Do NOT set `cwd` — installed commands must work from any directory
- Use `CLI_WEB_FORCE_INSTALLED=1` in CI

### TEST.md Part 1 — Write As You Go

As you write the tests, create `tests/TEST.md` documenting what you built.
Write this alongside the tests, not before or after:

1. **Test Inventory** — List test files and actual test counts
2. **Unit Test Plan** — For each core module: functions tested, edge cases covered
3. **E2E Test Plan** — Live CRUD workflows and what is verified
4. **Realistic Workflow Scenarios** — Multi-step flows with verification criteria:
   - Auth flow: login → store token → make authenticated request → token refresh
   - CRUD round-trip: create → read back → verify fields → update → verify → delete → verify 404
   - Paginated list: fetch page 1 → verify count → fetch page 2 → verify no overlap
   - Bulk operations: create N items → list all → verify count → delete all → verify empty
   - Rate limit handling: rapid requests → verify backoff behavior

---

## Run & Verify

1. **Verify auth is working FIRST:**
   ```bash
   cli-web-<app> auth login              # opens browser via playwright-cli
   cli-web-<app> auth status             # must show live validation: OK
   ```
   If auth status fails, fix it before proceeding.

2. Run full test suite: `python3 -m pytest cli_web/<app>/tests/ -v --tb=short`

3. Run subprocess tests: `CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/<app>/tests/ -v -s -k subprocess`

4. **ALL tests must pass.** If E2E tests fail with auth errors, go back to step 1.
   Do NOT record "auth not configured" as a test result — that means auth is broken.

---

## Document Results in TEST.md

**Goal:** Append test results to TEST.md (Part 2).

Part 2 is **appended** to the existing Part 1. Never overwrite.

**Append** Part 2 to existing `TEST.md`:
- Full `pytest -v --tb=no` output showing ALL tests passing
- Summary: total tests, pass rate, execution date
- Any gaps with explanation

Include example CLI usage in README.md.

### Failure Handling

When tests fail:
1. Show failures with full pytest output
2. Do NOT update TEST.md — it should only contain passing results
3. Analyze and suggest specific fixes
4. Offer to re-run after fixes

---

## Next Step

When all tests pass, invoke the `standards` skill to
publish and verify the CLI.

Do NOT skip to publishing — all tests must pass first.

---

## Reference Files

- [_resolve_cli Pattern](references/resolve-cli-pattern.md) — subprocess testing helper
- [Test Code Examples](references/test-code-examples.md) — unit test patterns, RPC testing

---

## Related

- **`capture`** skill — Phase 1 traffic recording (prerequisite chain)
- **`methodology`** skill — analyze/design/implement
- **`standards`** skill — publish, verify, smoke test
- **`/cli-anything-web:test`** — Command to run tests and update TEST.md
