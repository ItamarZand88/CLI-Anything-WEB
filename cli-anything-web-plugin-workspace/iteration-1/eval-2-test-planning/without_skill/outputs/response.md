# TEST.md — cli-web-notebooklm (Part 1: Test Plan)

**Written before any test code is implemented.**
**Part 2 (results) will be appended after running the suite.**

---

## 1. Test Inventory

| File | Layer | Estimated Tests |
|------|-------|----------------|
| `tests/test_core.py` | Unit (mocked HTTP) | 32 tests |
| `tests/test_e2e.py` | E2E fixture replay | 10 tests |
| `tests/test_e2e.py` | E2E live (real API) | 14 tests |
| `tests/test_e2e.py` | CLI subprocess | 9 tests |
| **Total** | | **65 tests** |

Fixture responses live in `tests/fixtures/`. Every fixture file is a JSON
snapshot captured from live NotebookLM traffic; fixture tests replay them
without hitting the network.

---

## 2. Unit Test Plan (`test_core.py`)

Unit tests use `unittest.mock.patch` exclusively. No real network calls.
Fast, deterministic, runnable without auth.

### 2.1 `core/client.py` — HTTP Client

**Functions under test:** `NotebookLMClient.__init__`, `get`, `post`, `delete`,
`_inject_auth`, `_handle_response`, `_backoff_retry`

**Tests:**

| Test function | What it covers |
|---|---|
| `test_client_injects_auth_header` | `Authorization: Bearer <token>` present on every request |
| `test_client_injects_cookie_session` | Cookie-based session header injected when token is a session cookie |
| `test_client_get_returns_parsed_json` | Successful 200 → `response.json()` returned |
| `test_client_post_returns_parsed_json` | POST with body → 201 response parsed and returned |
| `test_client_delete_returns_none_on_204` | DELETE returning 204 No Content → returns `None` without crashing |
| `test_client_raises_on_401` | 401 response raises `AuthError` with actionable message |
| `test_client_raises_on_403` | 403 response raises `AuthError` (permission denied) |
| `test_client_raises_on_404` | 404 response raises `NotFoundError` with entity info |
| `test_client_raises_on_500` | 500 response raises `APIError` with status code in message |
| `test_client_raises_on_malformed_json` | `JSONDecodeError` in response → raises `APIError`, not crash |
| `test_client_rate_limit_triggers_backoff` | 429 response → `_backoff_retry` called, retried after delay |
| `test_client_backoff_respects_retry_after_header` | `Retry-After: 5` header → waits ≥5s before retry |
| `test_client_no_bare_except` | (static) Ensure no `except:` in client source — enforced by grep in CI |

**Expected count: 13**

---

### 2.2 `core/auth.py` — Authentication

**Functions under test:** `AuthManager.load`, `save`, `is_valid`, `refresh`,
`get_headers`, `clear`

**Tests:**

| Test function | What it covers |
|---|---|
| `test_auth_load_reads_auth_json` | Reads `~/.config/cli-web-notebooklm/auth.json` correctly |
| `test_auth_load_raises_if_file_missing` | Missing auth file raises `AuthError` with install instructions |
| `test_auth_save_writes_file_with_chmod_600` | `save()` creates file and sets mode `0o600` |
| `test_auth_is_valid_returns_true_when_token_present` | Non-empty token → `is_valid()` is `True` |
| `test_auth_is_valid_returns_false_when_token_empty` | Empty/null token → `is_valid()` is `False` |
| `test_auth_is_valid_returns_false_when_expired` | Token with past `expires_at` timestamp → `False` |
| `test_auth_get_headers_returns_bearer_token` | Returns `{"Authorization": "Bearer <token>"}` |
| `test_auth_get_headers_raises_if_not_valid` | Calling `get_headers()` when invalid → raises `AuthError` |
| `test_auth_refresh_posts_to_token_endpoint` | `refresh()` sends POST to Google OAuth endpoint |
| `test_auth_refresh_updates_stored_token` | After refresh, new token is saved and `is_valid()` returns `True` |
| `test_auth_clear_removes_auth_file` | `clear()` deletes auth.json |

**Expected count: 11**

---

### 2.3 `core/models.py` — Response Models

**Functions under test:** `Notebook.from_dict`, `Source.from_dict`, field validation

**Tests:**

| Test function | What it covers |
|---|---|
| `test_notebook_from_dict_valid` | Full API dict → `Notebook` object with correct fields |
| `test_notebook_from_dict_missing_optional_fields` | Missing optional fields → default values, no crash |
| `test_notebook_from_dict_missing_required_field` | Missing `id` or `title` → raises `ValueError` |
| `test_source_from_dict_url_type` | URL source dict → `Source` with `type="url"` |
| `test_source_from_dict_pdf_type` | PDF source dict → `Source` with `type="pdf"` |
| `test_source_from_dict_unknown_type` | Unknown `type` value → handled gracefully (not crash) |
| `test_notebook_repr_is_human_readable` | `__repr__` or `__str__` contains title and id |
| `test_source_repr_includes_type_and_name` | `__repr__` contains source type and display name |

**Expected count: 8**

---

## 3. E2E Test Plan (`test_e2e.py`)

### 3.1 Fixture Replay Tests

These tests load JSON from `tests/fixtures/` and replay them through the
full command stack — no real network. They verify the parsing pipeline from
raw API response through to CLI output.

**Required fixture files:**

```
tests/fixtures/
  notebooks_list_response.json        # GET /notebooklm/v1/notebooks
  notebook_create_response.json       # POST /notebooklm/v1/notebooks
  notebook_get_response.json          # GET /notebooklm/v1/notebooks/{id}
  notebook_delete_response.json       # DELETE — 204 empty body
  sources_list_response.json          # GET /notebooklm/v1/notebooks/{id}/sources
  source_add_url_response.json        # POST sources with url payload
  source_add_pdf_response.json        # POST sources with pdf upload payload
  error_401_response.json             # 401 Unauthorized
  error_404_response.json             # 404 Not Found
  error_429_response.json             # 429 Too Many Requests
```

**Tests:**

| Test function | Fixture used | What is verified |
|---|---|---|
| `test_fixture_notebooks_list_parses_items` | `notebooks_list_response.json` | Returns list; each item has `id`, `title`, `created_at` |
| `test_fixture_notebook_create_returns_id_and_title` | `notebook_create_response.json` | Returned object `id` and `title` match submitted values |
| `test_fixture_sources_list_parses_items` | `sources_list_response.json` | Returns list; each item has `id`, `type`, `display_name` |
| `test_fixture_source_add_url_returns_source_object` | `source_add_url_response.json` | Returned source has `type="url"` and the submitted URL |
| `test_fixture_source_add_pdf_returns_source_object` | `source_add_pdf_response.json` | Returned source has `type="pdf"` and filename |
| `test_fixture_401_raises_auth_error` | `error_401_response.json` | `AuthError` raised with login instructions in message |
| `test_fixture_404_raises_not_found_error` | `error_404_response.json` | `NotFoundError` raised with entity id in message |
| `test_fixture_429_triggers_backoff` | `error_429_response.json` | `_backoff_retry` invoked; no immediate crash |
| `test_fixture_json_flag_outputs_valid_json` | `notebooks_list_response.json` | With `--json`, stdout is valid parseable JSON |
| `test_fixture_human_output_contains_table_headers` | `notebooks_list_response.json` | Without `--json`, stdout contains column headers (Title, ID) |

**Expected count: 10**

---

### 3.2 E2E Live Tests (Real API)

These tests hit the real NotebookLM API. They **FAIL** (not skip) if
`~/.config/cli-web-notebooklm/auth.json` is absent or invalid. This is
intentional — the CLI is useless without a live account, and skipping gives
false confidence.

**Auth gate pattern (applied to every live test class):**

```python
@pytest.fixture(autouse=True, scope="class")
def require_auth():
    from cli_web.notebooklm.core.auth import AuthManager
    mgr = AuthManager()
    if not mgr.is_valid():
        pytest.fail(
            "Auth required for live tests. Run: cli-web-notebooklm auth login"
        )
```

**Round-trip requirement:** every live test MUST do create → read back →
verify fields. Tests that only create without reading back are not accepted.

**Print IDs for manual verification:**
```python
print(f"[verify] Created notebook id={nb.id} title={nb.title}")
```

**Tests:**

| Test function | Operations | Verified |
|---|---|---|
| `test_live_notebooks_list` | GET /notebooks | Response is list; each item has `id`, `title`; count ≥ 0 |
| `test_live_notebook_create_and_delete` | POST notebook → GET → DELETE | Created id matches read-back; title round-trips; DELETE returns 204/200 |
| `test_live_notebook_create_verifies_fields` | POST notebook with specific title | Returned `title` == submitted `title`; `id` is non-empty string |
| `test_live_notebook_delete_then_get_404` | DELETE → GET same id | GET after DELETE raises `NotFoundError` or returns 404 status |
| `test_live_sources_list_empty_notebook` | POST notebook → GET sources | Empty source list returned; no crash |
| `test_live_source_add_url` | POST notebook → POST source (url) → GET sources | Source appears in list; `type="url"`; submitted URL present |
| `test_live_source_add_pdf` | POST notebook → upload PDF → GET sources | Source appears in list; `type="pdf"`; filename present |
| `test_live_source_list_reflects_added_url` | add-url → list sources → verify count | Count before and after differ by 1; new source has correct URL |
| `test_live_source_list_after_multiple_adds` | add 3 URLs → list sources | All 3 sources appear; no duplicates; each has required fields |
| `test_live_auth_status_shows_valid` | GET auth status | Returns non-empty identity (email or user id) |
| `test_live_notebooks_list_json_output` | CLI --json notebooks list | stdout parses as JSON array; each element has `id`, `title` |
| `test_live_sources_list_json_output` | CLI --json sources list --notebook-id {id} | stdout parses as JSON array; each element has `id`, `type` |
| `test_live_notebook_create_json_flag` | CLI --json notebooks create --title "Test" | stdout parses as JSON object; `id` field present |
| `test_live_cleanup_deletes_test_notebooks` | DELETE all notebooks created in session | Verify none remain via list |

**Expected count: 14**

---

### 3.3 CLI Subprocess Tests (`TestCLISubprocess`)

Tests the installed `cli-web-notebooklm` binary via `subprocess.run`.
Uses `_resolve_cli` to locate the command — never hardcodes paths.
Does NOT set `cwd` — the installed command must work from any directory.

**`_resolve_cli` helper (copy verbatim into `test_e2e.py`):**

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
```

**Class structure:**

```python
class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-web-notebooklm")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True,
            check=check,
        )
```

**Tests:**

| Test function | Command invoked | Verified |
|---|---|---|
| `test_subprocess_help` | `--help` | Exit code 0; output contains "notebooks" and "sources" |
| `test_subprocess_notebooks_help` | `notebooks --help` | Exit code 0; contains "list", "create", "delete" subcommands |
| `test_subprocess_sources_help` | `sources --help` | Exit code 0; contains "add-url", "add-pdf", "list" subcommands |
| `test_subprocess_notebooks_list_json` | `--json notebooks list` | Exit code 0; stdout is valid JSON array |
| `test_subprocess_notebook_create_json` | `--json notebooks create --title "Subprocess Test"` | Exit code 0; stdout JSON has `id` field |
| `test_subprocess_source_add_url_json` | `--json sources add-url --notebook-id {id} --url https://example.com` | Exit code 0; stdout JSON has `type="url"` |
| `test_subprocess_missing_required_arg_exits_nonzero` | `notebooks create` (no `--title`) | Exit code != 0; stderr explains missing argument |
| `test_subprocess_invalid_command_exits_nonzero` | `notebooks frobnicate` | Exit code != 0; stderr says "No such command" |
| `test_subprocess_version_flag` | `--version` | Exit code 0; output contains version string |

**Expected count: 9**

CI note: run subprocess tests with `CLI_WEB_FORCE_INSTALLED=1` to ensure
the installed package (not the source fallback) is exercised. Confirm
`[_resolve_cli] Using installed command:` appears in captured output.

---

## 4. Realistic Workflow Scenarios

These multi-step scenarios simulate real user tasks. Each is a single pytest
function that chains operations and verifies round-trip consistency.

---

### Scenario 1: Full Notebook Lifecycle

**Simulates:** A user creating a new research notebook, verifying it appears
in the list, then cleaning up.

**Operations:**
1. `POST /notebooks` — create with title "Lifecycle Test {uuid}"
2. `GET /notebooks/{id}` — read back by id
3. `GET /notebooks` — list all notebooks
4. `DELETE /notebooks/{id}` — delete
5. `GET /notebooks/{id}` — confirm 404

**Verified:**
- Step 2: returned `title` == submitted title; `id` matches step 1 id
- Step 3: notebook with step 1 id appears in list
- Step 4: response is 200/204 (no error)
- Step 5: raises `NotFoundError` or response status is 404
- Print: `[verify] Notebook id={id} title={title} — lifecycle complete`

**Test function:** `test_scenario_notebook_full_lifecycle`

---

### Scenario 2: Add URL Source to Notebook

**Simulates:** A user adding a web article as a source and confirming it
is indexed.

**Operations:**
1. `POST /notebooks` — create notebook
2. `POST /notebooks/{id}/sources` — add URL `https://en.wikipedia.org/wiki/Python_(programming_language)`
3. `GET /notebooks/{id}/sources` — list sources
4. `DELETE /notebooks/{id}` — cleanup

**Verified:**
- Step 2: returned source `type == "url"`; `url` field matches submitted URL
- Step 3: source count == 1; source id from step 2 appears in list
- Each source in list has `id`, `type`, `display_name` fields
- Print: `[verify] Source id={id} type=url url={url}`

**Test function:** `test_scenario_add_url_source`

---

### Scenario 3: Add PDF Source to Notebook

**Simulates:** A user uploading a local PDF for analysis.

**Operations:**
1. Create a temporary PDF file (minimal valid PDF bytes) in `/tmp/`
2. `POST /notebooks` — create notebook
3. `POST /notebooks/{id}/sources` — upload PDF via multipart/form-data
4. `GET /notebooks/{id}/sources` — list sources
5. Cleanup: delete notebook, delete temp file

**Verified:**
- Step 3: returned source `type == "pdf"`; filename in `display_name`
- Step 4: source appears in list with correct `type`
- Print: `[verify] PDF source id={id} filename={filename}`

**Test function:** `test_scenario_add_pdf_source`

---

### Scenario 4: Multiple Sources in One Notebook

**Simulates:** A user building a multi-source research project.

**Operations:**
1. `POST /notebooks` — create notebook
2. Add 3 URL sources (different Wikipedia URLs)
3. `GET /notebooks/{id}/sources` — list all sources
4. Verify count and no duplicates
5. `DELETE /notebooks/{id}` — cleanup

**Verified:**
- Source list count == 3
- All 3 source ids from step 2 appear in the list
- No duplicate ids in the list
- Each source has `id`, `type="url"`, `display_name`
- Print: `[verify] 3 sources created: {id1}, {id2}, {id3}`

**Test function:** `test_scenario_multiple_sources_same_notebook`

---

### Scenario 5: Auth Token Expiry and Refresh

**Simulates:** Long-running session where the access token expires mid-use.

**Operations:**
1. Load auth — verify `is_valid()` returns `True`
2. Artificially set `expires_at` to past timestamp in memory
3. Call `get_headers()` — expect `AuthError` OR automatic refresh triggered
4. If refresh is supported: verify new token stored, `is_valid()` returns `True`
5. If refresh not supported: verify error message includes `cli-web-notebooklm auth login`

**Verified:**
- Either refresh succeeds and new token has future `expires_at`
- Or error message is actionable (not a bare traceback)
- `auth.json` permissions remain `0o600` after any write

**Test function:** `test_scenario_auth_token_expiry_handling`

---

### Scenario 6: CLI Subprocess Full Workflow

**Simulates:** An agent or CI pipeline using the installed binary end-to-end.

**Operations (all via subprocess):**
1. `cli-web-notebooklm --json notebooks create --title "Agent Workflow Test"`
   → parse JSON → extract `id`
2. `cli-web-notebooklm --json sources add-url --notebook-id {id} --url https://example.com`
   → parse JSON → extract source `id`
3. `cli-web-notebooklm --json sources list --notebook-id {id}`
   → parse JSON → verify source appears
4. `cli-web-notebooklm --json notebooks delete --id {id}`
   → verify exit code 0

**Verified:**
- All subprocess calls exit with code 0
- All `--json` outputs are parseable JSON
- Notebook `id` from step 1 is used correctly in steps 2-4
- Source from step 2 appears in step 3 list
- `[_resolve_cli] Using installed command:` in output when `CLI_WEB_FORCE_INSTALLED=1`

**Test function:** `test_scenario_subprocess_agent_workflow`

---

## 5. Edge Cases Inventory

The following edge cases must be covered across unit and fixture layers.
Each maps to one or more specific test functions listed above.

| Edge case | Layer | Test function |
|---|---|---|
| Missing auth.json | Unit | `test_auth_load_raises_if_file_missing` |
| Expired token | Unit | `test_auth_is_valid_returns_false_when_expired` |
| Token refresh failure | Unit | `test_auth_refresh_posts_to_token_endpoint` |
| 401 Unauthorized | Unit + Fixture | `test_client_raises_on_401`, `test_fixture_401_raises_auth_error` |
| 403 Forbidden | Unit | `test_client_raises_on_403` |
| 404 Not Found | Unit + Fixture | `test_client_raises_on_404`, `test_fixture_404_raises_not_found_error` |
| 429 Rate limit | Unit + Fixture | `test_client_rate_limit_triggers_backoff`, `test_fixture_429_triggers_backoff` |
| 500 Server error | Unit | `test_client_raises_on_500` |
| Malformed JSON response | Unit | `test_client_raises_on_malformed_json` |
| Missing required CLI arg | Subprocess | `test_subprocess_missing_required_arg_exits_nonzero` |
| Unknown subcommand | Subprocess | `test_subprocess_invalid_command_exits_nonzero` |
| Empty notebooks list | Live | `test_live_notebooks_list` (count may be 0) |
| Empty sources list | Live | `test_live_sources_list_empty_notebook` |
| Delete non-existent notebook | Live | `test_live_notebook_delete_then_get_404` |
| PDF upload with invalid file | (future Phase 6 extension) | — |
| Notebook title with special characters | (future Phase 6 extension) | — |

---

## 6. Test Infrastructure Requirements

### Dependencies (`tests/requirements-test.txt`)

```
pytest>=7.0
pytest-cov
responses          # HTTP mocking alternative to unittest.mock
httpx              # If client uses httpx (needed for mocking)
```

### Running tests

```bash
# Unit tests only (no auth required)
cd notebooklm/agent-harness
python -m pytest cli_web/notebooklm/tests/test_core.py -v

# All tests including live E2E (auth required)
python -m pytest cli_web/notebooklm/tests/ -v --tb=short

# Subprocess tests against installed command
CLI_WEB_FORCE_INSTALLED=1 python -m pytest cli_web/notebooklm/tests/ -v -s -k subprocess

# Coverage report
python -m pytest cli_web/notebooklm/tests/test_core.py --cov=cli_web/notebooklm/core --cov-report=term-missing
```

### Coverage target

>80% line coverage on `core/client.py` and `core/auth.py`.
`core/models.py` should reach >90% — it is pure data transformation.

---

## 7. What Makes a Test Invalid (Rejection Criteria)

The following patterns are not accepted in this test suite:

- `pytest.skip()` on missing auth — tests MUST `pytest.fail()` with instructions
- Subprocess tests with hardcoded module paths instead of `_resolve_cli()`
- Subprocess tests that set `cwd` — installed commands must work from any directory
- Live tests that only create entities without reading them back
- Fixture tests that do not verify specific response body fields (checking
  status 200 alone is not sufficient)
- Unit tests that make real network calls
- Bare `except:` blocks in test helpers

---

*Part 2 (test results) will be appended here after running the suite.*
