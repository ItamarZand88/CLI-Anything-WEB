# TEST.md — cli-web-unsplash Test Plan & Results

## Part 1: Test Plan

### Site Profile
- **Type**: No-auth, read-only public API
- **Protocol**: REST JSON via `/napi/` endpoints
- **Auth**: None required

### Test Inventory

| File | Tests | Layer |
|------|-------|-------|
| `test_core.py` | 34 | Unit (mocked HTTP, no network) |
| `test_e2e.py` | 25 | Live API + subprocess |
| **Total** | **59** | |

### Unit Tests (`test_core.py`)

| Class | Tests | What's covered |
|-------|-------|----------------|
| `TestExceptionHierarchy` | 3 | All exceptions inherit from `UnsplashError`, `RateLimitError.retry_after`, `ServerError.status_code` |
| `TestClientErrorMapping` | 6 | 404→`NotFoundError`, 429→`RateLimitError`, 500→`ServerError`, timeout→`NetworkError`, connect error→`NetworkError`, successful JSON parse |
| `TestClientMethods` | 3 | Search params passed correctly, None params omitted, random photo params |
| `TestModels` | 6 | `format_photo_summary`, fallback description, `format_photo_detail` (exif, location, tags), `format_user_summary`, `format_collection_summary`, `format_topic_summary` |
| `TestHelpers` | 10 | `json_error` format + extra fields, `truncate` (short/long/None), `handle_errors` exit codes (1 for user errors, 2 for system, 130 for interrupt), JSON error output in `--json` mode |
| `TestCLIClick` | 6 | `--version`, `--help`, photos search JSON, photos get JSON, topics list JSON, `--json` error output for NotFoundError |

### E2E Live Tests (`test_e2e.py`)

| Class | Tests | What's covered |
|-------|-------|----------------|
| `TestPhotosLive` | 7 | Search, search with filters, photo detail, **list-search-get roundtrip**, statistics, random, autocomplete |
| `TestTopicsLive` | 3 | List topics, get topic detail, topic photos |
| `TestCollectionsLive` | 2 | Search collections, get collection + photos |
| `TestUsersLive` | 4 | Search users, get profile, user photos, user collections |
| `TestCLISubprocess` | 9 | `--help`, `--version`, photos search JSON, photos get JSON, topics list JSON, users get JSON, collections search JSON, random JSON, human-readable output |

### Roundtrip Verification
- **Read-only roundtrip**: Search photos → get first result by ID → verify `id`, `width`, `height`, `likes` match between list and detail views
- **Collection roundtrip**: Search collections → get one by ID → get its photos
- **Topic roundtrip**: List topics → get one by slug → get its photos

---

## Part 2: Test Results

### Run Date: 2026-03-20

```
cli_web/unsplash/tests/test_core.py::TestExceptionHierarchy::test_all_inherit_from_base PASSED
cli_web/unsplash/tests/test_core.py::TestExceptionHierarchy::test_rate_limit_has_retry_after PASSED
cli_web/unsplash/tests/test_core.py::TestExceptionHierarchy::test_server_error_has_status_code PASSED
cli_web/unsplash/tests/test_core.py::TestClientErrorMapping::test_404_raises_not_found PASSED
cli_web/unsplash/tests/test_core.py::TestClientErrorMapping::test_429_raises_rate_limit PASSED
cli_web/unsplash/tests/test_core.py::TestClientErrorMapping::test_500_raises_server_error PASSED
cli_web/unsplash/tests/test_core.py::TestClientErrorMapping::test_timeout_raises_network_error PASSED
cli_web/unsplash/tests/test_core.py::TestClientErrorMapping::test_connect_error_raises_network_error PASSED
cli_web/unsplash/tests/test_core.py::TestClientErrorMapping::test_successful_json_response PASSED
cli_web/unsplash/tests/test_core.py::TestClientMethods::test_search_photos_passes_params PASSED
cli_web/unsplash/tests/test_core.py::TestClientMethods::test_search_photos_omits_none_params PASSED
cli_web/unsplash/tests/test_core.py::TestClientMethods::test_get_random_photos_params PASSED
cli_web/unsplash/tests/test_core.py::TestModels::test_format_photo_summary PASSED
cli_web/unsplash/tests/test_core.py::TestModels::test_format_photo_summary_fallback_description PASSED
cli_web/unsplash/tests/test_core.py::TestModels::test_format_photo_detail PASSED
cli_web/unsplash/tests/test_core.py::TestModels::test_format_user_summary PASSED
cli_web/unsplash/tests/test_core.py::TestModels::test_format_collection_summary PASSED
cli_web/unsplash/tests/test_core.py::TestModels::test_format_topic_summary PASSED
cli_web/unsplash/tests/test_core.py::TestHelpers::test_json_error_format PASSED
cli_web/unsplash/tests/test_core.py::TestHelpers::test_json_error_extra_fields PASSED
cli_web/unsplash/tests/test_core.py::TestHelpers::test_truncate_short_text PASSED
cli_web/unsplash/tests/test_core.py::TestHelpers::test_truncate_long_text PASSED
cli_web/unsplash/tests/test_core.py::TestHelpers::test_truncate_none PASSED
cli_web/unsplash/tests/test_core.py::TestHelpers::test_handle_errors_not_found_exits_1 PASSED
cli_web/unsplash/tests/test_core.py::TestHelpers::test_handle_errors_server_error_exits_2 PASSED
cli_web/unsplash/tests/test_core.py::TestHelpers::test_handle_errors_network_error_exits_2 PASSED
cli_web/unsplash/tests/test_core.py::TestHelpers::test_handle_errors_json_mode_outputs_json PASSED
cli_web/unsplash/tests/test_core.py::TestHelpers::test_handle_errors_keyboard_interrupt_exits_130 PASSED
cli_web/unsplash/tests/test_core.py::TestCLIClick::test_version_flag PASSED
cli_web/unsplash/tests/test_core.py::TestCLIClick::test_help_flag PASSED
cli_web/unsplash/tests/test_core.py::TestCLIClick::test_photos_search_json PASSED
cli_web/unsplash/tests/test_core.py::TestCLIClick::test_photos_get_json PASSED
cli_web/unsplash/tests/test_core.py::TestCLIClick::test_topics_list_json PASSED
cli_web/unsplash/tests/test_core.py::TestCLIClick::test_json_error_on_not_found PASSED
cli_web/unsplash/tests/test_e2e.py::TestPhotosLive::test_search_photos PASSED
cli_web/unsplash/tests/test_e2e.py::TestPhotosLive::test_search_photos_with_filters PASSED
cli_web/unsplash/tests/test_e2e.py::TestPhotosLive::test_get_photo_detail PASSED
cli_web/unsplash/tests/test_e2e.py::TestPhotosLive::test_list_search_get_roundtrip PASSED
cli_web/unsplash/tests/test_e2e.py::TestPhotosLive::test_get_photo_statistics PASSED
cli_web/unsplash/tests/test_e2e.py::TestPhotosLive::test_random_photos PASSED
cli_web/unsplash/tests/test_e2e.py::TestPhotosLive::test_autocomplete PASSED
cli_web/unsplash/tests/test_e2e.py::TestTopicsLive::test_list_topics PASSED
cli_web/unsplash/tests/test_e2e.py::TestTopicsLive::test_get_topic PASSED
cli_web/unsplash/tests/test_e2e.py::TestTopicsLive::test_topic_photos PASSED
cli_web/unsplash/tests/test_e2e.py::TestCollectionsLive::test_search_collections PASSED
cli_web/unsplash/tests/test_e2e.py::TestCollectionsLive::test_get_collection_and_photos PASSED
cli_web/unsplash/tests/test_e2e.py::TestUsersLive::test_search_users PASSED
cli_web/unsplash/tests/test_e2e.py::TestUsersLive::test_get_user_profile PASSED
cli_web/unsplash/tests/test_e2e.py::TestUsersLive::test_user_photos PASSED
cli_web/unsplash/tests/test_e2e.py::TestUsersLive::test_user_collections PASSED
cli_web/unsplash/tests/test_e2e.py::TestCLISubprocess::test_help PASSED
cli_web/unsplash/tests/test_e2e.py::TestCLISubprocess::test_version PASSED
cli_web/unsplash/tests/test_e2e.py::TestCLISubprocess::test_photos_search_json PASSED
cli_web/unsplash/tests/test_e2e.py::TestCLISubprocess::test_photos_get_json PASSED
cli_web/unsplash/tests/test_e2e.py::TestCLISubprocess::test_topics_list_json PASSED
cli_web/unsplash/tests/test_e2e.py::TestCLISubprocess::test_users_get_json PASSED
cli_web/unsplash/tests/test_e2e.py::TestCLISubprocess::test_collections_search_json PASSED
cli_web/unsplash/tests/test_e2e.py::TestCLISubprocess::test_photos_random_json PASSED
cli_web/unsplash/tests/test_e2e.py::TestCLISubprocess::test_human_readable_output PASSED
```

### Summary

| Metric | Value |
|--------|-------|
| Total tests | 59 |
| Passed | 59 |
| Failed | 0 |
| Pass rate | **100%** |
| Execution time | ~25s |
| Date | 2026-03-20 |

### Notes
- No auth required — all endpoints are public
- Read-only site — no create/update/delete tests needed
- Subprocess tests use `_resolve_cli("cli-web-unsplash")` pattern
- All JSON output verified with `json.loads()` and field assertions
