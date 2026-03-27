# TEST.md — cli-web-hackernews

## Part 1: Test Plan

### Unit Tests (test_core.py)

| Category | Tests | Description |
|----------|-------|-------------|
| Story Model | 4 | to_dict, domain extraction, empty URL/time handling |
| Comment Model | 3 | HTML stripping, entity unescaping, empty text |
| User Model | 2 | submitted list trimming, about_plain HTML strip |
| SearchResult Model | 1 | to_dict serialization |
| HTTP Error Handling | 5 | 429 rate limit, 503 server error, 404 not found, network error, timeout |
| Client Parsing | 4 | Story building, user building, user not found, search results |
| Exception Serialization | 6 | AppError, RateLimitError, ServerError, NotFoundError, AuthError to_dict, recoverable flag |
| Auth Module | 6 | require_auth raises/returns, extract auth token from HTML, missing token raises, parse stories from HTML, 403 raises AuthError |

### E2E Tests (test_e2e.py)

| Category | Tests | Description |
|----------|-------|-------------|
| Stories Feed | 8 | All 6 feeds (top/new/best/ask/show/job), field validation, ID list |
| Story View | 2 | View by ID, get comments |
| User Profile | 2 | Get profile (dang), nonexistent user raises NotFoundError |
| Search | 3 | Stories search, date sort, comment search |
| Subprocess (read) | 6 | --version, --help, stories top --json, search --json, user --json, view --json |
| Subprocess (auth) | 5 | auth status --json, auth --help, upvote --help, submit --help, comment --help |
| Auth Actions (E2E) | 4 | Upvote story, get submissions, favorite story, validate auth |

**Total: 61 tests (31 unit + 30 E2E)**

## Part 2: Test Results

```
============================= 31 passed in 0.32s ==============================
(test_core.py — all unit tests pass)

============================= 30 passed in 159.47s ============================
(test_e2e.py — all E2E + subprocess + auth tests pass)
```

**Pass Rate: 61/61 (100%)**

### Notes
- E2E tests hit live Firebase API, Algolia search API, and HN web endpoints
- Subprocess tests use `_resolve_cli()` with `CLI_WEB_FORCE_INSTALLED=1`
- Auth E2E tests require valid `auth.json` (fail, not skip, without it)
- Auth actions (upvote, favorite) scrape CSRF tokens from page HTML
- Parallel HTTP fetching via asyncio in client
