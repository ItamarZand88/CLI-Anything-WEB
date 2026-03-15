# Test Plan — cli-web-notebooklm

## Unit Tests (test_core.py) — Mocked HTTP

### Session Extraction
- `test_extract_session_params_valid` — Extracts at, f_sid, bl from realistic HTML.
- `test_extract_session_params_missing_at` — Raises ValueError when SNlM0e absent.
- `test_extract_session_params_missing_sid` — Raises ValueError when FdrFJe absent.
- `test_extract_session_params_missing_bl` — Raises ValueError when cfb2h absent.

### Auth
- `test_save_and_load_cookies` — Round-trip save/load through auth.json.
- `test_load_cookies_missing_file` — Raises FileNotFoundError.
- `test_validate_cookies_all_present` — Returns empty list when complete.
- `test_validate_cookies_missing` — Returns list of missing cookie names.
- `test_build_cookie_header` — Produces correct "key=val; key=val" format.

### Client — batchexecute Parsing
- `test_parse_batchexecute_simple` — Parses a standard wrapped response.
- `test_parse_batchexecute_malformed` — Raises ValueError on garbage.
- `test_extract_chunks_single` — Extracts one length-prefixed chunk.
- `test_extract_chunks_multi` — Extracts multiple chunks.

### Client — RPC Call (mocked HTTP)
- `test_rpc_list_notebooks` — Sends correct f.req body, returns parsed data.
- `test_rpc_http_error` — Raises on 401/403/500 responses.

### Models
- `test_notebook_to_dict` — Serialization round-trip.
- `test_source_to_dict` — Serialization round-trip.
- `test_chat_session_to_dict` — Nested serialization.

### Output
- `test_output_json` — Produces valid JSON to stdout.
- `test_truncate_short` — No change on short strings.
- `test_truncate_long` — Truncates with ellipsis.

## End-to-End Tests (test_e2e.py) — Subprocess

### Auth
- `test_auth_status_no_cookies` — Exits non-zero, outputs error message.
- `test_help` — `--help` exits 0, output contains command groups.
- `test_version` — `--version` exits 0, output contains version.

### Notebooks (requires auth)
- `test_notebooks_list_json` — Exits 0, output is valid JSON array.
- `test_notebooks_list_table` — Exits 0, output contains header text.

### Chat (requires auth)
- `test_chat_query_json` — Exits 0, response contains question and response keys.

## Failure Policy
- All tests that require authentication MUST FAIL (not skip) when auth is missing.
- The `_resolve_cli()` helper locates the installed entry point for subprocess invocation.

---

## Part 2 — Test Results

### Run Date: 2026-03-15

### Unit Tests (test_core.py)
```
cli_web/notebooklm/tests/test_core.py::test_extract_session_params_valid PASSED
cli_web/notebooklm/tests/test_core.py::test_extract_session_params_missing_at PASSED
cli_web/notebooklm/tests/test_core.py::test_extract_session_params_missing_sid PASSED
cli_web/notebooklm/tests/test_core.py::test_extract_session_params_missing_bl PASSED
cli_web/notebooklm/tests/test_core.py::test_save_and_load_cookies PASSED
cli_web/notebooklm/tests/test_core.py::test_load_cookies_missing_file PASSED
cli_web/notebooklm/tests/test_core.py::test_validate_cookies_all_present PASSED
cli_web/notebooklm/tests/test_core.py::test_validate_cookies_missing PASSED
cli_web/notebooklm/tests/test_core.py::test_build_cookie_header PASSED
cli_web/notebooklm/tests/test_core.py::test_parse_batchexecute_simple PASSED
cli_web/notebooklm/tests/test_core.py::test_parse_batchexecute_malformed PASSED
cli_web/notebooklm/tests/test_core.py::test_extract_chunks_single PASSED
cli_web/notebooklm/tests/test_core.py::test_extract_chunks_multi PASSED
cli_web/notebooklm/tests/test_core.py::test_rpc_list_notebooks PASSED
cli_web/notebooklm/tests/test_core.py::test_rpc_http_error PASSED
cli_web/notebooklm/tests/test_core.py::test_notebook_to_dict PASSED
cli_web/notebooklm/tests/test_core.py::test_source_to_dict PASSED
cli_web/notebooklm/tests/test_core.py::test_chat_session_to_dict PASSED
cli_web/notebooklm/tests/test_core.py::test_output_json PASSED
cli_web/notebooklm/tests/test_core.py::test_truncate_short PASSED
cli_web/notebooklm/tests/test_core.py::test_truncate_long PASSED

21 passed in 0.22s
```

### E2E Tests (test_e2e.py)
```
cli_web/notebooklm/tests/test_e2e.py::test_cli_help PASSED
cli_web/notebooklm/tests/test_e2e.py::test_cli_version PASSED
cli_web/notebooklm/tests/test_e2e.py::test_auth_status_no_cookies PASSED
cli_web/notebooklm/tests/test_e2e.py::test_subprocess_help PASSED
cli_web/notebooklm/tests/test_e2e.py::test_subprocess_version PASSED
cli_web/notebooklm/tests/test_e2e.py::test_notebooks_list_json FAILED (auth not configured)
cli_web/notebooklm/tests/test_e2e.py::test_notebooks_list_table FAILED (auth not configured)
cli_web/notebooklm/tests/test_e2e.py::test_chat_query_json FAILED (auth not configured)

5 passed, 3 failed in 2.66s
```

### Summary
| Suite | Total | Passed | Failed | Notes |
|-------|-------|--------|--------|-------|
| Unit (test_core.py) | 21 | 21 | 0 | All mocked, deterministic |
| E2E (test_e2e.py) | 8 | 5 | 3 | 3 failures = auth not configured (expected) |
| **Total** | **29** | **26** | **3** | Auth-dependent failures per HARNESS.md spec |
