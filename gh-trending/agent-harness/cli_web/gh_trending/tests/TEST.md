# TEST.md — cli-web-github Test Plan & Results

## Part 1: Test Plan

### Test Inventory

| File | Layer | Count |
|------|-------|-------|
| `test_core.py` | Unit (mocked HTTP) | ~12 tests |
| `test_e2e.py` | E2E live + subprocess | ~10 tests |

### Unit Test Plan (test_core.py)

#### `test_parse_int`
- Parses `"4,859"` → `4859`
- Parses `"1,394 stars today"` → `1394`
- Parses empty string → `0`
- Parses `"0"` → `0`

#### `test_parse_repos_html`
- Fixture: realistic `article.Box-row` HTML with real CSS class names used by parser
- Verifies: at least 1 repo returned
- Verifies: `full_name` is `"owner/name"` format
- Verifies: `stars` > 0
- Verifies: `stars_today` > 0
- Verifies: `rank` starts at 1

#### `test_parse_repos_no_results`
- Fixture: empty article list
- Verifies: `ParseError` raised (cannot find trending repos on page)

#### `test_parse_developers_html`
- Fixture: realistic `article.Box-row.d-flex` HTML with real CSS class names
- Verifies: at least 1 developer returned
- Verifies: `login` is non-empty
- Verifies: `profile_url` starts with `https://github.com/`
- Verifies: `rank` starts at 1

#### `test_client_rate_limit`
- Mocked httpx returning 429 with `retry-after: 30`
- Verifies: `RateLimitError` raised with `retry_after=30`

#### `test_client_server_error`
- Mocked httpx returning 503
- Verifies: `ServerError` raised

#### `test_client_network_error`
- Mocked httpx raising `httpx.ConnectError`
- Verifies: `NetworkError` raised

#### `test_exceptions_to_dict`
- Each exception type serializes to `{"error": True, "code": "...", "message": "..."}`

#### `test_auth_load_missing`
- Auth file absent → `load_cookies()` returns `{}`

#### `test_auth_status_not_configured`
- No auth file → `auth_status()` returns `{"authenticated": False, ...}`

### E2E Live Test Plan (test_e2e.py)

**Note:** GitHub Trending is public — no auth required for E2E tests.

#### `test_trending_repos_today`
- Live fetch of trending repos (daily)
- Verifies: returns list with 1+ items
- Verifies: first item has `full_name` with `/` separator
- Verifies: first item `stars` > 0
- Verifies: first item `stars_today` >= 0
- Verifies: first item `rank == 1`

#### `test_trending_repos_python_weekly`
- Live fetch: `language=python`, `since=weekly`
- Verifies: returns list with 1+ items
- Verifies: all items `language == "Python"` (or None for mixed results)

#### `test_trending_repos_monthly`
- Live fetch: `since=monthly`
- Verifies: returns list with 1+ items

#### `test_trending_developers_today`
- Live fetch of trending developers
- Verifies: returns list with 1+ items
- Verifies: first item has non-empty `login`
- Verifies: first item `rank == 1`

#### `test_trending_developers_weekly`
- Live fetch: `since=weekly`
- Verifies: returns list with 1+ items

### CLI Subprocess Test Plan (test_e2e.py)

#### `TestCLISubprocess::test_help`
- `cli-web-github --help` → exit code 0, contains "repos"

#### `TestCLISubprocess::test_repos_list_json`
- `cli-web-github repos list --json` → valid JSON list
- Verifies: first item has `full_name`, `stars`, `stars_today`, `rank`

#### `TestCLISubprocess::test_repos_list_language_filter`
- `cli-web-github repos list --language python --json` → valid JSON
- Verifies: list is non-empty

#### `TestCLISubprocess::test_developers_list_json`
- `cli-web-github developers list --json` → valid JSON list
- Verifies: first item has `login`, `rank`

#### `TestCLISubprocess::test_auth_status`
- `cli-web-github auth status` → exit code 0

---

## Part 2: Test Results

### Run Date: 2026-03-19
### Pass Rate: 100% (37/37)

```
============================= test session starts =============================
platform win32 -- Python 3.12.8, pytest-8.3.4, pluggy-1.5.0
collected 37 items

test_core.py::TestParseInt::test_comma_separated PASSED
test_core.py::TestParseInt::test_stars_today_text PASSED
test_core.py::TestParseInt::test_empty PASSED
test_core.py::TestParseInt::test_zero PASSED
test_core.py::TestParseInt::test_plain_number PASSED
test_core.py::TestParseReposHTML::test_parses_repo_fields PASSED
test_core.py::TestParseReposHTML::test_description_parsed PASSED
test_core.py::TestParseReposHTML::test_empty_page_raises_parse_error PASSED
test_core.py::TestParseDevelopersHTML::test_parses_developer_fields PASSED
test_core.py::TestParseDevelopersHTML::test_empty_page_raises_parse_error PASSED
test_core.py::TestClientHTTPErrors::test_rate_limit_raises PASSED
test_core.py::TestClientHTTPErrors::test_server_error_raises PASSED
test_core.py::TestClientHTTPErrors::test_network_error_raises PASSED
test_core.py::TestClientHTTPErrors::test_timeout_raises_network_error PASSED
test_core.py::TestExceptionsToDicts::test_app_error_to_dict PASSED
test_core.py::TestExceptionsToDicts::test_auth_error_to_dict PASSED
test_core.py::TestExceptionsToDicts::test_rate_limit_error_to_dict PASSED
test_core.py::TestExceptionsToDicts::test_server_error_to_dict PASSED
test_core.py::TestExceptionsToDicts::test_parse_error_to_dict PASSED
test_core.py::TestAuth::test_load_cookies_missing_file PASSED
test_core.py::TestAuth::test_auth_status_not_configured PASSED
test_core.py::TestAuth::test_load_cookies_from_env PASSED
test_e2e.py::TestTrendingReposLive::test_repos_today PASSED
test_e2e.py::TestTrendingReposLive::test_repos_python_weekly PASSED
test_e2e.py::TestTrendingReposLive::test_repos_monthly PASSED
test_e2e.py::TestTrendingReposLive::test_repos_typescript_since PASSED
test_e2e.py::TestTrendingReposLive::test_repos_to_dict PASSED
test_e2e.py::TestTrendingDevelopersLive::test_developers_today PASSED
test_e2e.py::TestTrendingDevelopersLive::test_developers_weekly PASSED
test_e2e.py::TestTrendingDevelopersLive::test_developers_to_dict PASSED
test_e2e.py::TestCLISubprocess::test_help PASSED
test_e2e.py::TestCLISubprocess::test_repos_list_json PASSED
test_e2e.py::TestCLISubprocess::test_repos_list_language_filter_json PASSED
test_e2e.py::TestCLISubprocess::test_repos_list_since_weekly_json PASSED
test_e2e.py::TestCLISubprocess::test_developers_list_json PASSED
test_e2e.py::TestCLISubprocess::test_auth_status PASSED
test_e2e.py::TestCLISubprocess::test_version PASSED

============================= 37 passed in 26.32s ==============================
```

### Notes
- GitHub Trending is public — no auth required for any E2E test
- Subprocess tests used installed `cli-web-github.EXE` on Windows PATH
- Live E2E tests hit real GitHub servers (no mocking)
