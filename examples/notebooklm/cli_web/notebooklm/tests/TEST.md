# TEST.md — cli-web-notebooklm

## Part 1: Test Plan

### Test Inventory
- `test_core.py`: ~15 unit tests planned (RPC encoder/decoder, auth, models)
- `test_e2e.py`: ~8 E2E tests planned (live API calls, subprocess)

### Unit Test Plan

#### RPC Encoder (`core/rpc/encoder.py`)
- `test_encode_request` — verify URL-encoded form body structure
- `test_build_query_params` — verify query string params

#### RPC Decoder (`core/rpc/decoder.py`)
- `test_decode_simple_response` — parse basic batchexecute response
- `test_decode_multibyte_response` — handle Hebrew/emoji (byte vs char)
- `test_decode_multiple_chunks` — parse multiple length-prefixed chunks
- `test_extract_rpc_data` — extract specific RPC from envelopes
- `test_parse_rpc_result` — full decode + parse pipeline

#### Auth (`core/auth.py`)
- `test_cookies_to_header` — filter and format cookies
- `test_check_required_cookies` — validate required cookies present
- `test_extract_tokens_from_html` — regex extraction from page HTML
- `test_save_load_cookies` — roundtrip save/load

#### Models (`core/models.py`)
- `test_parse_notebook` — parse notebook from raw API data
- `test_parse_source` — parse source with various types
- `test_parse_artifact` — parse artifact with media URLs
- `test_parse_timestamp` — convert [secs, nanos] to ISO

### E2E Test Plan (Live)

1. **Auth status** — verify cookies present + live validation
2. **List notebooks** — verify returns non-empty list with expected fields
3. **Get notebook** — verify specific notebook by ID
4. **List sources** — verify sources for a notebook
5. **List artifacts** — verify artifacts for a notebook
6. **Chat suggested** — verify summary + questions
7. **Subprocess: --help** — verify installed CLI responds
8. **Subprocess: --json notebooks list** — verify JSON output

## Part 2: Test Results

**Date:** 2026-03-15
**Total tests:** 32
**Pass rate:** 100% (32/32)

### pytest output:

```
test_core.py::TestEncoder::test_encode_request_basic PASSED
test_core.py::TestEncoder::test_encode_request_with_list PASSED
test_core.py::TestEncoder::test_build_query_params PASSED
test_core.py::TestDecoder::test_decode_simple_response PASSED
test_core.py::TestDecoder::test_decode_multibyte_response PASSED
test_core.py::TestDecoder::test_decode_multiple_chunks PASSED
test_core.py::TestDecoder::test_extract_rpc_data PASSED
test_core.py::TestDecoder::test_extract_rpc_data_not_found PASSED
test_core.py::TestDecoder::test_parse_rpc_result PASSED
test_core.py::TestAuth::test_cookies_to_header_filters_domain PASSED
test_core.py::TestAuth::test_cookies_to_header_deduplicates PASSED
test_core.py::TestAuth::test_check_required_cookies_all_present PASSED
test_core.py::TestAuth::test_check_required_cookies_missing PASSED
test_core.py::TestAuth::test_extract_tokens_from_html PASSED
test_core.py::TestAuth::test_extract_tokens_missing PASSED
test_core.py::TestModels::test_parse_timestamp PASSED
test_core.py::TestModels::test_parse_timestamp_none PASSED
test_core.py::TestModels::test_parse_notebook PASSED
test_core.py::TestModels::test_parse_source PASSED
test_core.py::TestModels::test_parse_source_empty PASSED
test_core.py::TestModels::test_parse_artifact PASSED
test_e2e.py::TestAuthLive::test_auth_cookies_present PASSED
test_e2e.py::TestAuthLive::test_auth_live_validation PASSED
test_e2e.py::TestNotebooksLive::test_list_notebooks PASSED
test_e2e.py::TestNotebooksLive::test_get_notebook PASSED
test_e2e.py::TestSourcesLive::test_list_sources PASSED
test_e2e.py::TestArtifactsLive::test_list_artifacts PASSED
test_e2e.py::TestChatLive::test_get_summary PASSED
test_e2e.py::TestCLISubprocess::test_help PASSED
test_e2e.py::TestCLISubprocess::test_version PASSED
test_e2e.py::TestCLISubprocess::test_json_notebooks_list PASSED
test_e2e.py::TestCLISubprocess::test_json_auth_status PASSED

============================= 32 passed in 20.58s =============================
```

### Summary
- 21 unit tests (RPC encoder/decoder, auth, models) — all pass
- 7 E2E live API tests (auth, notebooks, sources, artifacts, chat) — all pass
- 4 subprocess tests (help, version, JSON list, JSON auth) — all pass
