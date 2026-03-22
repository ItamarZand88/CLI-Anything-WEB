# TEST.md — cli-web-booking Test Plan & Results

## Part 1: Test Plan

### Test Inventory

| File | Tests | Layer | Network |
|------|-------|-------|---------|
| `test_core.py` | 37 | Unit (mocked HTTP) | No |
| `test_e2e.py` | 15 | E2E live + Subprocess | Yes |
| **Total** | **52** | | |

### Unit Tests (`test_core.py`)

**Exceptions (6 tests)**
- Exception hierarchy (BookingError base class)
- AuthError recoverable/non-recoverable flag
- RateLimitError retry_after attribute
- ServerError status_code attribute
- WAFChallengeError message and recoverability

**Models — Destination (3 tests)**
- GraphQL city response parsing (dest_id, dest_type extraction)
- Airport response parsing
- to_dict serialization

**Models — Property (7 tests)**
- Score text parsing: "Scored 8.6 Excellent 677 reviews"
- Score text with different labels (Wonderful, Good)
- Score text with missing reviews
- Price text parsing: ILS, USD, empty
- to_dict with all fields

**Models — PropertyDetail (2 tests)**
- JSON-LD parsing (name, score, address, country, type)
- to_dict serialization

**Auth (5 tests)**
- Load cookies from environment variable
- Load cookies raises AuthError when missing
- Extract cookies from playwright list format
- Domain priority (booking.com over regional)
- Save and load round-trip

**Client (6 tests)**
- Autocomplete success with mocked GraphQL
- GraphQL server error → ServerError
- Network error → NetworkError
- WAF challenge detection → WAFChallengeError
- 404 response → NotFoundError
- 429 response → RateLimitError with retry_after

**Helpers (6 tests)**
- json_error format
- json_error with extra fields
- handle_errors: AuthError → exit 1
- handle_errors: ServerError → exit 2
- handle_errors: JSON mode outputs structured error
- handle_errors: KeyboardInterrupt → exit 130

**HTML Parsing (2 tests)**
- Parse single property card with real data-testid attributes
- Parse multiple property cards from results page

### E2E Live Tests (`test_e2e.py`)

**AutoComplete — no auth (4 tests)**
- Paris: returns city results with dest_id
- Tokyo: returns results
- Nonexistent query: returns list (empty or fallback)
- Limit parameter respected

**Search — requires WAF cookies (4 tests)**
- Paris search: returns properties with titles and slugs
- Score verification: at least some results have scores > 0
- Price verification: at least some results have price amounts
- Sort by price: returns results

**Property Detail — requires WAF cookies (1 test)**
- Le Senat hotel: name, score, review count, country verified

**Round-Trip (1 test)**
- Search → get first result → verify detail has a name

**Subprocess (5 tests)**
- `--help`: returns 0, shows command list
- `--version`: returns 0, shows "0.1.0"
- `autocomplete Paris --json`: structured output with results
- `auth status --json`: shows authenticated status
- `search find Paris --json`: returns properties

---

## Part 2: Test Results

**Date:** 2026-03-21
**Platform:** Windows 11 Pro, Python 3.12.8
**Duration:** 23.53s

### Full Results

```
52 passed in 23.53s

test_core.py::TestExceptions::test_booking_error_is_base PASSED
test_core.py::TestExceptions::test_auth_error_recoverable PASSED
test_core.py::TestExceptions::test_auth_error_not_recoverable PASSED
test_core.py::TestExceptions::test_rate_limit_error_retry_after PASSED
test_core.py::TestExceptions::test_server_error_status_code PASSED
test_core.py::TestExceptions::test_waf_challenge_error PASSED
test_core.py::TestDestination::test_from_graphql_city PASSED
test_core.py::TestDestination::test_from_graphql_airport PASSED
test_core.py::TestDestination::test_to_dict PASSED
test_core.py::TestProperty::test_parse_score_text_full PASSED
test_core.py::TestProperty::test_parse_score_text_wonderful PASSED
test_core.py::TestProperty::test_parse_score_text_no_reviews PASSED
test_core.py::TestProperty::test_parse_price_text_shekel PASSED
test_core.py::TestProperty::test_parse_price_text_usd PASSED
test_core.py::TestProperty::test_parse_price_text_empty PASSED
test_core.py::TestProperty::test_to_dict PASSED
test_core.py::TestPropertyDetail::test_from_json_ld PASSED
test_core.py::TestPropertyDetail::test_to_dict PASSED
test_core.py::TestAuth::test_load_cookies_from_env PASSED
test_core.py::TestAuth::test_load_cookies_missing_raises PASSED
test_core.py::TestAuth::test_extract_cookies_list_format PASSED
test_core.py::TestAuth::test_extract_cookies_domain_priority PASSED
test_core.py::TestAuth::test_save_and_load PASSED
test_core.py::TestClient::test_autocomplete_success PASSED
test_core.py::TestClient::test_graphql_server_error PASSED
test_core.py::TestClient::test_graphql_network_error PASSED
test_core.py::TestClient::test_search_waf_challenge PASSED
test_core.py::TestClient::test_fetch_html_404 PASSED
test_core.py::TestClient::test_fetch_html_429 PASSED
test_core.py::TestHelpers::test_json_error_format PASSED
test_core.py::TestHelpers::test_json_error_with_extra PASSED
test_core.py::TestHelpers::test_handle_errors_auth_exits_1 PASSED
test_core.py::TestHelpers::test_handle_errors_server_exits_2 PASSED
test_core.py::TestHelpers::test_handle_errors_json_mode PASSED
test_core.py::TestHelpers::test_handle_errors_keyboard_interrupt PASSED
test_core.py::TestSearchParsing::test_parse_property_card PASSED
test_core.py::TestSearchParsing::test_parse_search_results_multiple PASSED
test_e2e.py::TestAutoCompleteLive::test_autocomplete_paris PASSED
test_e2e.py::TestAutoCompleteLive::test_autocomplete_tokyo PASSED
test_e2e.py::TestAutoCompleteLive::test_autocomplete_empty PASSED
test_e2e.py::TestAutoCompleteLive::test_autocomplete_limit PASSED
test_e2e.py::TestSearchLive::test_search_paris PASSED
test_e2e.py::TestSearchLive::test_search_has_scores PASSED
test_e2e.py::TestSearchLive::test_search_has_prices PASSED
test_e2e.py::TestSearchLive::test_search_sort_by_price PASSED
test_e2e.py::TestPropertyDetailLive::test_get_property_le_senat PASSED
test_e2e.py::TestRoundTrip::test_search_then_detail PASSED
test_e2e.py::TestCLISubprocess::test_help PASSED
test_e2e.py::TestCLISubprocess::test_version PASSED
test_e2e.py::TestCLISubprocess::test_autocomplete_json PASSED
test_e2e.py::TestCLISubprocess::test_auth_status_json PASSED
test_e2e.py::TestCLISubprocess::test_search_json PASSED
```

### Summary

| Metric | Value |
|--------|-------|
| Total tests | 52 |
| Passed | 52 |
| Failed | 0 |
| Pass rate | 100% |
| Duration | 23.53s |

### Key Finding

Booking.com hotel detail pages redirect to search results when date/occupancy
parameters are included in the URL. The fix: fetch detail pages without
date parameters. Property info (name, rating, description) is available
regardless of dates via JSON-LD structured data.
