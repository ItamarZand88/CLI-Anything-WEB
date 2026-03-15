# TEST.md — cli-web-notebooklm
## Part 1: Test Plan (Phase 5)

> Written before any test code. Part 2 will be appended after tests pass (Phase 7).

---

## 1. Test Inventory

| File | Layer | Planned Tests |
|------|-------|--------------|
| `tests/test_core.py` | Unit (mocked HTTP) | 38 unit tests |
| `tests/test_e2e.py` | E2E fixture replay | 12 fixture tests |
| `tests/test_e2e.py` | E2E live (real API) | 14 live tests |
| `tests/test_e2e.py` | CLI subprocess | 10 subprocess tests |
| **Total** | | **74 tests** |

Fixture files to create in `tests/fixtures/`:
- `notebooks_list.json` — paginated list response
- `notebook_create.json` — create response with notebook ID
- `notebook_get.json` — single notebook read-back
- `notebook_delete.json` — delete 204/200 response
- `sources_list.json` — sources array for a notebook
- `source_add_url.json` — URL source creation response
- `source_add_pdf.json` — PDF source creation response
- `auth_missing.json` — 401 error payload
- `rate_limit.json` — 429 rate-limit error payload
- `notebook_not_found.json` — 404 error payload

---

## 2. Unit Test Plan (`test_core.py`)

All tests use `unittest.mock.patch` on the HTTP layer. No real network calls. All tests must be deterministic and fast (< 1s total).

### 2.1 Module: `core/client.py`

**Functions to test:** `get()`, `post()`, `delete()`, `_inject_auth_header()`, `_parse_response()`, `_handle_rate_limit()`

| Test function | What it verifies |
|---------------|-----------------|
| `test_client_get_injects_auth_header` | GET request includes Authorization/Cookie header from stored credentials |
| `test_client_post_sends_json_body` | POST serializes body dict to JSON; Content-Type is application/json |
| `test_client_delete_returns_on_204` | DELETE with 204 No Content does not raise; returns None or empty dict |
| `test_client_raises_on_401` | 401 response raises `AuthError` with clear message ("Run `cli-web-notebooklm auth login`") |
| `test_client_raises_on_404` | 404 response raises `NotFoundError` with entity description in message |
| `test_client_raises_on_500` | 500 response raises `APIError` with status code in message |
| `test_client_raises_on_malformed_json` | Response with invalid JSON body raises `ParseError`, does not crash silently |
| `test_client_rate_limit_triggers_backoff` | 429 response triggers retry with exponential backoff; asserts sleep was called with increasing intervals |
| `test_client_rate_limit_raises_after_max_retries` | After N retries all return 429, raises `RateLimitError` |
| `test_client_get_no_auth_file_raises` | When auth file does not exist, raises `AuthError` immediately — never falls back to unauthenticated |

**Edge cases:** empty response body, non-JSON content-type header, connection timeout, `Retry-After` header parsing.

**Expected test count: 10**

---

### 2.2 Module: `core/auth.py`

**Functions to test:** `load_credentials()`, `save_credentials()`, `is_authenticated()`, `get_auth_header()`, `clear_credentials()`

| Test function | What it verifies |
|---------------|-----------------|
| `test_load_credentials_reads_auth_json` | Reads from `~/.config/cli-web-notebooklm/auth.json`; returns dict with token fields |
| `test_load_credentials_missing_file_raises` | Missing auth file raises `AuthError`, not `FileNotFoundError` |
| `test_load_credentials_malformed_json_raises` | Corrupt auth.json raises `AuthError` with path in message |
| `test_save_credentials_writes_chmod_600` | After save, file permissions are 0o600 (owner read/write only) |
| `test_save_credentials_creates_parent_dirs` | Saves successfully even when `~/.config/cli-web-notebooklm/` doesn't exist yet |
| `test_is_authenticated_true_when_token_present` | Returns `True` when auth.json contains a non-empty token |
| `test_is_authenticated_false_when_file_missing` | Returns `False` when file absent |
| `test_get_auth_header_returns_dict` | Returns dict appropriate for HTTP header injection (e.g., `{"Authorization": "Bearer ..."}` or cookie dict) |
| `test_clear_credentials_removes_file` | After `clear_credentials()`, auth file no longer exists |

**Edge cases:** auth.json with extra unknown fields (forward compatibility), token field present but empty string.

**Expected test count: 9**

---

### 2.3 Module: `commands/notebooks.py`

**Functions to test:** `list_notebooks()`, `create_notebook()`, `delete_notebook()`

| Test function | What it verifies |
|---------------|-----------------|
| `test_list_notebooks_returns_list` | Returns list of notebook dicts; each item has `id` and `name` fields |
| `test_list_notebooks_empty_returns_empty_list` | API returning empty array produces `[]`, not error |
| `test_create_notebook_returns_entity_with_submitted_name` | Returned entity `name` matches what was submitted (response body verification) |
| `test_create_notebook_returns_id` | Returned entity contains `id` field (non-empty, non-None) |
| `test_delete_notebook_calls_correct_endpoint` | DELETE is called on the correct URL path containing the notebook ID |
| `test_delete_notebook_404_raises_not_found` | 404 during delete raises `NotFoundError` with notebook ID in message |

**Edge cases:** notebook name with Unicode characters, notebook name with special characters (`/`, `"`, `\n`), very long name (>255 chars).

**Expected test count: 6**

---

### 2.4 Module: `commands/sources.py`

**Functions to test:** `list_sources()`, `add_url_source()`, `add_pdf_source()`

| Test function | What it verifies |
|---------------|-----------------|
| `test_list_sources_returns_list` | Returns list; each item has `id`, `type`, and at least one identifying field |
| `test_list_sources_for_nonexistent_notebook_raises` | 404 from API raises `NotFoundError` with notebook ID |
| `test_add_url_source_sends_url_in_body` | POST body contains the submitted URL |
| `test_add_url_source_returns_source_id` | Returned entity contains `id` field |
| `test_add_url_source_invalid_url_raises` | Malformed URL raises `ValueError` client-side before any HTTP call |
| `test_add_pdf_source_reads_local_file` | Reads PDF bytes from local path; sends correct multipart/form-data |
| `test_add_pdf_source_file_not_found_raises` | Non-existent PDF path raises `FileNotFoundError` with the path in message |

**Edge cases:** URL with query params, URL with fragments, PDF file that is 0 bytes, PDF path with spaces.

**Expected test count: 7**

---

### 2.5 Module: `utils/output.py`

**Functions to test:** `format_json()`, `format_table()`, `print_entity()`

| Test function | What it verifies |
|---------------|-----------------|
| `test_format_json_produces_valid_json` | Output is parseable JSON; matches input data |
| `test_format_table_renders_notebook_list` | Renders list of notebooks with `id` and `name` columns |
| `test_format_table_empty_list_renders_header_only` | Empty list renders column headers, not an error |
| `test_print_entity_id_logged_for_verification` | Output includes `[verify]` prefix with entity ID and name (for manual audit) |
| `test_json_flag_overrides_table_format` | When `--json` is active, output is raw JSON regardless of data type |
| `test_format_table_truncates_long_names` | Names > terminal width are truncated with ellipsis, not wrapped badly |

**Expected test count: 6**

---

## 3. E2E Test Plan (`test_e2e.py`)

### 3.1 Fixture Replay Tests

These tests load pre-captured API responses from `tests/fixtures/` and replay them through the real parsing/command logic. No network required. They verify that parsing logic, field extraction, and output formatting are correct for real API shapes.

| Test function | Fixture file | What it verifies |
|---------------|-------------|-----------------|
| `test_fixture_notebooks_list_parsed_correctly` | `notebooks_list.json` | Top-level structure, each notebook has `id`+`name`, count matches |
| `test_fixture_notebook_create_fields_extracted` | `notebook_create.json` | Returned `id` is non-empty; `name` matches submitted value |
| `test_fixture_notebook_get_id_matches` | `notebook_get.json` | Returned entity `id` matches requested ID |
| `test_fixture_notebook_delete_succeeds` | `notebook_delete.json` | 204/200 is handled without raising |
| `test_fixture_sources_list_parsed_correctly` | `sources_list.json` | Each source has `id` and `type`; list count > 0 |
| `test_fixture_source_add_url_fields_extracted` | `source_add_url.json` | Returned source has `id` and reflects submitted URL |
| `test_fixture_source_add_pdf_fields_extracted` | `source_add_pdf.json` | Returned source has `id` and `type == "pdf"` (or equivalent) |
| `test_fixture_401_raises_auth_error` | `auth_missing.json` | 401 payload triggers `AuthError`, not generic crash |
| `test_fixture_429_triggers_retry_logic` | `rate_limit.json` | 429 payload is recognized; retry/backoff path is entered |
| `test_fixture_404_notebook_not_found` | `notebook_not_found.json` | 404 payload raises `NotFoundError` with ID in message |
| `test_fixture_json_output_matches_raw` | `notebooks_list.json` | `--json` output is valid JSON; top-level keys match fixture |
| `test_fixture_table_output_contains_names` | `notebooks_list.json` | Table output contains at least the notebook names from fixture |

**Expected test count: 12**

---

### 3.2 Live E2E Tests

These tests call the real NotebookLM API. Auth is **required** — tests FAIL (do not skip) if `~/.config/cli-web-notebooklm/auth.json` is absent. Each test prints `[verify]` lines with entity IDs for manual audit.

**Setup:** `pytest.fixture` creates a fresh notebook at session start; teardown deletes it. Tests share this notebook to avoid excessive create/delete cycles.

| Test function | Operations | Verified fields |
|---------------|-----------|-----------------|
| `test_live_auth_required_fails_without_credentials` | Attempts any API call with auth file removed | Raises `AuthError`; return code non-zero |
| `test_live_notebooks_list_returns_items` | `GET /notebooks` | Response is list; each item has `id`, `name`; count >= 0 |
| `test_live_notebook_create_round_trip` | `POST /notebooks` → `GET /notebooks/{id}` | Created `name` matches submitted; read-back `id` matches create response `id` |
| `test_live_notebook_create_verifies_body` | `POST /notebooks` with specific name | Returned entity `name` == submitted name (not just 201 status) |
| `test_live_notebook_delete_then_verify_404` | `DELETE /notebooks/{id}` → `GET /notebooks/{id}` | Delete succeeds; subsequent read returns 404 / `NotFoundError` |
| `test_live_notebook_create_unicode_name` | `POST /notebooks` with Unicode name (e.g., `"テストノート"`) | Returned `name` matches submitted Unicode string exactly |
| `test_live_sources_list_for_notebook` | `GET /notebooks/{id}/sources` | Returns list (may be empty); structure has `id` field per source |
| `test_live_source_add_url_round_trip` | `POST /notebooks/{id}/sources` (URL) → `GET /notebooks/{id}/sources` | Source appears in list; `id` matches create response; URL is preserved |
| `test_live_source_add_url_verifies_body` | `POST` with specific URL | Returned source contains submitted URL (not just 200 status) |
| `test_live_source_add_pdf_round_trip` | `POST /notebooks/{id}/sources` (PDF) → list sources | Source appears with correct `type`; file name or metadata preserved |
| `test_live_sources_list_empty_notebook` | List sources on brand-new notebook | Returns empty list `[]`, not error |
| `test_live_notebooks_list_count_after_create` | List → create → list again | Count increases by exactly 1 |
| `test_live_notebooks_list_count_after_delete` | List → delete → list again | Count decreases by exactly 1 |
| `test_live_full_notebook_lifecycle` | Create → read → list (verify present) → add source → list sources → delete → verify 404 | All fields at each step; complete lifecycle in one test |

**Expected test count: 14**

---

### 3.3 CLI Subprocess Tests

These tests invoke the installed `cli-web-notebooklm` binary via `subprocess.run` using `_resolve_cli()`. They test the full stack: arg parsing, HTTP dispatch, output formatting, exit codes.

**The `_resolve_cli` helper (required in test_e2e.py):**

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
    module = "cli_web.notebooklm.notebooklm_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-web-notebooklm")

    def _run(self, args, check=True, env=None):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True,
            check=check, env=env,
        )
```

Note: `cwd` is never set — the installed command must work from any directory.

| Test function | Command invoked | Verified |
|---------------|----------------|---------|
| `test_subprocess_help` | `--help` | Exit code 0; stdout contains "notebooks" and "sources" |
| `test_subprocess_notebooks_help` | `notebooks --help` | Exit code 0; stdout contains "list", "create", "delete" |
| `test_subprocess_sources_help` | `sources --help` | Exit code 0; stdout contains "add-url", "add-pdf", "list" |
| `test_subprocess_notebooks_list_json` | `--json notebooks list` | Exit code 0; stdout is valid JSON list |
| `test_subprocess_notebooks_list_table` | `notebooks list` (no --json) | Exit code 0; stdout is human-readable table (not raw JSON) |
| `test_subprocess_notebook_create_and_delete` | `--json notebooks create --name "subprocess-test"` → parse ID → `notebooks delete --id {id}` | Create exit code 0; returned JSON has `id`; delete exit code 0 |
| `test_subprocess_source_add_url` | `--json sources add-url --notebook-id {id} --url https://example.com` | Exit code 0; returned JSON has source `id` |
| `test_subprocess_missing_auth_exits_nonzero` | Any command with auth file removed via env override | Exit code non-zero; stderr contains auth instruction |
| `test_subprocess_invalid_notebook_id_exits_nonzero` | `notebooks delete --id nonexistent-id-xyz` | Exit code non-zero; stderr contains "not found" or similar |
| `test_subprocess_version_or_no_args_shows_help` | (no args) | Exit code 0; REPL launches or help is shown — does NOT crash |

**Expected test count: 10**

---

## 4. Realistic Workflow Scenarios

These are the multi-step workflows that E2E live tests must cover. Each scenario simulates a real user task.

---

### Scenario A: New Notebook Lifecycle

**Simulates:** A researcher starts a new project by creating a notebook, adds sources, and later deletes the project.

**Operations:**
1. `notebooks list` → record initial count `N`
2. `notebooks create --name "Q1 Research 2026"` → capture `notebook_id`
3. Print `[verify] Created notebook id={notebook_id} name="Q1 Research 2026"`
4. `notebooks list` → verify count is now `N+1`; verify new notebook appears in list by ID
5. `sources list --notebook-id {notebook_id}` → verify empty list (new notebook has no sources)
6. `sources add-url --notebook-id {notebook_id} --url https://en.wikipedia.org/wiki/Python_(programming_language)` → capture `source_id`
7. Print `[verify] Added source id={source_id}`
8. `sources list --notebook-id {notebook_id}` → verify count is 1; verify `source_id` appears
9. `notebooks delete --id {notebook_id}`
10. `notebooks list` → verify count is back to `N`; verify `notebook_id` is absent

**Verified:**
- Submitted name propagates to read-back (not server-generated default)
- List count increments and decrements correctly
- Source is visible in list immediately after add (no eventual consistency lag in tests)
- Deletion is permanent: notebook absent from list after delete

---

### Scenario B: Source Ingestion (URL + PDF)

**Simulates:** A user populates a notebook with multiple source types before generating content.

**Operations:**
1. `notebooks create --name "Mixed Sources Test"` → capture `notebook_id`
2. `sources add-url --notebook-id {notebook_id} --url https://docs.python.org/3/`
3. `sources add-url --notebook-id {notebook_id} --url https://peps.python.org/pep-0008/`
4. `sources add-pdf --notebook-id {notebook_id} --path tests/fixtures/sample.pdf`
5. `sources list --notebook-id {notebook_id}` → verify exactly 3 sources; each has `id` and `type`
6. Verify URL sources have `type` indicating URL; PDF source has `type` indicating PDF
7. `notebooks delete --id {notebook_id}` (cleanup)

**Verified:**
- Multiple sources can be added sequentially without errors
- Each source has distinct `id`
- Source `type` field correctly reflects the ingestion method
- Final count matches number of add operations

---

### Scenario C: Auth Failure Isolation

**Simulates:** A user whose credentials have expired tries to use the CLI; the error message guides them to re-authenticate.

**Operations:**
1. Temporarily rename/remove `~/.config/cli-web-notebooklm/auth.json`
2. Attempt `notebooks list`
3. Restore auth file

**Verified:**
- Command exits with non-zero exit code
- Error message (stderr) explicitly instructs user to run `cli-web-notebooklm auth login` (or equivalent auth command)
- No partial output to stdout (no mixing of error into JSON output stream)
- Test does NOT skip — it fails if auth failure is not properly surfaced

---

### Scenario D: JSON Output for Agent Consumption

**Simulates:** An AI agent uses the CLI as a tool and parses `--json` output programmatically.

**Operations:**
1. `--json notebooks list` → parse stdout as JSON; verify schema
2. `--json notebooks create --name "Agent Test Notebook"` → parse stdout; extract `id`
3. `--json sources add-url --notebook-id {id} --url https://example.com` → parse stdout; extract source `id`
4. `--json sources list --notebook-id {id}` → parse stdout; verify source `id` appears in list
5. `--json notebooks delete --id {id}` → parse stdout or verify exit code 0

**Verified:**
- Every `--json` command produces valid, parseable JSON on stdout
- No log lines, banners, or human-readable text mixed into stdout when `--json` is active
- Schema is consistent across calls (list always returns array, create always returns object with `id`)
- Exit code is 0 for all successful operations; non-zero only on error

---

### Scenario E: Idempotency and Duplicate Handling

**Simulates:** A user accidentally runs the same source-add command twice.

**Operations:**
1. `notebooks create --name "Idempotency Test"` → capture `notebook_id`
2. `sources add-url --notebook-id {notebook_id} --url https://example.com` → capture `source_id_1`
3. `sources add-url --notebook-id {notebook_id} --url https://example.com` (same URL again)
4. `sources list --notebook-id {notebook_id}`
5. Cleanup: `notebooks delete --id {notebook_id}`

**Verified:**
- CLI does not crash on duplicate add (either succeeds with new ID or returns existing)
- List count is inspected and documented (behavior is noted, not asserted as error)
- If the API returns an error on duplicate, the CLI surfaces it clearly rather than crashing

---

### Scenario F: Bulk Create and Clean Up

**Simulates:** A script creates several test notebooks and must clean them all up after a batch run.

**Operations:**
1. `notebooks list` → record initial count `N`
2. Create 5 notebooks: `notebooks create --name "Bulk Test {i}"` for i in 1..5 → collect all IDs
3. `notebooks list` → verify count is `N+5`; verify all 5 IDs appear in list
4. Delete all 5: `notebooks delete --id {id}` for each collected ID
5. `notebooks list` → verify count is back to `N`

**Verified:**
- All create operations succeed without rate-limit errors (backoff is working)
- IDs are unique across all 5 create responses
- List faithfully reflects current state after each mutation
- All 5 deletes succeed; final count matches original

---

## 5. Coverage Targets

| Module | Target Coverage | Priority |
|--------|----------------|----------|
| `core/client.py` | > 85% | Critical (all error paths) |
| `core/auth.py` | > 90% | Critical (auth is everything) |
| `commands/notebooks.py` | > 80% | High |
| `commands/sources.py` | > 80% | High |
| `utils/output.py` | > 75% | Medium |
| `utils/config.py` | > 75% | Medium |

Run coverage with:
```
python -m pytest cli_web/notebooklm/tests/ --cov=cli_web.notebooklm --cov-report=term-missing
```

---

## 6. Test Infrastructure Notes

### Auth for Live Tests

Live tests load credentials from `~/.config/cli-web-notebooklm/auth.json`. If the file is absent, **tests fail** — they do not skip. This is by design (HARNESS.md Rules).

A session-scoped pytest fixture handles notebook lifecycle:

```python
@pytest.fixture(scope="session")
def live_notebook(client):
    """Create a notebook at session start; delete at teardown."""
    nb = client.create_notebook(name="pytest-session-fixture")
    print(f"[verify] Session notebook id={nb['id']} name={nb['name']}")
    yield nb
    client.delete_notebook(nb["id"])
```

### Fixture Files

Fixture JSON files in `tests/fixtures/` are captured from real API traffic (Phase 1). They must not be hand-authored — they must be real responses to ensure parsing tests exercise actual API shape.

### Subprocess / CI

In CI, set `CLI_WEB_FORCE_INSTALLED=1` before running subprocess tests:
```
pip install -e .
CLI_WEB_FORCE_INSTALLED=1 python -m pytest cli_web/notebooklm/tests/ -v -s -k subprocess
```
Verify that output contains `[_resolve_cli] Using installed command:` — not the fallback path.

### Rate Limiting

Live tests must not fire requests in a tight loop. Between sequential mutating calls (create/delete), insert a minimal sleep if the API exhibits rate limit sensitivity during test development. Remove sleeps once backoff in `client.py` is confirmed working.

---

*Part 2 (pytest output and summary) will be appended here after Phase 7.*
