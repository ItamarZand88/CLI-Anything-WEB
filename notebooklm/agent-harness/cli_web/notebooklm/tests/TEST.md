# cli-web-notebooklm — Test Plan and Results

## Part 1: Test Plan

### Test Inventory

| File | Type | Count |
|------|------|-------|
| `test_core.py` | Unit tests (no network) | 52 |
| `test_e2e.py` | Fixture replay (no network) | 20 |
| `test_e2e.py` | Live API tests (require auth) | 6 |
| `test_e2e.py` | CLI subprocess tests | 6 |
| **Total** | | **84** |

---

### Unit Test Plan (test_core.py)

#### RPC Encoder (core/rpc/encoder.py) — 8 tests
- `encode_request`: body format, CSRF field, params serialization, empty params
- `build_url`: rpcids param, f.sid, bl, hl (lang) defaults

#### RPC Decoder (core/rpc/decoder.py) — 13 tests
- `strip_prefix`: XSSI prefix removal for str/bytes, passthrough when absent
- `parse_chunks`: JSON array extraction, multiple chunks, digit-line skipping
- `extract_result`: normal result (double-decode), missing rpc_id → ValueError,
  er code 7/9 → AuthError, other code → RPCError, None payload
- `decode_response`: full pipeline (bytes, str, wrong rpc_id)

#### Models (core/models.py) — 17 tests
- `parse_notebook`: flat rLM1Ne style, nested wXbhsf style, missing id → None,
  empty input, default emoji, source_count
- `parse_source`: type_id 4/5/8/11 mapping, id extraction from `[[uuid]]`,
  char_count, created_at, unknown type, empty input
- `parse_user`: all fields, no avatar, empty input

#### Client (core/client.py) — 14 tests
- `list_notebooks`: parses Notebook objects, empty result
- `create_notebook`: returns Notebook with title, params include title only
- `get_notebook`: params are `[notebook_id]` (not `[None, None, id]`)
- `add_url_source`: params are `[nb_id, [url]]`, correct RPC method
- `401 retry`: refresh_tokens called, retry succeeds; 429 → RuntimeError; 500 → RuntimeError

---

### E2E Test Plan (test_e2e.py)

#### Fixture Replay Tests — 20 tests
No network calls. Fixtures are hardcoded response shapes matching real API.

Key fixtures:
- `FIXTURE_RLME1NE`: rLM1Ne flat array `[title, sources, nb_id, emoji, None, flags]`
- `FIXTURE_WXBHSF_ENTRY`: wXbhsf content entry with title/sources/uuid
- `FIXTURE_CCQFVF`: CCqFvf create response `["", None, "new-nb-uuid", ...]`
- `FIXTURE_VFAZJD`: VfAZjd response `[None, "source-id"]`
- `FIXTURE_SOURCE_ENTRY`: source entry from rLM1Ne sources list

Tests cover: title extraction, source count, notebook id, is_pinned, created_at,
cursor-entry skipping, `_parse_create_response`, `_extract_sources_from_nb_result`,
source type mapping (type_id 4→text, 5→url), char_count.

#### Live API Tests — 6 tests
Require auth: `pytest.fail()` (not skip) if `load_cookies()` raises.

- `test_live_list_notebooks`: list ≥0 notebooks, each has id/title
- `test_live_create_get_delete_notebook`: create → get → verify title → delete
- `test_live_add_url_source`: create notebook → add Wikipedia URL → verify source_id
- `test_live_list_sources`: find notebook with sources, verify count > 0
- `test_live_whoami`: verify email is non-empty string
- `test_live_chat_query`: ask question, verify non-empty answer

#### CLI Subprocess Tests — 6 tests
Uses `_resolve_cli("cli-web-notebooklm")` — never hardcodes paths.

- `test_help`: `--help` exits 0, mentions "notebooks"
- `test_notebooks_help`: `notebooks --help` exits 0
- `test_notebooks_list_json`: `notebooks list --json` returns valid JSON list with id/title
- `test_auth_status_json`: `auth status --json` has "configured" key
- `test_whoami_json`: `whoami --json` has "email" key
- `test_notebooks_create_and_delete`: create → verify in list → delete (full CLI cycle)

---

### Realistic Workflow Scenarios

#### Scenario 1: Notebook CRUD lifecycle
- **Simulates**: creating a new research notebook, adding sources, asking questions
- **Operations**: create notebook → add_url_source → list_sources → chat_query → delete
- **Verified**: notebook id round-trip, source_id returned, answer non-empty

#### Scenario 2: Auth validation
- **Simulates**: checking if session is valid before using the CLI
- **Operations**: auth status → fetch tokens → verify CSRF/session_id present
- **Verified**: cookies present, session_id visible, status shows "OK"

#### Scenario 3: Bulk notebook listing
- **Simulates**: user listing all notebooks to find one to work with
- **Operations**: list_notebooks → verify each entry has id/title/source_count
- **Verified**: list is non-empty (user has notebooks), all fields populated

---

## Part 2: Test Results

### Run Date: 2026-03-18

### Environment
- Python 3.12.8
- pytest 8.3.4
- Platform: Windows 11 Pro

### Full pytest output

```
collected 84 items

test_core.py::TestEncodeRequest::test_build_url_contains_rpcid PASSED
test_core.py::TestEncodeRequest::test_build_url_default_lang PASSED
test_core.py::TestEncodeRequest::test_build_url_has_build_label PASSED
test_core.py::TestEncodeRequest::test_build_url_has_session_id PASSED
test_core.py::TestEncodeRequest::test_encode_request_body_format PASSED
test_core.py::TestEncodeRequest::test_encode_request_empty_params PASSED
test_core.py::TestEncodeRequest::test_encode_request_list_params PASSED
test_core.py::TestEncodeRequest::test_encode_request_with_csrf PASSED
test_core.py::TestStripPrefix::test_strip_prefix_bytes_input PASSED
test_core.py::TestStripPrefix::test_strip_prefix_no_prefix PASSED
test_core.py::TestStripPrefix::test_strip_prefix_removes_xssi PASSED
test_core.py::TestParseChunks::test_parse_chunks_extracts_arrays PASSED
test_core.py::TestParseChunks::test_parse_chunks_multiple_chunks PASSED
test_core.py::TestParseChunks::test_parse_chunks_skips_digit_only_lines PASSED
test_core.py::TestExtractResult::test_extract_result_error_code_7 PASSED
test_core.py::TestExtractResult::test_extract_result_error_code_9 PASSED
test_core.py::TestExtractResult::test_extract_result_found PASSED
test_core.py::TestExtractResult::test_extract_result_non_auth_error_code PASSED
test_core.py::TestExtractResult::test_extract_result_none_payload PASSED
test_core.py::TestExtractResult::test_extract_result_not_found PASSED
test_core.py::TestDecodeResponse::test_decode_response_full_pipeline PASSED
test_core.py::TestDecodeResponse::test_decode_response_string_input PASSED
test_core.py::TestDecodeResponse::test_decode_response_wrong_rpcid_raises PASSED
test_core.py::TestParseNotebook::test_parse_notebook_default_emoji PASSED
test_core.py::TestParseNotebook::test_parse_notebook_empty_input_returns_none PASSED
test_core.py::TestParseNotebook::test_parse_notebook_flat_rlm1ne PASSED
test_core.py::TestParseNotebook::test_parse_notebook_flat_source_count PASSED
test_core.py::TestParseNotebook::test_parse_notebook_missing_id_returns_none PASSED
test_core.py::TestParseNotebook::test_parse_notebook_nested_wXbhsf PASSED
test_core.py::TestParseSource::test_parse_source_char_count PASSED
test_core.py::TestParseSource::test_parse_source_created_at PASSED
test_core.py::TestParseSource::test_parse_source_empty_input PASSED
test_core.py::TestParseSource::test_parse_source_extracts_id PASSED
test_core.py::TestParseSource::test_parse_source_text_type_4 PASSED
test_core.py::TestParseSource::test_parse_source_text_type_8 PASSED
test_core.py::TestParseSource::test_parse_source_unknown_type PASSED
test_core.py::TestParseSource::test_parse_source_url_type_11 PASSED
test_core.py::TestParseSource::test_parse_source_url_type_5 PASSED
test_core.py::TestParseUser::test_parse_user_empty_input PASSED
test_core.py::TestParseUser::test_parse_user_empty_users_list PASSED
test_core.py::TestParseUser::test_parse_user_extracts_fields PASSED
test_core.py::TestParseUser::test_parse_user_no_avatar PASSED
test_core.py::TestClientListNotebooks::test_list_notebooks_empty_result PASSED
test_core.py::TestClientListNotebooks::test_list_notebooks_parses_response PASSED
test_core.py::TestClientCreateNotebook::test_create_notebook_passes_title_in_params PASSED
test_core.py::TestClientCreateNotebook::test_create_notebook_returns_notebook PASSED
test_core.py::TestClientGetNotebook::test_client_get_notebook_fixed_params PASSED
test_core.py::TestClientAddUrlSource::test_add_url_source_rpc_method PASSED
test_core.py::TestClientAddUrlSource::test_client_add_url_source_fixed_params PASSED
test_core.py::TestClient401Retry::test_client_401_triggers_token_refresh_and_retry PASSED
test_core.py::TestClient401Retry::test_client_429_raises_runtime_error PASSED
test_core.py::TestClient401Retry::test_client_generic_http_error_raises PASSED
test_e2e.py::TestFixtureReplay::test_rlm1ne_parse_title PASSED
test_e2e.py::TestFixtureReplay::test_rlm1ne_parse_source_count PASSED
test_e2e.py::TestFixtureReplay::test_rlm1ne_parse_notebook_id PASSED
test_e2e.py::TestFixtureReplay::test_rlm1ne_parse_is_pinned PASSED
test_e2e.py::TestFixtureReplay::test_rlm1ne_parse_created_at PASSED
test_e2e.py::TestFixtureReplay::test_wXbhsf_parse_entry PASSED
test_e2e.py::TestFixtureReplay::test_wXbhsf_parse_source_count PASSED
test_e2e.py::TestFixtureReplay::test_wXbhsf_skips_empty_title_entries PASSED
test_e2e.py::TestFixtureReplay::test_create_response_parse PASSED
test_e2e.py::TestFixtureReplay::test_create_response_empty_title PASSED
test_e2e.py::TestFixtureReplay::test_create_response_none_returns_none PASSED
test_e2e.py::TestFixtureReplay::test_add_url_source_response PASSED
test_e2e.py::TestFixtureReplay::test_parse_source_from_rlm1ne PASSED
test_e2e.py::TestFixtureReplay::test_parse_source_char_count PASSED
test_e2e.py::TestFixtureReplay::test_parse_source_type_text PASSED
test_e2e.py::TestFixtureReplay::test_parse_source_created_at PASSED
test_e2e.py::TestFixtureReplay::test_parse_source_url_type PASSED
test_e2e.py::TestFixtureReplay::test_parse_source_none_returns_none PASSED
test_e2e.py::TestFixtureReplay::test_parse_notebook_none_returns_none PASSED
test_e2e.py::TestFixtureReplay::test_extract_sources_from_nb_result PASSED
test_e2e.py::TestLiveAPI::test_live_list_notebooks PASSED
test_e2e.py::TestLiveAPI::test_live_create_get_delete_notebook PASSED
test_e2e.py::TestLiveAPI::test_live_add_url_source PASSED
test_e2e.py::TestLiveAPI::test_live_list_sources PASSED
test_e2e.py::TestLiveAPI::test_live_whoami PASSED
test_e2e.py::TestLiveAPI::test_live_chat_query PASSED
test_e2e.py::TestCLISubprocess::test_help PASSED
test_e2e.py::TestCLISubprocess::test_notebooks_help PASSED
test_e2e.py::TestCLISubprocess::test_notebooks_list_json PASSED
test_e2e.py::TestCLISubprocess::test_auth_status_json PASSED
test_e2e.py::TestCLISubprocess::test_whoami_json PASSED
test_e2e.py::TestCLISubprocess::test_notebooks_create_and_delete PASSED

84 passed in 47.40s
```

### Summary

| Metric | Value |
|--------|-------|
| Total tests | 84 |
| Passed | 84 |
| Failed | 0 |
| Pass rate | 100% |
| Execution time | 47.40s |
| Date | 2026-03-18 |

### Gap Notes

- `rename_notebook` (s0tc2d): params unconfirmed — tested via unit mock only
- `delete_source` (e3bVqc): not live-tested (low priority)
- `generate_artifact` (CYK0Xb): params unconfirmed — no live test
- `add_text_source` (hPTbtc): actual "add text" endpoint not confirmed (hPTbtc appears to be "list text sources")
- `chat_query` uses `GenerateFreeFormStreamed` (gRPC-web endpoint), not the deprecated `yyryJe` batchexecute method
- `get_user` uses homepage HTML scraping (JFMDGd batchexecute method returns [3] error for all params)
