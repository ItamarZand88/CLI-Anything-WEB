---
name: cli-anything-web-testing
description: Use this skill when writing tests for a cli-web-* CLI, implementing test suites for web API wrappers, setting up pytest for HTTP-based CLIs, creating TEST.md files, writing E2E tests with fixture replay, or implementing subprocess tests with _resolve_cli. Also use when the user asks about testing patterns for web CLIs, how to mock HTTP calls, how to structure test files for cli_web packages, or when working on Phases 5-7 of the cli-anything-web pipeline.
version: 0.1.0
---

# CLI-Anything-Web Testing Patterns

This skill contains the testing methodology for `cli-web-*` CLIs. It activates
automatically during test planning, test writing, and test documentation — you
don't need to invoke it explicitly.

For the full methodology SOP, read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`.

## Auth MUST Be Working Before Any E2E Test

This is the #1 rule for web CLI testing. Before writing or running any E2E test:

1. Run `cli-web-<app> auth login --from-browser` (extracts cookies from Chrome debug profile)
2. Run `cli-web-<app> auth status` — must show live validation succeeded
3. If auth fails, STOP and fix it. Do NOT write tests that catch auth errors.

Tests that output "auth not configured" or skip on missing auth are **broken tests**.
The web app requires authentication — the tests must authenticate. This is the web
equivalent of CLI-Anything's rule that the real software must be installed.

If a test cannot authenticate, it must call `pytest.fail()` with a message telling
the user to run `auth login --from-browser`, not silently skip or catch the error.

## Testing with Browser-Delegated Auth

For apps that use browser-delegated auth (Google batchexecute, etc.), tests need
more than just cookies — they need fresh CSRF and session tokens too.

**Test setup flow:**
1. Ensure Chrome debug profile is running (port 9222) with active login
2. `cli-web-<app> auth login --from-browser` — extracts cookies via CDP
3. Auth module automatically fetches CSRF + session tokens via HTTP GET
4. `cli-web-<app> auth status` — must show cookies, CSRF token, AND session ID
5. If first API call gets 401, the client should auto-refresh tokens before failing

**Unit tests for RPC protocols:**
When the app uses batchexecute or custom RPC, add unit tests for the codec:
- Test `rpc/encoder.py`: verify triple-nested array format, URL encoding
- Test `rpc/decoder.py`: verify anti-XSSI stripping, chunked parsing, double-JSON decode
- Use captured response fixtures in `tests/fixtures/` for decoder tests
- Test error response detection (`"er"` entries in batchexecute)
- Test auth error detection and refresh trigger

## TEST.md: Two-Part Structure

TEST.md is written in two phases — plan first, results later:

**Part 1 (Phase 5 — before writing test code):**
1. **Test Inventory** — planned files and estimated counts per file
2. **Unit Test Plan** — per-module: functions, edge cases, expected count
3. **E2E Test Plan** — fixture replay scenarios + live CRUD workflows
4. **Realistic Workflow Scenarios** — multi-step flows with verification criteria

**Part 2 (Phase 7 — appended after running tests):**
- Full `pytest -v --tb=no` output
- Summary: total, pass rate, date
- Gap notes

Part 2 is **appended** to the existing Part 1. Never overwrite.

## Four-Layer Testing Strategy

| Layer | File | Purpose |
|-------|------|---------|
| Unit | `test_core.py` | Core functions with mocked HTTP. No network. Fast. |
| E2E fixture | `test_e2e.py` | Replay captured responses from `tests/fixtures/`. Verifies parsing. |
| E2E live | `test_e2e.py` | Real API calls. Require auth — FAIL (not skip) without it. |
| CLI subprocess | `test_e2e.py` | Installed `cli-web-<app>` via `_resolve_cli()`. Full end-to-end. |

## The `_resolve_cli` Pattern

Every subprocess test must use this helper — never hardcode paths:

```python
import os
import sys
import shutil
import subprocess

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
- Always use `_resolve_cli("cli-web-<app>")` — never hardcode module paths
- Do NOT set `cwd` — installed commands must work from any directory
- Use `CLI_WEB_FORCE_INSTALLED=1` in CI to ensure the installed command is tested
- After running, verify `[_resolve_cli] Using installed command:` appears in output

## Response Body Verification

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

## Round-Trip Test Requirement

Every E2E live test MUST include at minimum a create-read-verify round-trip:

```
create entity → read it back → verify fields match → update →
verify update → delete → verify 404 on read
```

Tests that only create without reading back give false confidence.

## Realistic Workflow Scenarios

Include multi-step scenarios that simulate real user tasks:

- **Auth flow**: login → store token → authenticated request → token refresh
- **CRUD round-trip**: create → read → verify → update → verify → delete → verify 404
- **Paginated list**: page 1 → verify count → page 2 → verify no overlap
- **Bulk operations**: create N → list all → verify count → delete all → verify empty
- **Rate limit handling**: rapid requests → verify backoff behavior

## Unit Test Pattern

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

## End-User Smoke Test (Phase 8)

After all unit and E2E tests pass, the agent MUST run a final smoke test that
simulates what a real end user would do. This catches issues that test mocks hide:

1. `pip install -e .` (already done)
2. `cli-web-<app> auth login` (Playwright) or `auth login --from-browser` (CDP)
3. `cli-web-<app> auth status` — must show live validation OK
4. `cli-web-<app> --json <resource> list` — must return real data from live API
5. If any step fails, the pipeline is NOT complete

This is different from E2E tests — those run inside pytest with pre-configured auth.
The smoke test verifies the full user journey: install → login → use.

## Failure Handling

When tests fail:
1. Show failures with full pytest output
2. Do NOT update TEST.md — it should only contain passing results
3. Analyze and suggest specific fixes
4. Offer to re-run after fixes

## Related

- **`/cli-anything-web:test`** — Command to run tests and update TEST.md
- **`${CLAUDE_PLUGIN_ROOT}/HARNESS.md`** — Full methodology (Phases 5-7 cover testing)
- **`cli-anything-web-standards`** skill — The 50-check quality checklist (Categories 5 and 8 cover test standards)
