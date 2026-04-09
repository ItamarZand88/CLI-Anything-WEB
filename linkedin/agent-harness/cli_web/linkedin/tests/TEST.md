# TEST.md — cli-web-linkedin Test Plan & Results


## Part 1: Test Plan


### Test Inventory

| File | Tests | Layer |
|------|-------|-------|
| test_core.py | 48 | Unit (mocked) |
| test_e2e.py | 21 | E2E (live) + Subprocess |

**Total: 69 tests**


### test_core.py

**TestExceptions** (12 tests) — Unit (mocked)

- `test_linkedin_error_base_to_dict` — linkedin error base to dict
- `test_auth_error_recoverable_flag` — auth error recoverable flag
- `test_auth_error_to_dict_code` — auth error to dict code
- `test_rate_limit_error_retry_after` — rate limit error retry after
- `test_rate_limit_error_to_dict_includes_retry_after` — rate limit error to dict includes retry after
- `test_rate_limit_error_to_dict_omits_retry_after_when_none` — rate limit error to dict omits retry after when none
- `test_server_error_status_code` — server error status code
- `test_server_error_default_status_code` — server error default status code
- `test_not_found_error_to_dict` — not found error to dict
- `test_network_error_to_dict` — network error to dict
- `test_rpc_error_to_dict` — rpc error to dict
- `test_all_exceptions_inherit_from_linkedin_error` — all exceptions inherit from linkedin error

**TestModels** (7 tests) — Unit (mocked)

- `test_post_to_dict_all_fields` — post to dict all fields
- `test_post_defaults` — post defaults
- `test_profile_to_dict_preserves_fields` — profile to dict preserves fields
- `test_company_to_dict_preserves_fields` — company to dict preserves fields
- `test_job_to_dict_preserves_fields` — job to dict preserves fields
- `test_search_result_to_dict_all_fields` — search result to dict all fields
- `test_comment_to_dict_all_fields` — comment to dict all fields

**TestHelpers** (12 tests) — Unit (mocked)

- `test_handle_errors_catches_auth_error_exit_1` — handle errors catches auth error exit 1
- `test_handle_errors_catches_not_found_error_exit_1` — handle errors catches not found error exit 1
- `test_handle_errors_catches_server_error_exit_2` — handle errors catches server error exit 2
- `test_handle_errors_catches_network_error_exit_1` — handle errors catches network error exit 1
- `test_handle_errors_catches_generic_exception_exit_2` — handle errors catches generic exception exit 2
- `test_handle_errors_keyboard_interrupt_exit_130` — handle errors keyboard interrupt exit 130
- `test_handle_errors_json_mode_outputs_json` — handle errors json mode outputs json
- `test_handle_errors_json_mode_generic_exception` — handle errors json mode generic exception
- `test_resolve_json_mode_true` — resolve json mode true
- `test_resolve_json_mode_false` — resolve json mode false
- `test_resolve_json_mode_from_context` — resolve json mode from context
- `test_resolve_json_mode_context_no_json` — resolve json mode context no json

**TestCSRFExtraction** (4 tests) — Unit (mocked)

- `test_extract_csrf_strips_quotes` — extract csrf strips quotes
- `test_extract_csrf_no_quotes` — extract csrf no quotes
- `test_extract_csrf_missing_jsessionid_raises_auth_error` — extract csrf missing jsessionid raises auth error
- `test_extract_csrf_empty_jsessionid_raises_auth_error` — extract csrf empty jsessionid raises auth error

**TestClientHTTPErrors** (9 tests) — Unit (mocked)

- `test_401_raises_auth_error` — 401 raises auth error
- `test_403_raises_auth_error` — 403 raises auth error
- `test_404_raises_not_found_error` — 404 raises not found error
- `test_429_raises_rate_limit_error` — 429 raises rate limit error
- `test_429_without_retry_after_header` — 429 without retry after header
- `test_500_raises_server_error` — 500 raises server error
- `test_502_raises_server_error` — 502 raises server error
- `test_200_does_not_raise` — 200 does not raise
- `test_400_raises_linkedin_error` — 400 raises linkedin error

**TestTruncate** (4 tests) — Unit (mocked)

- `test_short_string_unchanged` — short string unchanged
- `test_exact_length_unchanged` — exact length unchanged
- `test_long_string_truncated_with_ellipsis` — long string truncated with ellipsis
- `test_empty_string` — empty string

### test_e2e.py

**TestCLISubprocess** (13 tests) — Subprocess

- `test_help_loads` — help loads
- `test_version` — version
- `test_search_help` — search help
- `test_profile_help` — profile help
- `test_jobs_help` — jobs help
- `test_post_help` — post help
- `test_auth_help` — auth help
- `test_auth_status_json` — auth status json
- `test_feed_json` — feed json
- `test_profile_me_json` — profile me json
- `test_company_json` — company json
- `test_jobs_search_json` — jobs search json
- `test_feed_text_mode` — feed text mode

**TestFeedE2E** (2 tests) — E2E (live)

- `test_feed_returns_data` — feed returns data
- `test_feed_count_parameter` — feed count parameter

**TestProfileE2E** (2 tests) — E2E (live)

- `test_profile_me` — profile me
- `test_profile_get_williamhgates` — profile get williamhgates

**TestCompanyE2E** (2 tests) — E2E (live)

- `test_company_anthropic` — company anthropic
- `test_company_has_organization_key` — company has organization key

**TestJobsE2E** (2 tests) — E2E (live)

- `test_jobs_search_returns_elements` — jobs search returns elements
- `test_job_cards_have_title` — job cards have title

---


## Part 2: Test Results


**Date:** 2026-04-07 13:58 UTC


### Summary

| Metric | Value |
|--------|-------|
| Total tests | 0 |
| Passed | 0 |
| Failed | 0 |
| Errors | 0 |
| Skipped | 0 |
| Pass rate | N/A |
| Execution time | 16.34s |
| Date | 2026-04-07 13:58 UTC |

### Raw Output

```
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\סמדרזנד\CLI-Anything-WEB\linkedin\agent-harness
plugins: anyio-4.13.0
collected 69 items

cli_web\linkedin\tests\test_core.py .................................... [ 52%]
............                                                             [ 69%]
cli_web\linkedin\tests\test_e2e.py .....................                 [100%]

============================= 69 passed in 16.34s =============================
```
