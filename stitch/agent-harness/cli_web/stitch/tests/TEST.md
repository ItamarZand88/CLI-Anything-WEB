# TEST.md — cli-web-stitch Test Plan & Results

## Part 1: Test Plan

### Test Files

| File | Type | Tests | Description |
|------|------|-------|-------------|
| `test_core.py` | Unit | 107 | Core modules with mocked HTTP |
| `test_e2e.py` | E2E + Subprocess | 10 | Live API + installed CLI |

### Unit Tests (`test_core.py`)

**RPC Codec (16 tests)**
- Encoder: `encode_request` body format, empty params, `build_url` with/without build label
- Decoder: `strip_prefix` bytes/str, `parse_chunks` extraction, `extract_result` wrb.fr lookup, error codes 7/9 → AuthError, other codes → RPCError, missing rpc_id → ValueError, `decode_response` full pipeline

**Exceptions (11 tests)**
- Inheritance chain (all extend StitchError)
- AuthError.recoverable, RateLimitError.retry_after, ServerError.status_code
- Default values and custom values

**Model Parsers (17 tests)**
- `parse_project`: full data, missing fields, short list, None/empty/non-list
- `parse_screen`: full data, missing thumb/html, missing id
- `parse_session`: full data, pending status, string prompt

**Client (11 tests)**
- `list_projects` parsing with mocked httpx
- HTTP status → exception mapping: 401/403→AuthError (with retry), 429→RateLimitError, 500→ServerError, 404→NotFoundError
- Network errors: ConnectError, TimeoutException, RequestError → NetworkError

**Helpers (27 tests)**
- `resolve_partial_id`: exact, prefix, ambiguous, no match, case-insensitive
- `sanitize_filename`: invalid chars, empty, dots, truncation
- `handle_errors`: exit codes 1/2/130, JSON mode error output
- `get/set_context_value`: round-trip, missing key, overwrite

**Auth (14 tests)**
- `load_cookies`: from file, from env var, missing file, list format
- `_extract_cookies`: .google.com priority, regional domains, filtering
- `get_auth_status`: not configured, valid, expired

### E2E Live Tests (`test_e2e.py`)

**Prerequisite:** Auth configured via `cli-web-stitch auth login`

| Test | Verifies |
|------|----------|
| `test_auth_status` | Auth is valid, session active |
| `test_list_projects` | Returns ≥1 project with id, resource_name |
| `test_get_project` | Fetches by ID, round-trip ID match |
| `test_list_screens` | Returns ≥1 screen with id, name for ready project |
| `test_design_history` | Lists sessions with resource_name |
| `test_delete_project` | Delete + verify removal from list |

**Note:** Create round-trip is limited because Stitch's CREATE_PROJECT RPC is a client-side operation (browser generates the project ID). Project creation requires SEND_PROMPT which triggers actual AI generation.

### Subprocess Tests (`test_e2e.py`)

| Test | Verifies |
|------|----------|
| `test_help` | `--help` exits 0, contains "stitch" |
| `test_auth_status_json` | `auth status --json` returns valid JSON |
| `test_projects_list_json` | `projects list --json` returns success with list |
| `test_screens_list_json` | `screens list --project <id> --json` returns success |

---

## Part 2: Test Results

**Date:** 2026-03-22
**Environment:** Windows 11, Python 3.12.8, pytest 8.3.4

### Results Summary

| Metric | Value |
|--------|-------|
| Total tests | 117 |
| Passed | 117 |
| Failed | 0 |
| Skipped | 0 |
| Pass rate | 100% |
| Duration | 53.39s |

### Full Test Output

```
117 passed, 107 warnings in 53.39s
```

All unit tests (107) pass with mocked HTTP. All E2E tests (6) pass against live Stitch API. All subprocess tests (4) pass with installed `cli-web-stitch` binary.
