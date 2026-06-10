# TEST.md — cli-web-youtube

## Part 1: Test Plan

### Test Files
- `test_core.py` — 28 unit tests (mocked HTTP, no network)
- `test_e2e.py` — 27 E2E tests (live InnerTube API + CLI subprocess, marked `e2e`)

### Unit Test Coverage

#### Models (5 tests)
- `format_video_from_renderer` — extracts all fields from videoRenderer
- `format_video_from_renderer` — handles empty renderer
- `format_video_detail` — extracts full detail with microformat
- `format_video_detail` — handles missing microformat
- `format_channel` — extracts pageHeaderRenderer format

#### Exceptions (7 tests)
- `YouTubeError.to_dict()` returns structured JSON
- `AuthError` has code AUTH_EXPIRED
- `RateLimitError.to_dict()` includes retry_after
- `ServerError` stores status_code
- `NotFoundError`, `ParseError`, `NetworkError` have correct codes

#### Helpers (4 tests)
- `handle_errors` exits 1 on YouTubeError
- `handle_errors` exits 1 on unexpected error
- `handle_errors` JSON mode outputs structured error
- `handle_errors` JSON mode includes retry_after for RateLimitError

#### Client (5 tests, mocked httpx)
- Search returns videos list with estimated_results
- Video detail returns full info
- 404 raises NotFoundError
- 429 raises RateLimitError with retry_after
- 500 raises ServerError with status_code

#### CLI Click (7 tests)
- `--help` lists all command groups
- `--version` shows 0.1.0
- `search --help` shows videos subcommand
- `video --help` shows get subcommand
- `search videos` returns JSON with query + videos
- `video get` returns JSON with video details
- `video get` extracts ID from full YouTube URL

### E2E Test Coverage (`test_e2e.py`, live network — no auth required)

#### Live API — Python layer (11 tests)
- Search: returns videos + estimated_results, respects `--limit`, field shapes (11-char id, watch URL), no protocol leakage
- Video detail: known video (dQw4w9WgXcQ) fields, numeric view count, unknown ID raises `NotFoundError`
- Trending: `now` and `music` categories return videos with titles
- Channel: `@YouTube` returns title + `UC...` channel_id, recent_videos list

#### CLI Subprocess — `TestCLISubprocess` (16 tests)
- Resolves binary via `_resolve_cli("cli-web-youtube")` (`CLI_WEB_FORCE_INSTALLED=1` forces installed binary; falls back to `python -m cli_web.youtube`); `_run` sets no `cwd`
- `--help` exits 0 and lists all command groups; `--version` shows 0.1.0
- REPL (default mode) exits cleanly on `exit`; invalid command exits non-zero
- `search videos --json`, `video get --json` (ID + full URL), `trending list --json`, `channel get --json` return parseable JSON with expected fields
- Unknown video ID with `--json` exits non-zero with `{"error": true, "code": "NOT_FOUND"}` envelope
- Global `--json` flag propagates to subcommands; no `wrb.fr`/`af.httprm` protocol leaks
- `--help` works for every command group (search/video/trending/channel)

---

## Part 2: Test Results

### Unit — Run Date: 2026-03-26
### Pass Rate: 100% (28/28)

```
test_core.py::TestModels::test_format_video_from_renderer PASSED
test_core.py::TestModels::test_format_video_from_renderer_empty PASSED
test_core.py::TestModels::test_format_video_detail PASSED
test_core.py::TestModels::test_format_video_detail_no_microformat PASSED
test_core.py::TestModels::test_format_channel_page_header PASSED
test_core.py::TestExceptions::test_youtube_error_to_dict PASSED
test_core.py::TestExceptions::test_auth_error_code PASSED
test_core.py::TestExceptions::test_rate_limit_to_dict_includes_retry_after PASSED
test_core.py::TestExceptions::test_server_error_stores_status_code PASSED
test_core.py::TestExceptions::test_not_found_error PASSED
test_core.py::TestExceptions::test_parse_error PASSED
test_core.py::TestExceptions::test_network_error PASSED
test_core.py::TestHelpers::test_handle_errors_youtube_error_exits_1 PASSED
test_core.py::TestHelpers::test_handle_errors_unexpected_exits_1 PASSED
test_core.py::TestHelpers::test_handle_errors_json_mode_outputs_json PASSED
test_core.py::TestHelpers::test_handle_errors_json_mode_rate_limit PASSED
test_core.py::TestClientMocked::test_search_returns_videos PASSED
test_core.py::TestClientMocked::test_video_detail_returns_info PASSED
test_core.py::TestClientMocked::test_404_raises_not_found PASSED
test_core.py::TestClientMocked::test_429_raises_rate_limit PASSED
test_core.py::TestClientMocked::test_500_raises_server_error PASSED
test_core.py::TestCLIClick::test_help PASSED
test_core.py::TestCLIClick::test_version PASSED
test_core.py::TestCLIClick::test_search_help PASSED
test_core.py::TestCLIClick::test_video_help PASSED
test_core.py::TestCLIClick::test_search_json PASSED
test_core.py::TestCLIClick::test_video_get_json PASSED
test_core.py::TestCLIClick::test_video_get_extracts_id_from_url PASSED

28 passed in 0.24s
```

### E2E — Run Date: 2026-06-10
### Pass Rate: 100% (27/27)

```
python -m pytest cli_web/youtube/tests/test_e2e.py -q
...........................                                              [100%]
27 passed in 18.42s
```

Live network tests hit the real InnerTube API and youtube.com channel pages
(no auth required). Subprocess tests ran via the `python -m cli_web.youtube`
fallback; set `CLI_WEB_FORCE_INSTALLED=1` to require the installed binary.
