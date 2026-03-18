# TEST.md — FUTBIN CLI Test Plan & Results

## Part 1: Test Plan

### Test Inventory
- `test_core.py`: ~15 unit tests planned
- `test_e2e.py`: ~8 E2E tests planned (live), ~3 subprocess tests planned

### Unit Test Plan (test_core.py)

#### client.py
- `test_parse_price_millions` — "2.73M" → 2730000
- `test_parse_price_thousands` — "690K" → 690000
- `test_parse_price_plain` — "3,600" → 3600
- `test_parse_price_zero` — "0" → None
- `test_parse_price_dash` — "---" → None
- `test_search_players_json` — Mock /players/search response, verify parsed PlayerSearchResult
- `test_list_players_html` — Mock /players HTML response, verify parsed Player list
- `test_get_price_history` — Mock /26/player/{id}/{slug}/prices, verify PriceHistory with data-ps-data parsing

#### auth.py
- `test_save_and_load_cookies` — Round-trip save/load
- `test_load_cookies_missing` — Returns None when no file
- `test_get_auth_status_no_cookies` — Shows not authenticated
- `test_get_auth_status_with_cookies` — Shows authenticated
- `test_clear_cookies` — Removes file

#### models.py
- `test_player_to_dict` — Verify dict output excludes None/empty
- `test_price_history_to_dict` — Verify nested serialization

### E2E Test Plan (test_e2e.py)

#### Live Tests (require network)
- `test_search_live` — Search "Messi", verify results have id/name/position
- `test_list_players_live` — List page 1 ST, verify non-empty with correct fields
- `test_get_player_live` — Get player by known ID, verify fields
- `test_price_history_live` — Get prices for known player, verify price points
- `test_market_index_live` — Get market index, verify indices returned
- `test_sbc_list_live` — List SBCs, verify response
- `test_popular_players_live` — Get popular players
- `test_latest_players_live` — Get latest players

#### Subprocess Tests
- `test_cli_help` — `cli-web-futbin --help` exits 0
- `test_cli_search_json` — `cli-web-futbin --json players search --query Messi` returns valid JSON
- `test_cli_market_json` — `cli-web-futbin --json market index` returns valid JSON

### Realistic Workflow Scenarios

1. **Player Discovery**: Search "Mbappe" → pick first result → get full details → get price history → verify price data contains recent points
2. **Market Check**: Get market index → verify all rating tiers present → verify values are numeric
3. **SBC Browse**: List SBCs → verify response structure

---

## Part 2: Test Results

**Date:** 2026-03-16
**Total tests:** 24
**Pass rate:** 100% (24/24)

```
cli_web/futbin/tests/test_core.py::test_parse_price_millions PASSED
cli_web/futbin/tests/test_core.py::test_parse_price_thousands PASSED
cli_web/futbin/tests/test_core.py::test_parse_price_plain PASSED
cli_web/futbin/tests/test_core.py::test_parse_price_zero PASSED
cli_web/futbin/tests/test_core.py::test_parse_price_dash PASSED
cli_web/futbin/tests/test_core.py::test_parse_price_empty PASSED
cli_web/futbin/tests/test_core.py::TestAuth::test_save_and_load_cookies PASSED
cli_web/futbin/tests/test_core.py::TestAuth::test_load_cookies_missing PASSED
cli_web/futbin/tests/test_core.py::TestAuth::test_get_auth_status_no_cookies PASSED
cli_web/futbin/tests/test_core.py::TestAuth::test_get_auth_status_with_cookies PASSED
cli_web/futbin/tests/test_core.py::TestAuth::test_clear_cookies PASSED
cli_web/futbin/tests/test_core.py::test_player_to_dict PASSED
cli_web/futbin/tests/test_core.py::test_price_history_to_dict PASSED
cli_web/futbin/tests/test_core.py::test_search_players_mocked PASSED
cli_web/futbin/tests/test_e2e.py::TestLiveAPI::test_search_live PASSED
cli_web/futbin/tests/test_e2e.py::TestLiveAPI::test_list_players_live PASSED
cli_web/futbin/tests/test_e2e.py::TestLiveAPI::test_get_price_history_live PASSED
cli_web/futbin/tests/test_e2e.py::TestLiveAPI::test_market_index_live PASSED
cli_web/futbin/tests/test_e2e.py::TestLiveAPI::test_popular_players_live PASSED
cli_web/futbin/tests/test_e2e.py::TestLiveAPI::test_latest_players_live PASSED
cli_web/futbin/tests/test_e2e.py::TestPlayerDiscoveryWorkflow::test_search_then_prices PASSED
cli_web/futbin/tests/test_e2e.py::TestCLISubprocess::test_cli_help PASSED
cli_web/futbin/tests/test_e2e.py::TestCLISubprocess::test_cli_search_json PASSED
cli_web/futbin/tests/test_e2e.py::TestCLISubprocess::test_cli_market_json PASSED

============================= 24 passed in 12.46s =============================
```

### Summary
- **Unit tests (14):** All pass — price parsing, auth CRUD, model serialization, mocked search
- **E2E live tests (7):** All pass — search, list, prices, market, popular, latest, discovery workflow
- **Subprocess tests (3):** All pass — --help, --json search, --json market
