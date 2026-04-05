# TEST.md — cli-web-tripadvisor

## Part 1: Test Plan

### Test Inventory

| File | Tests | Purpose |
|------|-------|---------|
| `test_core.py` | 44 | Unit tests — mocked HTTP, no network |
| `test_e2e.py` | ~18 | Live E2E + subprocess tests |
| **Total** | **~62** | |

---

### Unit Test Plan (`test_core.py`)

#### `TestExceptions` (8 tests)
- `TripAdvisorError` stores message, `to_dict()` returns `{"error": true, "code": "ERROR"}`
- `AuthError` stores `recoverable`, `to_dict()["code"] == "AUTH_EXPIRED"`
- `RateLimitError` stores `retry_after` float, `to_dict()["retry_after"]` present
- `ServerError` stores `status_code` int, `to_dict()["status_code"]` preserved
- `NotFoundError` → `to_dict()["code"] == "NOT_FOUND"`
- `ParseError` → `to_dict()["code"] == "PARSE_ERROR"`
- `NetworkError` → `to_dict()["code"] == "NETWORK_ERROR"`
- All exception classes inherit from `TripAdvisorError` and `Exception`

#### `TestSlugHelpers` (7 tests)
- `_make_slug("Paris")` → `"Paris"` (simple passthrough)
- `_make_slug("Paris, Ile-de-France")` → `"Paris_Ile_de_France"` (comma+space → underscore)
- `_make_slug("New York City")` → `"New_York_City"` (spaces → underscores)
- `_slug_from_url("/Hotels-g187147-Paris_Ile_de_France-Hotels.html")` → `"Paris_Ile_de_France"`
- `_slug_from_url("/Restaurants-g60763-New_York_City_New_York.html")` → `"New_York_City_New_York"`
- `_slug_from_url("/Tourism-g60763-New_York_City_New_York-Vacations.html")` → `"New_York_City_New_York"`
- `_slug_from_url("/SomeOtherPage.html")` → `None`

#### `TestExtractId` (4 tests)
- Hotel URL → extracts `"d229968"` → `"229968"`
- Restaurant URL → extracts `"d1035679"` → `"1035679"`
- Attraction URL → extracts `"d188151"` → `"188151"`
- Non-review URL → returns `""`

#### `TestJsonLDExtraction` (7 tests)
- Mocked HTML with single `<script type="application/ld+json">` → one parsed block
- `_find_jsonld_by_type(blocks, "Hotel")` → returns matching block
- `_find_jsonld_by_type(blocks, "Restaurant")` on Hotel HTML → returns `None`
- `ItemList` block with `itemListElement` → `_find_jsonld_items(blocks, "Hotel")` returns 2 items
- Empty HTML → returns `[]`
- Invalid JSON in script tag → returns `[]` (no exception)
- Two script tags → returns two blocks

#### `TestBuildHotel` (3 tests)
- Full JSON-LD dict → `_build_hotel()` extracts all fields: id, name, rating, review_count, price_range, address, city, country, telephone, lat/lon
- Minimal dict (no aggregateRating) → missing fields fall back to `None`
- `to_dict()` keys match expected set exactly: `{id, name, url, rating, review_count, price_range, address, city, country, telephone, latitude, longitude, image, amenities}`

#### `TestBuildRestaurant` (3 tests)
- Full JSON-LD → all fields extracted including cuisines list
- `servesCuisine` as single string → wrapped in list `["Italian"]`
- `to_dict()` keys match expected set: `{id, name, url, rating, review_count, price_range, cuisines, address, city, telephone, latitude, longitude, image, opening_hours}`

#### `TestBuildAttraction` (2 tests)
- Full JSON-LD → all fields extracted including opening_hours
- `to_dict()` keys match expected set: `{id, name, url, rating, review_count, address, city, telephone, latitude, longitude, image, opening_hours, description}`

#### `TestModels` (2 tests)
- `Location.to_dict()` → all fields round-trip: geo_id, name, url, type, coords, parent_name, geo_name
- `Hotel.to_dict()` → amenities list preserved, rating preserved

#### `TestHelpers` (8 tests)
- `truncate("hello", 60)` → unchanged (under limit)
- `truncate("a" * 70, 60)` → ends with `…`, length 61
- `truncate(None)` → `""`
- `format_rating("4.5", 1234)` → `"4.5 (1,234)"`
- `format_rating("4.5", None)` → `"4.5"`
- `format_rating(None, 100)` → `"—"`
- `resolve_json_mode(True)` → `True`
- `resolve_json_mode(False)` → `False`

---

### E2E Test Plan (`test_e2e.py`)

**Site profile:** TripAdvisor.com — No-auth, read-only. All commands use public endpoints via curl_cffi with DataDome bypass (Safari iOS 17.2 impersonation).

#### `TestCLISubprocess` (9 tests) — no network required
- `--help` loads, "tripadvisor" in output
- `--version` returns `0.1.0`
- `locations --help` shows "search"
- `hotels --help` shows "search" and "get"
- `restaurants --help` shows "search" and "get"
- `attractions --help` shows "search" and "get"
- `hotels search --help` shows `--geo-id`, `--page`, `--json`
- `restaurants search --help` shows `--geo-id`, `--page`, `--json`
- `attractions search --help` shows `--geo-id`, `--page`, `--json`

#### `TestLocationsSearchLive` (3 tests) — live API
- `locations search "Paris" --json` → success, Paris geo_id 187147 in results
- `locations search "New York" --json` → NYC (60763) or New York state (28953) in geo_ids
- `locations search "London" --json` → first result has `geo_id`, `name`, `url`, `type` fields

#### `TestHotelsLive` (3 tests) — live API (Paris geo_id 187147)
- `hotels search Paris --geo-id 187147 --json` → success, non-empty hotels list
- Hotel fields: `id`, `name` (non-empty), `url` (non-empty), `rating`, `review_count`, `price_range`, `city`
- Hotel URLs contain `tripadvisor.com` and `Hotel_Review`

#### `TestRestaurantsLive` (2 tests) — live API (Paris geo_id 187147)
- `restaurants search Paris --geo-id 187147 --json` → success, non-empty list
- Restaurant fields: `id`, `name` (non-empty), `url`, `rating`, `cuisines`, `price_range`

#### `TestAttractionsLive` (3 tests) — live API (Paris geo_id 187147)
- `attractions search Paris --geo-id 187147 --json` → success, non-empty list
- Attraction fields: `id`, `name` (non-empty), `url`, `rating`
- Eiffel Tower appears in results (by name substring "eiffel")

---

### Realistic Workflow Scenarios

**Scenario 1 — Hotel discovery pipeline:**
```
locations search "Paris" --json
→ get geo_id (e.g. 187147)
→ hotels search "Paris" --geo-id 187147 --json
→ pick first hotel URL
→ hotels get "<URL>" --json
→ verify hotel fields (name, rating, address)
```

**Scenario 2 — Restaurant exploration:**
```
locations search "New York City" --json
→ get geo_id (60763)
→ restaurants search "New York City" --geo-id 60763 --json
→ extract top 3 by rating
→ restaurants get "<URL>" --json for each
```

**Scenario 3 — Attractions check:**
```
locations search "London" --json
→ get geo_id
→ attractions search "London" --geo-id <id> --json
→ verify landmarks present (e.g. "Tower of London", "Big Ben")
```

---

### Known Gaps

- `hotels get`, `restaurants get`, `attractions get` detail commands require a valid TripAdvisor URL — E2E tests rely on search first
- `price_range` may be `null` for some hotels (TripAdvisor doesn't always expose it in JSON-LD)
- DataDome bot protection may occasionally block requests during CI; retry logic in client handles transient failures

---

## Part 2: Test Results

### Run Date: 2026-04-05

### Full `pytest -v --tb=no` Output (unit tests)

```
============================= test session starts =============================
platform win32 -- Python 3.12, pytest-9.x

cli_web/tripadvisor/tests/test_core.py::TestExceptions::test_base_exception PASSED
cli_web/tripadvisor/tests/test_core.py::TestExceptions::test_auth_error PASSED
cli_web/tripadvisor/tests/test_core.py::TestExceptions::test_rate_limit_error PASSED
cli_web/tripadvisor/tests/test_core.py::TestExceptions::test_server_error PASSED
cli_web/tripadvisor/tests/test_core.py::TestExceptions::test_not_found_error PASSED
cli_web/tripadvisor/tests/test_core.py::TestExceptions::test_parse_error PASSED
cli_web/tripadvisor/tests/test_core.py::TestExceptions::test_network_error PASSED
cli_web/tripadvisor/tests/test_core.py::TestExceptions::test_inheritance_chain PASSED
cli_web/tripadvisor/tests/test_core.py::TestSlugHelpers::test_make_slug_simple PASSED
cli_web/tripadvisor/tests/test_core.py::TestSlugHelpers::test_make_slug_with_comma_space PASSED
cli_web/tripadvisor/tests/test_core.py::TestSlugHelpers::test_make_slug_with_spaces PASSED
cli_web/tripadvisor/tests/test_core.py::TestSlugHelpers::test_slug_from_hotels_url PASSED
cli_web/tripadvisor/tests/test_core.py::TestSlugHelpers::test_slug_from_restaurants_url PASSED
cli_web/tripadvisor/tests/test_core.py::TestSlugHelpers::test_slug_from_tourism_url PASSED
cli_web/tripadvisor/tests/test_core.py::TestSlugHelpers::test_slug_from_none PASSED
cli_web/tripadvisor/tests/test_core.py::TestExtractId::test_extract_hotel_id PASSED
cli_web/tripadvisor/tests/test_core.py::TestExtractId::test_extract_restaurant_id PASSED
cli_web/tripadvisor/tests/test_core.py::TestExtractId::test_extract_attraction_id PASSED
cli_web/tripadvisor/tests/test_core.py::TestExtractId::test_extract_id_no_match PASSED
cli_web/tripadvisor/tests/test_core.py::TestJsonLDExtraction::test_extract_single_block PASSED
cli_web/tripadvisor/tests/test_core.py::TestJsonLDExtraction::test_find_by_type PASSED
cli_web/tripadvisor/tests/test_core.py::TestJsonLDExtraction::test_find_by_type_not_found PASSED
cli_web/tripadvisor/tests/test_core.py::TestJsonLDExtraction::test_find_items_from_itemlist PASSED
cli_web/tripadvisor/tests/test_core.py::TestJsonLDExtraction::test_extract_empty_html PASSED
cli_web/tripadvisor/tests/test_core.py::TestJsonLDExtraction::test_extract_invalid_json PASSED
cli_web/tripadvisor/tests/test_core.py::TestJsonLDExtraction::test_extract_multiple_blocks PASSED
cli_web/tripadvisor/tests/test_core.py::TestBuildHotel::test_basic_build PASSED
cli_web/tripadvisor/tests/test_core.py::TestBuildHotel::test_missing_fields_fallback PASSED
cli_web/tripadvisor/tests/test_core.py::TestBuildHotel::test_to_dict_completeness PASSED
cli_web/tripadvisor/tests/test_core.py::TestBuildRestaurant::test_basic_build PASSED
cli_web/tripadvisor/tests/test_core.py::TestBuildRestaurant::test_single_cuisine_string PASSED
cli_web/tripadvisor/tests/test_core.py::TestBuildRestaurant::test_to_dict_completeness PASSED
cli_web/tripadvisor/tests/test_core.py::TestBuildAttraction::test_basic_build PASSED
cli_web/tripadvisor/tests/test_core.py::TestBuildAttraction::test_to_dict_completeness PASSED
cli_web/tripadvisor/tests/test_core.py::TestModels::test_location_to_dict PASSED
cli_web/tripadvisor/tests/test_core.py::TestModels::test_hotel_to_dict_all_fields PASSED
cli_web/tripadvisor/tests/test_core.py::TestHelpers::test_truncate_short PASSED
cli_web/tripadvisor/tests/test_core.py::TestHelpers::test_truncate_long PASSED
cli_web/tripadvisor/tests/test_core.py::TestHelpers::test_truncate_none PASSED
cli_web/tripadvisor/tests/test_core.py::TestHelpers::test_format_rating_with_count PASSED
cli_web/tripadvisor/tests/test_core.py::TestHelpers::test_format_rating_without_count PASSED
cli_web/tripadvisor/tests/test_core.py::TestHelpers::test_format_rating_none PASSED
cli_web/tripadvisor/tests/test_core.py::TestHelpers::test_resolve_json_mode_flag PASSED
cli_web/tripadvisor/tests/test_core.py::TestHelpers::test_resolve_json_mode_false PASSED

============================== 44 passed in 2.1s ==============================
```
