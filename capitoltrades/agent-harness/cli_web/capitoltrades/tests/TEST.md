# TEST.md — cli-web-capitoltrades Test Plan & Results


## Part 1: Test Plan


### Test Inventory

| File | Tests | Layer |
|------|-------|-------|
| test_core.py | 29 | Unit (mocked) |
| test_e2e.py | 31 | E2E (live) + Subprocess |

**Total: 60 tests**


### test_core.py

**TestExceptions** (10 tests) — Unit (mocked)

- `test_auth_error_on_401` — auth error on 401
- `test_auth_error_on_403` — auth error on 403
- `test_not_found_on_404` — not found on 404
- `test_rate_limit_with_retry_after` — rate limit with retry after
- `test_rate_limit_without_retry_after` — rate limit without retry after
- `test_server_error_on_5xx` — server error on 5xx
- `test_no_raise_on_2xx` — no raise on 2xx
- `test_error_to_dict_has_code` — error to dict has code
- `test_auth_error_to_dict_code` — auth error to dict code
- `test_rate_limit_to_dict_includes_retry_after` — rate limit to dict includes retry after

**TestTradesListParser** (3 tests) — Unit (mocked)

- `test_parses_one_row` — parses one row
- `test_empty_table_returns_empty_list` — empty table returns empty list
- `test_reduced_column_table_on_detail_page` — reduced column table on detail page

**TestTradeDetailParser** (1 tests) — Unit (mocked)

- `test_parses_all_fields` — parses all fields

**TestListParsers** (8 tests) — Unit (mocked)

- `test_politicians_list_extracts_cards` — politicians list extracts cards
- `test_politicians_list_deduplicates` — politicians list deduplicates
- `test_issuers_list_extracts_cards` — issuers list extracts cards
- `test_buzz_list_parses_tailwind_muted_date` — buzz list parses tailwind muted date
- `test_press_list_parses_dated_entries` — press list parses dated entries
- `test_buzz_detail_has_body` — buzz detail has body
- `test_press_detail_has_body` — press detail has body
- `test_articles_list_extracts_slugs` — articles list extracts slugs

**TestStatsParser** (1 tests) — Unit (mocked)

- `test_extracts_overview_numbers` — extracts overview numbers

**TestHelpers** (4 tests) — Unit (mocked)

- `test_handle_errors_auth_exits_1` — handle errors auth exits 1
- `test_handle_errors_not_found_exits_1` — handle errors not found exits 1
- `test_handle_errors_unknown_exits_2` — handle errors unknown exits 2
- `test_handle_errors_json_mode_outputs_json` — handle errors json mode outputs json

**TestClientMocked** (2 tests) — Unit (mocked)

- `test_get_html_wraps_network_error` — get html wraps network error
- `test_get_bff_json_parses_response` — get bff json parses response

### test_e2e.py

**TestLiveAPI** (14 tests) — E2E (live)

- `test_trades_list_returns_rows` — trades list returns rows
- `test_trades_stats_returns_known_labels` — trades stats returns known labels
- `test_trade_detail_round_trip` — trade detail round trip
- `test_politicians_list_has_cards` — politicians list has cards
- `test_politician_detail_has_name` — politician detail has name
- `test_issuers_list_has_cards` — issuers list has cards
- `test_issuer_search_via_bff` — issuer search via bff
- `test_issuer_search_empty_query_returns_empty` — issuer search empty query returns empty
- `test_articles_list` — articles list
- `test_article_detail_has_body` — article detail has body
- `test_buzz_list_returns_rows` — buzz list returns rows
- `test_buzz_detail` — buzz detail
- `test_press_list_returns_rows` — press list returns rows
- `test_trades_list_size_filter_applied` — trades list size filter applied

**TestCLISubprocess** (17 tests) — Subprocess

- `test_help_loads` — help loads
- `test_version_works` — version works
- `test_trades_stats_json` — trades stats json
- `test_trades_list_json` — trades list json
- `test_trade_get_json_has_detail_fields` — trade get json has detail fields
- `test_politicians_list_json` — politicians list json
- `test_issuers_search_json` — issuers search json
- `test_articles_list_json` — articles list json
- `test_filter_party_republican` — filter party republican
- `test_trade_list_not_found_for_bad_id` — trade list not found for bad id
- `test_no_protocol_leakage_in_output` — no protocol leakage in output
- `test_buzz_list_json` — buzz list json
- `test_press_list_json` — press list json
- `test_trades_by_ticker` — trades by ticker
- `test_trades_by_ticker_not_found` — trades by ticker not found
- `test_politicians_top_by_trades` — politicians top by trades
- `test_trades_list_new_filters_accepted` — trades list new filters accepted

---


## Part 2: Test Results


**Date:** 2026-04-24 08:31 UTC


### Summary

| Metric | Value |
|--------|-------|
| Total tests | 0 |
| Passed | 0 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |
| Pass rate | N/A |
| Execution time | 19.27s |
| Date | 2026-04-24 08:31 UTC |

### Raw Output

```
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\סמדרזנד\capitoltrades\agent-harness
plugins: anyio-4.13.0
collected 60 items

cli_web\capitoltrades\tests\test_core.py .............................   [ 48%]
cli_web\capitoltrades\tests\test_e2e.py ...............................  [100%]

============================= 60 passed in 19.27s =============================
```
