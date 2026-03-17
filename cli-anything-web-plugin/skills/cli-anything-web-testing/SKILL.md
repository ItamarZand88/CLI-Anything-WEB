---
name: cli-anything-web-testing
description: >
  Plan, write, and document tests for cli-web-* CLIs. Covers Phases 5-7: write
  TEST.md Part 1 (test plan), implement test suite (unit + E2E + subprocess),
  append TEST.md Part 2 (results). Use when writing tests for web API wrappers,
  setting up pytest for HTTP-based CLIs, creating TEST.md files, writing E2E tests
  with fixture replay, implementing subprocess tests with _resolve_cli, or when
  working on Phases 5-7 of the cli-anything-web pipeline.
version: 0.1.0
---

# CLI-Anything-Web Testing (Phases 5-7)

Plan, write, and document tests for cli-web-* CLIs. This skill owns the full
testing lifecycle: test planning, test implementation, and test documentation.

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] Phase 4 implementation is complete (all core modules + commands exist)
- [ ] `pip install -e .` succeeds and `cli-web-<app>` is on PATH
- [ ] `<APP>.md` exists with API map and auth scheme

If implementation is incomplete, invoke the `cli-anything-web-methodology` skill first.

---

## Phase 5: Plan Tests (TEST.md Part 1)

**Goal:** Write the test plan BEFORE writing any test code.

**BEFORE writing any test code**, create `tests/TEST.md` in the app package.
This file serves as the test plan and MUST contain:

1. **Test Inventory** -- List planned test files and estimated test counts:
   - `test_core.py`: XX unit tests planned
   - `test_e2e.py`: XX E2E tests planned (fixture), XX E2E tests planned (live),
     XX subprocess tests planned

2. **Unit Test Plan** -- For each core module, describe what will be tested:
   - Module name (e.g., `client.py`)
   - Functions to test
   - Edge cases (invalid auth, rate limit response, malformed JSON, 404, 401, 500)
   - Expected test count

3. **E2E Test Plan** -- Describe the test scenarios:
   - Fixture replay tests: which captured responses will be replayed?
   - Live tests: which CRUD workflows will run against the real API?
   - What response fields will be verified?

4. **Realistic Workflow Scenarios** -- Detail each multi-step workflow:
   - **Scenario name**
   - **Simulates**: what real user task (e.g., "creating and managing a project board",
     "bulk-creating tasks and archiving completed ones")
   - **Operations**: step-by-step API calls
   - **Verified**: what response fields and round-trip consistency is checked

   Example scenarios for web apps:
   - Auth flow: login -> store token -> make authenticated request -> token refresh
   - CRUD round-trip: create entity -> read it back -> verify fields match -> update ->
     verify update -> delete -> verify 404 on read
   - Paginated list: fetch page 1 -> verify count -> fetch page 2 -> verify no overlap
   - Bulk operations: create N items -> list all -> verify count -> delete all -> verify empty
   - Rate limit handling: rapid requests -> verify backoff behavior
   - Content generation: trigger generate -> poll status -> download result -> verify file exists and size > 0
   - CAPTCHA handling: mock a CAPTCHA response -> verify CLI pauses with user prompt (not crash/skip)

This planning document ensures comprehensive test coverage before writing code.

---

## Phase 6: Write Tests

**Goal:** Comprehensive test suite covering all layers.

### Auth MUST Be Working Before Any E2E Test

This is the #1 rule for web CLI testing. Before writing or running any E2E test:

1. Ensure playwright-cli is available (`npx @playwright/cli@latest --version`)
2. Run `cli-web-<app> auth login` (playwright-cli state-save)
3. Run `cli-web-<app> auth status` -- must show valid
4. If auth fails, STOP and fix it. Do NOT write tests that catch auth errors.

Tests that output "auth not configured" or skip on missing auth are **broken tests**.
The web app requires authentication -- the tests must authenticate. This is the web
equivalent of CLI-Anything's rule that the real software must be installed.

If a test cannot authenticate, it must call `pytest.fail()` with a message telling
the user to run `auth login`, not silently skip or catch the error.

### Testing with Browser-Delegated Auth

For apps that use browser-delegated auth (Google batchexecute, etc.), tests need
more than just cookies -- they need fresh CSRF and session tokens too.

**Test setup flow:**
1. Ensure playwright-cli is available (`npx @playwright/cli@latest --version`)
2. `cli-web-<app> auth login` -- captures auth state via playwright-cli state-save
3. Auth module automatically fetches CSRF + session tokens via HTTP GET
4. `cli-web-<app> auth status` -- must show cookies, CSRF token, AND session ID
5. If first API call gets 401, the client should auto-refresh tokens before failing

**Unit tests for RPC protocols:**
When the app uses batchexecute or custom RPC, add unit tests for the codec:
- Test `rpc/encoder.py`: verify triple-nested array format, URL encoding
- Test `rpc/decoder.py`: verify anti-XSSI stripping, chunked parsing, double-JSON decode
- Use captured response fixtures in `tests/fixtures/` for decoder tests
- Test error response detection (`"er"` entries in batchexecute)
- Test auth error detection and refresh trigger

### Four-Layer Testing Strategy

| Layer | File | Purpose |
|-------|------|---------|
| Unit | `test_core.py` | Core functions with mocked HTTP. No network. Fast. |
| E2E fixture | `test_e2e.py` | Replay captured responses from `tests/fixtures/`. Verifies parsing. |
| E2E live | `test_e2e.py` | Real API calls. Require auth -- FAIL (not skip) without it. |
| CLI subprocess | `test_e2e.py` | Installed `cli-web-<app>` via `_resolve_cli()`. Full end-to-end. |

### Parallel Test Writing (dispatch independent test files as subagents)

Like Phase 4, test files are independent and can be written in parallel:

| Test file | Scope | Independent? |
|-----------|-------|-------------|
| `test_core.py` -- client tests | Mock HTTP, test `client.py` | Yes |
| `test_core.py` -- auth tests | Mock filesystem, test `auth.py` | Yes |
| `test_core.py` -- RPC codec tests | Test encoder/decoder with fixtures | Yes |
| `test_e2e.py` -- fixture replay | Replay captured responses | Depends on fixtures existing |
| `test_e2e.py` -- live tests | Real API calls | Depends on auth working |
| `test_e2e.py` -- subprocess tests | `_resolve_cli()` | Depends on `pip install -e .` |

Dispatch strategy:
```
Agent 1 -> "Write unit tests for core/client.py and core/auth.py in test_core.py"
Agent 2 -> "Write RPC encoder/decoder unit tests (if applicable) in test_core.py"
Agent 3 -> "Write E2E fixture replay tests and live CRUD tests in test_e2e.py"
# After all return, integrate into final test files and run
```

Each agent receives: the module it's testing, the TEST.md plan (from Phase 5),
and sample API responses from `tests/fixtures/`. Agents must NOT depend on each
other's output.

### Testing Rules

- Use `unittest.mock.patch` for HTTP in unit tests
- Store captured responses in `tests/fixtures/` for replay
- E2E live tests require auth -- **FAIL (not skip, not catch, not "auth not configured")**
- If a test cannot authenticate, it must `pytest.fail("Auth not configured. Run: cli-web-<app> auth login")`
- `TestCLISubprocess` using `_resolve_cli("cli-web-<app>")`
- Target: >80% coverage on core modules

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

Every subprocess test must use this helper -- never hardcode paths:

```python
import os, sys, shutil, subprocess

def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev."""
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-web-", "cli_web.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-web-<app>")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True,
            check=check,
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
```

Key rules for subprocess tests:
- Always use `_resolve_cli("cli-web-<app>")` -- never hardcode module paths
- Do NOT set `cwd` -- installed commands must work from any directory
- Use `CLI_WEB_FORCE_INSTALLED=1` in CI to ensure the installed command is tested
- After running, verify `[_resolve_cli] Using installed command:` appears in output

### Unit Test Pattern

```python
from unittest.mock import patch, MagicMock

def test_client_get_boards():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"boards": [{"id": 1, "name": "Sprint"}]}

    with patch("cli_web.<app>.core.client.httpx.get", return_value=mock_response):
        result = get_boards()
        assert len(result["boards"]) == 1
        assert result["boards"][0]["name"] == "Sprint"
```

---

## Phase 7: Document (Update TEST.md)

**Goal:** Append test results to TEST.md (Part 2).

Phase 7 **appends** results to the existing `TEST.md` (which already has Part 1
from Phase 5). It does NOT write TEST.md from scratch.

### Process

1. **Verify auth is working FIRST:**
   ```bash
   cli-web-<app> auth login              # opens browser via playwright-cli
   cli-web-<app> auth status             # must show live validation: OK
   ```
   If auth status fails, fix it before proceeding. Do NOT run tests without working auth.

2. Run full test suite: `python3 -m pytest cli_web/<app>/tests/ -v --tb=short`

3. Run subprocess tests: `CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/<app>/tests/ -v -s -k subprocess`

4. **ALL tests must pass.** If E2E tests fail with auth errors, go back to step 1.
   Do NOT record "auth not configured" as a test result -- that means auth is broken.

5. **Append** Part 2 to existing `TEST.md`:
   - Full `pytest -v --tb=no` output showing ALL tests passing
   - Summary: total tests, pass rate, execution date
   - Any gaps with explanation

6. Include example CLI usage in README.md

### TEST.md: Two-Part Structure

**Part 1 (Phase 5 -- before writing test code):**
1. Test Inventory -- planned files and estimated counts per file
2. Unit Test Plan -- per-module: functions, edge cases, expected count
3. E2E Test Plan -- fixture replay scenarios + live CRUD workflows
4. Realistic Workflow Scenarios -- multi-step flows with verification criteria

**Part 2 (Phase 7 -- appended after running tests):**
- Full `pytest -v --tb=no` output
- Summary: total, pass rate, date
- Gap notes

Part 2 is **appended** to the existing Part 1. Never overwrite.

---

## Failure Handling

When tests fail:
1. Show failures with full pytest output
2. Do NOT update TEST.md -- it should only contain passing results
3. Analyze and suggest specific fixes
4. Offer to re-run after fixes

---

## Next Step

When all tests pass, invoke the `cli-anything-web-standards` skill to
publish and verify the CLI.

Do NOT skip to publishing -- all tests must pass first.

---

## Related

- **`cli-anything-web-capture`** skill -- Phase 1 traffic recording (prerequisite chain)
- **`cli-anything-web-methodology`** skill -- Phases 2-4 analyze/design/implement
- **`cli-anything-web-standards`** skill -- Phase 8 publish, verify, smoke test
- **`/cli-anything-web:test`** -- Command to run tests and update TEST.md
