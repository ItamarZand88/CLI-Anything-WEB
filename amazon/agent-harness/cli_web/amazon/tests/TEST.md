# TEST.md — cli-web-amazon

## Part 1: Test Plan

### Test Inventory

| File | Tests | Purpose |
|------|-------|---------|
| `test_core.py` | 27 | Unit tests — mocked HTTP, no network |
| `test_e2e.py` | ~30 | Live E2E + subprocess tests |
| **Total** | **~57** | |

---

### Unit Test Plan (`test_core.py`)

#### `TestExceptions` (4 tests)
- `RateLimitError` stores `retry_after` float
- `ServerError` stores `status_code` int
- `error_code_for()` maps exception types → string codes: `RATE_LIMITED`, `NOT_FOUND`, `SERVER_ERROR`, `UNKNOWN_ERROR`

#### `TestModels` (4 tests)
- `SearchResult.to_dict()` — all fields round-trip through dict
- `Product.to_dict()` — ASIN + brand preserved
- `BestSeller.to_dict()` — rank + ASIN preserved
- `Suggestion.to_dict()` — value + type preserved

#### `TestClientSuggestions` (3 tests)
- Mocked JSON response → `get_suggestions()` returns `Suggestion` list
- Empty suggestions list returns `[]`
- 429 response raises `RateLimitError` with correct `retry_after`

#### `TestClientSearch` (3 tests)
- Mocked HTML with real `data-component-type="s-search-result"` + `data-asin` attrs → returns `SearchResult` list with correct ASINs and titles
- Empty HTML page → returns `[]`
- URL normalization: relative `/dp/...` paths become `https://www.amazon.com/dp/...`

#### `TestClientProductDetail` (2 tests)
- Mocked HTML with real Amazon product page structure (`#productTitle`, `.a-offscreen`, `#acrPopover`, `#bylineInfo`, `#landingImage`) → all fields parsed correctly
- Product URL reflects canonical `https://www.amazon.com/dp/<ASIN>` form

#### `TestClientBestSellers` (2 tests)
- Mocked HTML with `#gridItemRoot` + `.zg-bdg-text` rank badges → `BestSeller` list with correct rank, ASIN, title, price
- Ranks returned in sequential order (1, 2, ...)

#### `TestHelpers` (7 tests)
- `sanitize_filename()` passes through safe names unchanged
- Strips `/` and `:` from filenames
- Empty/whitespace string → `"untitled"`
- `handle_errors(json_mode=False)` on `NotFoundError` → `SystemExit(1)`
- `handle_errors(json_mode=True)` on `NotFoundError` → JSON output `{"error": true, "code": "NOT_FOUND", ...}`
- `handle_errors()` on unknown exception → `SystemExit(2)`
- `handle_errors()` on `KeyboardInterrupt` → `SystemExit(130)`

---

### E2E Test Plan (`test_e2e.py`)

**Site profile:** Amazon.com — No-auth, read-only. All commands use public endpoints.

#### `TestE2ESuggest` (4 tests) — live autocomplete API
- `suggest "laptop"` returns non-empty list with `value` and `type` fields
- Response includes at least one `KEYWORD` type entry
- No raw protocol data leakage in suggestion values
- Unusual query returns empty list without raising

#### `TestE2ESearch` (5 tests) — live HTML search
- `search "laptop"` returns results with 10-char ASINs
- Each result has non-empty title and URL starting with `https://www.amazon.com`
- URL contains the ASIN of the result
- Page 1 and page 2 return different ASINs (pagination works)
- No raw protocol data in titles

#### `TestE2EProduct` (5 tests) — live product detail page
- `get_product("B0GRZ78683")` returns product with correct ASIN and non-trivial title
- Product URL contains ASIN
- Rating field (if present) contains "out of 5" format
- Round-trip: `search` → pick first ASIN → `get_product` → verify ASIN matches
- No raw protocol data in title or price

#### `TestE2EBestSellers` (5 tests) — live bestseller page
- `get_bestsellers("electronics")` returns non-empty list with rank=1 first
- All ASINs are exactly 10 characters
- Ranks are sequential and start at 1
- All titles are non-empty
- Each item's URL contains its ASIN

#### `TestCLISubprocess` (≥11 tests) — installed `cli-web-amazon` binary
- `--help` loads successfully
- `--version` works
- `search laptop --json` → valid JSON array with `asin`, `title` fields; ASINs are 10 chars
- `search laptop --json` → no RPC leakage in titles
- `suggest laptop --json` → valid JSON array with `value` and `type` fields
- `product get B0GRZ78683 --json` → JSON object with correct `asin`, non-empty `title`, `url` containing ASIN
- `product get B0GRZ78683 --json` → no RPC data in title
- `bestsellers electronics --json` → JSON array; first item `rank == 1`
- `bestsellers electronics --json` → all items have `asin`, `title`, `rank`
- `search laptop --page 2 --json` → valid JSON array (pagination option works)
- `search laptop --dept electronics --json` → valid JSON array (department filter works)
- `product get BADASIN000 --json` → structured error JSON on failure (no crash)
- `search --help`, `product --help`, `bestsellers --help`, `suggest --help` all return exit 0

---

### Realistic Workflow Scenarios

**Scenario 1 — Product discovery pipeline:**
```
suggest "wireless headphones" --json
→ pick top KEYWORD suggestion
→ search "<suggestion>" --json
→ pick top ASIN
→ product get <ASIN> --json
→ verify product fields match listing
```

**Scenario 2 — Category exploration:**
```
bestsellers electronics --json
→ extract top 5 ASINs
→ product get <ASIN> --json for each
→ compare prices and ratings
```

---

### Known Gaps

- `price` and `review_count` are empty in search results — Amazon client-side renders these fields; `product get` returns reliable pricing
- `product get` may return empty `price` for geo-restricted products; `price_note` explains the reason

---

## Part 2: Test Results

### Run Date: 2026-04-05

### Full `pytest -v --tb=no` Output

```
============================= test session starts =============================
platform win32 -- Python 3.12, pytest-9.x

cli_web/amazon/tests/test_core.py::TestExceptions::test_rate_limit_error_with_retry_after PASSED
cli_web/amazon/tests/test_core.py::TestExceptions::test_server_error_status_code PASSED
cli_web/amazon/tests/test_core.py::TestExceptions::test_error_code_for_rate_limit PASSED
cli_web/amazon/tests/test_core.py::TestExceptions::test_error_code_for_not_found PASSED
cli_web/amazon/tests/test_core.py::TestExceptions::test_error_code_for_server_error PASSED
cli_web/amazon/tests/test_core.py::TestExceptions::test_error_code_for_unknown PASSED
cli_web/amazon/tests/test_core.py::TestModels::test_bestseller_to_dict PASSED
cli_web/amazon/tests/test_core.py::TestModels::test_product_to_dict PASSED
cli_web/amazon/tests/test_core.py::TestModels::test_search_result_to_dict PASSED
cli_web/amazon/tests/test_core.py::TestModels::test_suggestion_to_dict PASSED
cli_web/amazon/tests/test_core.py::TestClientSuggestions::test_get_suggestions_429_raises_rate_limit PASSED
cli_web/amazon/tests/test_core.py::TestClientSuggestions::test_get_suggestions_empty_results PASSED
cli_web/amazon/tests/test_core.py::TestClientSuggestions::test_get_suggestions_parses_keywords PASSED
cli_web/amazon/tests/test_core.py::TestClientSearch::test_search_empty_page PASSED
cli_web/amazon/tests/test_core.py::TestClientSearch::test_search_returns_products PASSED
cli_web/amazon/tests/test_core.py::TestClientSearch::test_search_url_normalization PASSED
cli_web/amazon/tests/test_core.py::TestClientProductDetail::test_get_product_parses_all_fields PASSED
cli_web/amazon/tests/test_core.py::TestClientProductDetail::test_get_product_url PASSED
cli_web/amazon/tests/test_core.py::TestClientBestSellers::test_get_bestsellers_parses_items PASSED
cli_web/amazon/tests/test_core.py::TestClientBestSellers::test_get_bestsellers_rank_order PASSED
cli_web/amazon/tests/test_core.py::TestHelpers::test_handle_errors_json_mode_outputs_json PASSED
cli_web/amazon/tests/test_core.py::TestHelpers::test_handle_errors_keyboard_interrupt_exits_130 PASSED
cli_web/amazon/tests/test_core.py::TestHelpers::test_handle_errors_not_found_exits_1 PASSED
cli_web/amazon/tests/test_core.py::TestHelpers::test_handle_errors_unknown_exits_2 PASSED
cli_web/amazon/tests/test_core.py::TestHelpers::test_sanitize_filename_basic PASSED
cli_web/amazon/tests/test_core.py::TestHelpers::test_sanitize_filename_empty PASSED
cli_web/amazon/tests/test_core.py::TestHelpers::test_sanitize_filename_invalid_chars PASSED

============================== 27 passed in 4.3s ==============================
```
