# TEST.md — cli-web-hackernews Test Plan & Results


## Part 1: Test Plan


### Test Inventory

| File | Tests | Layer |
|------|-------|-------|
| test_core.py | 31 | Unit (mocked) |
| test_e2e.py | 30 | E2E (live) + Subprocess |

**Total: 61 tests**


### test_core.py

**TestStoryModel** (4 tests) — Unit (mocked)

- `test_to_dict_includes_computed` — to dict includes computed
- `test_domain_extraction` — domain extraction
- `test_domain_empty_when_no_url` — domain empty when no url
- `test_age_empty_when_no_time` — age empty when no time

**TestCommentModel** (3 tests) — Unit (mocked)

- `test_text_plain_strips_html` — text plain strips html
- `test_text_plain_unescapes_entities` — text plain unescapes entities
- `test_text_plain_empty` — text plain empty

**TestUserModel** (2 tests) — Unit (mocked)

- `test_to_dict_trims_submitted` — to dict trims submitted
- `test_about_plain` — about plain

**TestSearchResultModel** (1 tests) — Unit (mocked)

- `test_to_dict` — to dict

**TestClientHTTPErrors** (5 tests) — Unit (mocked)

- `test_rate_limit_raises` — rate limit raises
- `test_server_error_raises` — server error raises
- `test_404_raises_not_found` — 404 raises not found
- `test_network_error_raises` — network error raises
- `test_timeout_raises_network_error` — timeout raises network error

**TestClientParsing** (4 tests) — Unit (mocked)

- `test_get_story_builds_model` — get story builds model
- `test_get_user_builds_model` — get user builds model
- `test_get_user_not_found` — get user not found
- `test_search_builds_results` — search builds results

**TestExceptionsToDicts** (6 tests) — Unit (mocked)

- `test_app_error_to_dict` — app error to dict
- `test_rate_limit_error_to_dict` — rate limit error to dict
- `test_server_error_to_dict` — server error to dict
- `test_not_found_to_dict` — not found to dict
- `test_auth_error_to_dict` — auth error to dict
- `test_auth_error_recoverable` — auth error recoverable

**TestAuthModule** (6 tests) — Unit (mocked)

- `test_require_auth_raises_without_cookie` — require auth raises without cookie
- `test_require_auth_returns_cookie` — require auth returns cookie
- `test_extract_auth_token_from_html` — extract auth token from html
- `test_extract_auth_token_missing_raises` — extract auth token missing raises
- `test_parse_stories_from_html_extracts_ids` — parse stories from html extracts ids
- `test_authenticated_get_html_403_raises_auth_error` — authenticated get html 403 raises auth error

### test_e2e.py

**TestStoriesFeedE2E** (8 tests) — E2E (live)

- `test_top_stories_returns_list` — top stories returns list
- `test_new_stories_returns_list` — new stories returns list
- `test_best_stories_returns_list` — best stories returns list
- `test_ask_stories_returns_list` — ask stories returns list
- `test_show_stories_returns_list` — show stories returns list
- `test_job_stories_returns_list` — job stories returns list
- `test_story_has_required_fields` — story has required fields
- `test_story_ids_returns_ints` — story ids returns ints

**TestStoryViewE2E** (2 tests) — E2E (live)

- `test_get_story_by_id` — get story by id
- `test_get_comments_for_story` — get comments for story

**TestUserE2E** (2 tests) — E2E (live)

- `test_get_user_profile` — get user profile
- `test_get_nonexistent_user_raises` — get nonexistent user raises

**TestSearchE2E** (3 tests) — E2E (live)

- `test_search_stories` — search stories
- `test_search_by_date` — search by date
- `test_search_comments` — search comments

**TestSubprocess** (11 tests) — Subprocess

- `test_version` — version
- `test_help` — help
- `test_stories_top_json` — stories top json
- `test_search_stories_json` — search stories json
- `test_user_view_json` — user view json
- `test_stories_view_json` — stories view json
- `test_auth_status_json` — auth status json
- `test_auth_help` — auth help
- `test_upvote_help` — upvote help
- `test_submit_help` — submit help
- `test_comment_help` — comment help

**TestAuthActionsE2E** (4 tests) — E2E (live)

- `test_upvote_story` — upvote story
- `test_get_submissions` — get submissions
- `test_favorite_and_list` — favorite and list
- `test_auth_validate` — auth validate

---

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
