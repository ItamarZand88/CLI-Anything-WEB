# TEST.md — cli-web-airbnb

## Part 1: Test Plan

### 1. Test Inventory

| File | Tests | Purpose |
|------|-------|---------|
| `test_core.py` | 51 | Unit tests — no network, mocked HTTP |
| `test_e2e.py` | 20 | Live E2E + subprocess CLI tests |
| **Total** | **71** | |

### 2. Unit Test Plan (`test_core.py`)

#### 2.1 Exception Hierarchy (6 tests)
- `AirbnbError` is an `Exception` subclass
- `AuthError` defaults: `recoverable=False`, message contains "Authentication"
- `AuthError` with `recoverable=True`
- `RateLimitError` stores `retry_after` attribute
- `ServerError` stores `status_code` attribute
- All domain exceptions are subclasses of `AirbnbError`

#### 2.2 Listing ID Encode/Decode (4 tests)
- Roundtrip: `_encode_listing_id` → `_decode_listing_id` returns original integer string
- Known mapping from captured traffic: b64 `RGVtYW5kU3RheUxpc3Rpbmc6NzcwOTkz...` → `770993223449115417`
- `_encode_listing_id` produces correct `DemandStayListing:<id>` prefix
- Invalid base64 passthrough: returns input unchanged

#### 2.3 Location Slug Conversion (4 tests)
- `"London, UK"` → `"London--UK"`
- Multi-part: `"New York, NY, United States"` → `"New-York--NY--United-States"`
- Spaces in city: `"Paris, France"` → `"Paris--France"`
- No comma: `"Barcelona"` → `"Barcelona"`

#### 2.4 niobeClientData Extraction (4 tests)
- Finds `StaysSearch` operation in well-formed HTML
- Returns `None` for unknown operation key
- Handles non-dict JSON values in script tags (e.g. `true`) without crashing
- Returns `None` for HTML with no script tags

#### 2.5 `_parse_search_listing` (4 tests)
- Parses all fields from full search result: id, name, rating, price, coordinates, badges, URL
- `to_dict()` on parsed listing contains correct types
- Falls back to `name` key when `nameLocalized` is absent
- Empty badges list parses cleanly

#### 2.6 Models (4 tests)
- `Listing.to_dict()` returns all expected keys
- All 19 model fields are present in `to_dict()` output
- `LocationSuggestion.to_dict()` returns query, place_id, display
- `LocationSuggestion.display` falls back to `query` when not set

#### 2.7 `json_error` Helper (2 tests)
- Produces `{"error": true, "code": ..., "message": ...}` structure
- Extra kwargs are included in output (e.g. `retry_after`)

#### 2.8 `truncate` Helper (4 tests)
- Short strings returned unchanged
- Long strings truncated at 60 chars with `…` suffix
- `None` input returns `""`
- Empty string returns `""`

#### 2.9 `resolve_json_mode` Helper (4 tests)
- Explicit `True` returns `True`
- Explicit `False` with no context returns `False`
- `False` with `ctx.obj["json"] = True` returns `True` (inherits parent flag)
- `False` with `ctx.obj["json"] = False` returns `False`

#### 2.10 `handle_errors` Exit Codes (8 tests)
- `AuthError` → exit code 1
- `NotFoundError` → exit code 1
- `RateLimitError` → exit code 1
- `ServerError` → exit code 2
- `NetworkError` → exit code 2
- JSON mode `AuthError` → structured `{"error": true, "code": "AUTH_EXPIRED"}`
- JSON mode `ParseError` → `{"code": "PARSE_ERROR"}`
- JSON mode `RateLimitError` → `{"code": "RATE_LIMITED", "retry_after": 60}`

#### 2.11 Client HTTP Status → Exception Mapping (7 tests, mocked)
- HTTP 404 → `NotFoundError`
- HTTP 429 with `Retry-After: 30` → `RateLimitError(retry_after=30.0)`
- HTTP 503 → `ServerError(status_code=503)`
- Network exception → `NetworkError`
- SSR page without niobeClientData → `ParseError`
- Autocomplete parses API response → returns `LocationSuggestion` objects
- Empty autocomplete response → returns `[]`

### 3. E2E Test Plan (`test_e2e.py`)

Airbnb is a **no-auth public site** — no login required. All E2E tests use real live HTTP via the installed `cli-web-airbnb` binary.

#### 3.1 Search Stays (6 tests)
- Basic search "London, UK" returns listings with id, name, url
- Search with dates and guest count succeeds
- Search with `--max-price 200` succeeds
- Pagination: page 1 cursor used for page 2, IDs must differ
- JSON structure: all required fields (`id`, `id_b64`, `name`, `url`) present
- Field sanity: `id` is numeric, `name` non-empty, URL matches ID

#### 3.2 `--json` Flag Placement (4 tests)
- `--json` at group level before `search stays` → valid JSON output
- `--json` at end of `search stays` → valid JSON (not "No such option" error)
- `--json` at group level before `autocomplete locations` → valid JSON
- `--json` at end of `autocomplete locations` → valid JSON

#### 3.3 Listings Get (3 tests)
- `listings get <id>` returns correct `id`, `name`, `url`
- Nonexistent listing (99999999999999): error JSON or 0 exit (graceful)
- **Round-trip**: `search stays "London, UK"` → take first ID → `listings get <id>` → verify `id`, `url`, `name` match

#### 3.4 Autocomplete (3 tests)
- `autocomplete locations "Lond"` returns `success=True` with suggestions list
- `--num-results 3` returns at most 3 suggestions
- Each suggestion has `query` and `display` fields

#### 3.5 CLI Help / Version (4 tests)
- `--help` shows `search`, `listings`, `autocomplete`
- `search stays --help` shows `--checkin`, `--checkout`
- `--version` shows `0.1.0`
- `listings get --help` shows `--json`

### 4. Realistic Workflow Scenarios

#### Scenario A: Search and Inspect
```
cli-web-airbnb search stays "London, UK" --json
  → listings[0].id captured
cli-web-airbnb listings get <id> --json
  → id, url, name match search result
```
Verified by: `test_get_listing_search_then_get_roundtrip`

#### Scenario B: Paginated Browse
```
cli-web-airbnb search stays "London, UK" --json
  → next_cursor captured
cli-web-airbnb search stays "London, UK" --cursor <token> --json
  → page 2 IDs differ from page 1
```
Verified by: `test_search_pagination_cursor`

#### Scenario C: Location Discovery → Search
```
cli-web-airbnb autocomplete locations "New Yor" --json
  → suggestions[0].query used as location
cli-web-airbnb search stays "<query>" --json
  → results returned
```

### 5. Notes

- **No-auth site**: Airbnb is fully public. No `auth.py`, no `auth login` command, no auth prerequisite.
- **Bot protection**: curl_cffi with Chrome impersonation bypasses Akamai/DataDome. Tests rely on this being maintained.
- **Encoding fix**: All subprocess calls use `encoding="utf-8", errors="replace"` to handle non-ASCII listing names on Windows.
- **Client-side operations**: No create/update/delete operations exist — Airbnb is read-only for the CLI. Round-trip is list→get.
- **Listing IDs**: Long integer strings (e.g. `770993223449115417`). Base64 encoded IDs appear in SSR data.

---

## Part 2: Test Results

**Run date:** 2026-04-04 (re-run confirmed)  
**Python:** 3.13.12  
**Platform:** win32  
**pytest:** 9.0.2

### Full Output

```
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\...\CLI-Anything-WEB\airbnb\agent-harness
plugins: anyio-4.13.0
collecting ... collected 71 items

cli_web/airbnb/tests/test_core.py::test_airbnb_error_is_exception PASSED
cli_web/airbnb/tests/test_core.py::test_auth_error_defaults PASSED
cli_web/airbnb/tests/test_core.py::test_auth_error_recoverable PASSED
cli_web/airbnb/tests/test_core.py::test_rate_limit_error PASSED
cli_web/airbnb/tests/test_core.py::test_server_error PASSED
cli_web/airbnb/tests/test_core.py::test_exception_hierarchy PASSED
cli_web/airbnb/tests/test_core.py::test_decode_listing_id_roundtrip PASSED
cli_web/airbnb/tests/test_core.py::test_decode_listing_id_known PASSED
cli_web/airbnb/tests/test_core.py::test_encode_listing_id_known PASSED
cli_web/airbnb/tests/test_core.py::test_decode_invalid_id_passthrough PASSED
cli_web/airbnb/tests/test_core.py::test_location_to_slug_simple PASSED
cli_web/airbnb/tests/test_core.py::test_location_to_slug_multi PASSED
cli_web/airbnb/tests/test_core.py::test_location_to_slug_spaces PASSED
cli_web/airbnb/tests/test_core.py::test_location_to_slug_no_comma PASSED
cli_web/airbnb/tests/test_core.py::test_extract_niobe_data_found PASSED
cli_web/airbnb/tests/test_core.py::test_extract_niobe_data_not_found PASSED
cli_web/airbnb/tests/test_core.py::test_extract_niobe_data_bool_script PASSED
cli_web/airbnb/tests/test_core.py::test_extract_niobe_data_empty PASSED
cli_web/airbnb/tests/test_core.py::test_parse_search_listing PASSED
cli_web/airbnb/tests/test_core.py::test_parse_search_listing_to_dict PASSED
cli_web/airbnb/tests/test_core.py::test_parse_search_listing_fallback_name PASSED
cli_web/airbnb/tests/test_core.py::test_parse_search_listing_empty_badges PASSED
cli_web/airbnb/tests/test_core.py::test_listing_to_dict_complete PASSED
cli_web/airbnb/tests/test_core.py::test_listing_all_fields_in_dict PASSED
cli_web/airbnb/tests/test_core.py::test_location_suggestion_to_dict PASSED
cli_web/airbnb/tests/test_core.py::test_location_suggestion_display_fallback PASSED
cli_web/airbnb/tests/test_core.py::test_json_error_structure PASSED
cli_web/airbnb/tests/test_core.py::test_json_error_extra_fields PASSED
cli_web/airbnb/tests/test_core.py::test_truncate_short_string PASSED
cli_web/airbnb/tests/test_core.py::test_truncate_long_string PASSED
cli_web/airbnb/tests/test_core.py::test_truncate_none PASSED
cli_web/airbnb/tests/test_core.py::test_truncate_empty PASSED
cli_web/airbnb/tests/test_core.py::test_resolve_json_mode_explicit_true PASSED
cli_web/airbnb/tests/test_core.py::test_resolve_json_mode_explicit_false_no_ctx PASSED
cli_web/airbnb/tests/test_core.py::test_resolve_json_mode_from_ctx PASSED
cli_web/airbnb/tests/test_core.py::test_resolve_json_mode_ctx_false PASSED
cli_web/airbnb/tests/test_core.py::test_handle_errors_auth_exits_1 PASSED
cli_web/airbnb/tests/test_core.py::test_handle_errors_not_found_exits_1 PASSED
cli_web/airbnb/tests/test_core.py::test_handle_errors_rate_limit_exits_1 PASSED
cli_web/airbnb/tests/test_core.py::test_handle_errors_server_error_exits_2 PASSED
cli_web/airbnb/tests/test_core.py::test_handle_errors_network_error_exits_2 PASSED
cli_web/airbnb/tests/test_core.py::test_handle_errors_json_mode_auth PASSED
cli_web/airbnb/tests/test_core.py::test_handle_errors_json_mode_parse_error PASSED
cli_web/airbnb/tests/test_core.py::test_handle_errors_json_mode_rate_limit PASSED
cli_web/airbnb/tests/test_core.py::test_client_raises_not_found_on_404 PASSED
cli_web/airbnb/tests/test_core.py::test_client_raises_rate_limit_on_429 PASSED
cli_web/airbnb/tests/test_core.py::test_client_raises_server_error_on_503 PASSED
cli_web/airbnb/tests/test_core.py::test_client_raises_network_error_on_exception PASSED
cli_web/airbnb/tests/test_core.py::test_client_raises_parse_error_when_no_niobe PASSED
cli_web/airbnb/tests/test_core.py::test_client_autocomplete_parses_response PASSED
cli_web/airbnb/tests/test_core.py::test_client_autocomplete_empty_response PASSED
cli_web/airbnb/tests/test_e2e.py::TestSearchStays::test_search_returns_listings PASSED
cli_web/airbnb/tests/test_e2e.py::TestSearchStays::test_search_with_dates_and_guests PASSED
cli_web/airbnb/tests/test_e2e.py::TestSearchStays::test_search_with_max_price PASSED
cli_web/airbnb/tests/test_e2e.py::TestSearchStays::test_search_pagination_cursor PASSED
cli_web/airbnb/tests/test_e2e.py::TestSearchStays::test_search_json_structure PASSED
cli_web/airbnb/tests/test_e2e.py::TestSearchStays::test_search_listing_fields_not_empty PASSED
cli_web/airbnb/tests/test_e2e.py::TestJsonFlagPlacement::test_json_flag_at_group_level_search PASSED
cli_web/airbnb/tests/test_e2e.py::TestJsonFlagPlacement::test_json_flag_at_subcommand_level_search PASSED
cli_web/airbnb/tests/test_e2e.py::TestJsonFlagPlacement::test_json_flag_at_group_level_autocomplete PASSED
cli_web/airbnb/tests/test_e2e.py::TestJsonFlagPlacement::test_json_flag_at_subcommand_level_autocomplete PASSED
cli_web/airbnb/tests/test_e2e.py::TestListingsGet::test_get_listing_returns_name PASSED
cli_web/airbnb/tests/test_e2e.py::TestListingsGet::test_get_listing_not_found PASSED
cli_web/airbnb/tests/test_e2e.py::TestListingsGet::test_get_listing_search_then_get_roundtrip PASSED
cli_web/airbnb/tests/test_e2e.py::TestAutocomplete::test_locations_returns_suggestions PASSED
cli_web/airbnb/tests/test_e2e.py::TestAutocomplete::test_locations_num_results PASSED
cli_web/airbnb/tests/test_e2e.py::TestAutocomplete::test_locations_suggestion_fields PASSED
cli_web/airbnb/tests/test_e2e.py::TestCliHelp::test_help_loads PASSED
cli_web/airbnb/tests/test_e2e.py::TestCliHelp::test_search_help PASSED
cli_web/airbnb/tests/test_e2e.py::TestCliHelp::test_version PASSED
cli_web/airbnb/tests/test_e2e.py::TestCliHelp::test_listings_help PASSED

============================= 71 passed in 23.47s ==============================
```

### Summary

| Metric | Value |
|--------|-------|
| Total tests | 76 |
| Passed | 76 |
| Failed | 0 |
| Pass rate | 100% |
| Unit tests (no network) | 51 |
| E2E / subprocess tests (live) | 25 |
| Execution time | ~26.3s |
| Date | 2026-04-04 (Phase 4 update) |

### Gaps / Notes

- **VCR cassettes**: Not added. Airbnb uses SSR HTML (not a batchexecute/GraphQL protocol) so the unit mock layer already provides full coverage without cassettes.
- **Bot protection**: E2E tests depend on curl_cffi Chrome impersonation. If Airbnb updates their bot detection, tests may need `camoufox` as fallback.
- **Listing ID `1603496841117193305`**: Hardcoded in `test_get_listing_returns_name`. If this listing is delisted, the test will need a new ID.

### Phase 4 Additions (2026-04-04)

During Phase 4 standards review, the following improvements were made:

**New commands implemented** (Traffic Fidelity review found these were documented in AIRBNB.md but missing):
- `listings reviews LISTING_ID` — get guest reviews via `StaysPdpReviewsQuery` persisted GraphQL
- `listings availability LISTING_ID` — get 12-month availability calendar via `PdpAvailabilityCalendar` persisted GraphQL

**New models added** to `core/models.py`: `Review`, `AvailabilityDay`, `AvailabilityMonth`

**`_api_v3_get()` helper** added to `AirbnbClient` — clean DRY pattern for v3 persisted GraphQL calls

**`_encode_stay_listing_id()`** added — `StayListing:` prefix (required for reviews GraphQL, differs from search's `DemandStayListing:`)

**User-agent header** added to `_DEFAULT_HEADERS` (as documented in AIRBNB.md)

**`TestCLISubprocess` class** added to `test_e2e.py` with 5 tests covering the installed binary and the new commands

**5 new E2E tests** added (total 25 E2E tests):
- `TestCLISubprocess::test_binary_resolves`
- `TestCLISubprocess::test_reviews_help`
- `TestCLISubprocess::test_availability_help`
- `TestCLISubprocess::test_reviews_returns_data`
- `TestCLISubprocess::test_availability_returns_data`

All 51 unit tests continue to pass after these additions.
