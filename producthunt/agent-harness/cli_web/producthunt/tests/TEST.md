# TEST.md -- cli-web-producthunt Test Plan & Results

## Part 1: Test Plan

### test_core.py -- Unit tests (mocked HTTP)

| # | Class | Test | What it verifies |
|---|-------|------|-----------------|
| 1 | TestParsePostCards | test_returns_list_of_posts | _parse_post_cards returns correct number of Post objects |
| 2 | TestParsePostCards | test_name_extraction | Post name is extracted from link text, rank prefix stripped |
| 3 | TestParsePostCards | test_slug_extraction | Slug parsed from href path |
| 4 | TestParsePostCards | test_rank_from_prefix | Rank integer parsed from "1. Name" prefix |
| 5 | TestParsePostCards | test_votes_and_comments | Votes/comments extracted from button elements |
| 6 | TestParsePostCards | test_topics_from_links | Topics extracted from /topics/ anchor links |
| 7 | TestParsePostCards | test_tagline_from_sibling | Tagline from next sibling element |
| 8 | TestParsePostCards | test_thumbnail_url | Thumbnail from img src |
| 9 | TestParsePostCards | test_post_id_from_data_test | ID from data-test="post-name-{id}" |
| 10 | TestParsePostCards | test_url_built_from_slug | URL = base + /products/ + slug |
| 11 | TestParseProductDetail | test_title_parsing | Title from <title> with suffix stripped |
| 12 | TestParseProductDetail | test_description_from_meta | Description from meta[name=description] |
| 13 | TestParseProductDetail | test_topics_extraction | Topics from /topics/ links on detail page |
| 14 | TestParseProductDetail | test_thumbnail_from_og_image | Thumbnail from og:image meta tag |
| 15 | TestParseProductDetail | test_votes_and_comments | Votes/comments from buttons on detail page |
| 16 | TestParseUserProfile | test_name_parsing | Name from og:title, (@username) stripped |
| 17 | TestParseUserProfile | test_headline | Headline from meta description |
| 18 | TestParseUserProfile | test_profile_image | Profile image from og:image |
| 19 | TestParseUserProfile | test_followers_count | Followers parsed from "N Followers" text |
| 20 | TestClientHTTPErrors | test_403_raises_auth_error | 403 -> AuthError (Cloudflare) |
| 21 | TestClientHTTPErrors | test_404_raises_not_found_error | 404 -> NotFoundError |
| 22 | TestClientHTTPErrors | test_429_raises_rate_limit_error | 429 -> RateLimitError |
| 23 | TestClientHTTPErrors | test_429_with_retry_after | 429 with Retry-After header parsed |
| 24 | TestClientHTTPErrors | test_500_raises_server_error | 500 -> ServerError |
| 25 | TestClientHTTPErrors | test_502_raises_server_error | 502 -> ServerError |
| 26 | TestClientHTTPErrors | test_network_exception_raises_network_error | Connection error -> NetworkError |
| 27 | TestExceptions | test_app_error_to_dict | AppError.to_dict() code=UNKNOWN |
| 28 | TestExceptions | test_auth_error_to_dict | AuthError.to_dict() code=AUTH_EXPIRED |
| 29 | TestExceptions | test_rate_limit_error_to_dict | RateLimitError.to_dict() with retry_after |
| 30 | TestExceptions | test_not_found_error_to_dict | NotFoundError.to_dict() code=NOT_FOUND |
| 31 | TestExceptions | test_server_error_to_dict | ServerError.to_dict() code=SERVER_ERROR |
| 32 | TestExceptions | test_network_error_to_dict | NetworkError.to_dict() code=NETWORK_ERROR |
| 33 | TestExceptions | test_graphql_error_to_dict | GraphQLError.to_dict() code=GRAPHQL_ERROR |
| 34 | TestModels | test_post_to_dict_contains_all_keys | Post.to_dict() serialization |
| 35 | TestModels | test_post_from_card_strips_rank | from_card rank prefix parsing |
| 36 | TestModels | test_post_from_card_no_rank | from_card without rank prefix |
| 37 | TestModels | test_user_to_dict_contains_all_keys | User.to_dict() serialization |
| 38 | TestModels | test_user_from_card | User.from_card defaults |

### test_e2e.py -- E2E + subprocess tests (live network)

| # | Class | Test | What it verifies |
|---|-------|------|-----------------|
| 1 | TestLiveAPI | test_list_posts | Homepage returns Post list with name/slug |
| 2 | TestLiveAPI | test_get_post | Known product "producthunt" returns name/description |
| 3 | TestLiveAPI | test_leaderboard | Daily leaderboard returns ranked posts |
| 4 | TestLiveAPI | test_get_user | @rrhoover has name Ryan, >100k followers |
| 5 | TestLiveAPI | test_list_posts_have_urls | Posts have properly formed PH URLs |
| 6 | TestCLISubprocess | test_help | --help exits 0 |
| 7 | TestCLISubprocess | test_posts_list_json | posts list --json returns valid JSON list |
| 8 | TestCLISubprocess | test_posts_get_json | posts get --json returns product dict |
| 9 | TestCLISubprocess | test_auth_status_json | auth status --json says no auth required |
| 10 | TestCLISubprocess | test_version | --version exits 0 |
| 11 | TestCLISubprocess | test_posts_leaderboard_json | leaderboard --json returns list |
| 12 | TestCLISubprocess | test_users_get_json | users get --json returns user dict |
| 13 | TestCLISubprocess | test_invalid_command | Nonexistent command exits non-zero |

**Total: 38 unit + 13 E2E = 51 tests**

## Part 2: Test Results

```
============================= test session starts =============================
platform win32 -- Python 3.12.8, pytest-8.3.4, pluggy-1.5.0
rootdir: producthunt/agent-harness
collected 51 items

cli_web/producthunt/tests/test_core.py::TestParsePostCards::test_name_extraction PASSED [  1%]
cli_web/producthunt/tests/test_core.py::TestParsePostCards::test_post_id_from_data_test PASSED [  3%]
cli_web/producthunt/tests/test_core.py::TestParsePostCards::test_rank_from_prefix PASSED [  5%]
cli_web/producthunt/tests/test_core.py::TestParsePostCards::test_returns_list_of_posts PASSED [  7%]
cli_web/producthunt/tests/test_core.py::TestParsePostCards::test_slug_extraction PASSED [  9%]
cli_web/producthunt/tests/test_core.py::TestParsePostCards::test_tagline_from_sibling PASSED [ 11%]
cli_web/producthunt/tests/test_core.py::TestParsePostCards::test_thumbnail_url PASSED [ 13%]
cli_web/producthunt/tests/test_core.py::TestParsePostCards::test_topics_from_links PASSED [ 15%]
cli_web/producthunt/tests/test_core.py::TestParsePostCards::test_url_built_from_slug PASSED [ 17%]
cli_web/producthunt/tests/test_core.py::TestParsePostCards::test_votes_and_comments PASSED [ 19%]
cli_web/producthunt/tests/test_core.py::TestParseProductDetail::test_description_from_meta PASSED [ 21%]
cli_web/producthunt/tests/test_core.py::TestParseProductDetail::test_thumbnail_from_og_image PASSED [ 23%]
cli_web/producthunt/tests/test_core.py::TestParseProductDetail::test_title_parsing PASSED [ 25%]
cli_web/producthunt/tests/test_core.py::TestParseProductDetail::test_topics_extraction PASSED [ 27%]
cli_web/producthunt/tests/test_core.py::TestParseProductDetail::test_votes_and_comments PASSED [ 29%]
cli_web/producthunt/tests/test_core.py::TestParseUserProfile::test_followers_count PASSED [ 31%]
cli_web/producthunt/tests/test_core.py::TestParseUserProfile::test_headline PASSED [ 33%]
cli_web/producthunt/tests/test_core.py::TestParseUserProfile::test_name_parsing PASSED [ 35%]
cli_web/producthunt/tests/test_core.py::TestParseUserProfile::test_profile_image PASSED [ 37%]
cli_web/producthunt/tests/test_core.py::TestClientHTTPErrors::test_403_raises_auth_error PASSED [ 39%]
cli_web/producthunt/tests/test_core.py::TestClientHTTPErrors::test_404_raises_not_found_error PASSED [ 41%]
cli_web/producthunt/tests/test_core.py::TestClientHTTPErrors::test_429_raises_rate_limit_error PASSED [ 43%]
cli_web/producthunt/tests/test_core.py::TestClientHTTPErrors::test_429_with_retry_after PASSED [ 45%]
cli_web/producthunt/tests/test_core.py::TestClientHTTPErrors::test_500_raises_server_error PASSED [ 47%]
cli_web/producthunt/tests/test_core.py::TestClientHTTPErrors::test_502_raises_server_error PASSED [ 49%]
cli_web/producthunt/tests/test_core.py::TestClientHTTPErrors::test_network_exception_raises_network_error PASSED [ 50%]
cli_web/producthunt/tests/test_core.py::TestExceptions::test_app_error_to_dict PASSED [ 52%]
cli_web/producthunt/tests/test_core.py::TestExceptions::test_auth_error_to_dict PASSED [ 54%]
cli_web/producthunt/tests/test_core.py::TestExceptions::test_graphql_error_to_dict PASSED [ 56%]
cli_web/producthunt/tests/test_core.py::TestExceptions::test_network_error_to_dict PASSED [ 58%]
cli_web/producthunt/tests/test_core.py::TestExceptions::test_not_found_error_to_dict PASSED [ 60%]
cli_web/producthunt/tests/test_core.py::TestExceptions::test_rate_limit_error_to_dict PASSED [ 62%]
cli_web/producthunt/tests/test_core.py::TestExceptions::test_server_error_to_dict PASSED [ 64%]
cli_web/producthunt/tests/test_core.py::TestModels::test_post_from_card_no_rank PASSED [ 66%]
cli_web/producthunt/tests/test_core.py::TestModels::test_post_from_card_strips_rank PASSED [ 68%]
cli_web/producthunt/tests/test_core.py::TestModels::test_post_to_dict_contains_all_keys PASSED [ 70%]
cli_web/producthunt/tests/test_core.py::TestModels::test_user_from_card PASSED [ 72%]
cli_web/producthunt/tests/test_core.py::TestModels::test_user_to_dict_contains_all_keys PASSED [ 74%]
cli_web/producthunt/tests/test_e2e.py::TestLiveAPI::test_get_post PASSED [ 76%]
cli_web/producthunt/tests/test_e2e.py::TestLiveAPI::test_get_user PASSED [ 78%]
cli_web/producthunt/tests/test_e2e.py::TestLiveAPI::test_leaderboard PASSED [ 80%]
cli_web/producthunt/tests/test_e2e.py::TestLiveAPI::test_list_posts PASSED [ 82%]
cli_web/producthunt/tests/test_e2e.py::TestLiveAPI::test_list_posts_have_urls PASSED [ 84%]
cli_web/producthunt/tests/test_e2e.py::TestCLISubprocess::test_auth_status_json PASSED [ 86%]
cli_web/producthunt/tests/test_e2e.py::TestCLISubprocess::test_help PASSED [ 88%]
cli_web/producthunt/tests/test_e2e.py::TestCLISubprocess::test_invalid_command PASSED [ 90%]
cli_web/producthunt/tests/test_e2e.py::TestCLISubprocess::test_posts_get_json PASSED [ 92%]
cli_web/producthunt/tests/test_e2e.py::TestCLISubprocess::test_posts_leaderboard_json PASSED [ 94%]
cli_web/producthunt/tests/test_e2e.py::TestCLISubprocess::test_posts_list_json PASSED [ 96%]
cli_web/producthunt/tests/test_e2e.py::TestCLISubprocess::test_users_get_json PASSED [ 98%]
cli_web/producthunt/tests/test_e2e.py::TestCLISubprocess::test_version PASSED [100%]

============================= 51 passed in 5.46s ==============================
```
