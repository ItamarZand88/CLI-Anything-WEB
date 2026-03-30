# TEST.md — cli-web-chatgpt

## Part 1: Test Plan

### Test Files
| File | Layer | Count | Description |
|------|-------|-------|-------------|
| `test_core.py` | Unit | 34 | Exceptions, error handling, auth, sentinel, client error mapping |
| `test_e2e.py` | E2E + Subprocess | 19 | Live API, browser chat/image, CLI subprocess |

### Unit Tests (test_core.py)
- **Exception hierarchy**: All exception types inherit from ChatGPTError
- **AuthError**: recoverable flag, default not recoverable
- **RateLimitError**: retry_after field
- **ServerError**: status_code field
- **handle_errors()**: exit codes (1 for user errors, 2 for system, 130 for interrupt)
- **handle_errors() JSON mode**: structured JSON error output with codes
- **json_error()**: JSON error string formatting with extra fields
- **truncate()**: short text, long text, None, empty
- **Client error mapping**: 401→AuthError, 403→AuthError, 404→NotFoundError, 429→RateLimitError, 5xx→ServerError, 4xx→ChatGPTError
- **Auth module**: load from env var, load from file, save+load round trip, missing raises AuthError, clear_auth removes file
- **Sentinel**: proof-of-work solver produces valid hash, proof token has correct format

### E2E Tests (test_e2e.py)
- **Read-only API** (curl_cffi, no browser):
  - `get_me()` — returns user ID, email, name
  - `get_models()` — returns model list with GPT slugs
  - `list_conversations()` — pagination, item structure
  - `list_recent_images()` — image items with URL and title
  - `get_image_styles()` — style list
- **Chat (Camoufox headless browser)**:
  - Ask simple question → verify text contains expected answer
  - Ask math question → verify Instruments widget extraction
  - Generate image → verify file_id and download_url returned
  - Download generated image → verify PNG/JPEG bytes >1KB
- **File download**:
  - Download recent image from URL

### Subprocess Tests (test_e2e.py)
- `--help` — loads without error
- `--json me` — returns user data
- `--json models` — returns model list
- `--json conversations list` — returns conversation items
- `--json images list` — returns image items
- `--json auth status` — shows logged_in=true
- `--json chat ask` — returns text response, no protocol leakage
- Plain text conversations list — table headers present

---

## Part 2: Test Results

### Run Date: 2026-03-30

### Unit Tests (test_core.py): 34/34 PASSED
```
cli_web/chatgpt/tests/test_core.py::TestExceptions::test_chatgpt_error_is_base PASSED
cli_web/chatgpt/tests/test_core.py::TestExceptions::test_auth_error_recoverable PASSED
cli_web/chatgpt/tests/test_core.py::TestExceptions::test_auth_error_not_recoverable_by_default PASSED
cli_web/chatgpt/tests/test_core.py::TestExceptions::test_rate_limit_error_retry_after PASSED
cli_web/chatgpt/tests/test_core.py::TestExceptions::test_rate_limit_error_no_retry PASSED
cli_web/chatgpt/tests/test_core.py::TestExceptions::test_server_error_status_code PASSED
cli_web/chatgpt/tests/test_core.py::TestHandleErrors::test_auth_error_exits_1 PASSED
cli_web/chatgpt/tests/test_core.py::TestHandleErrors::test_not_found_exits_1 PASSED
cli_web/chatgpt/tests/test_core.py::TestHandleErrors::test_rate_limit_exits_1 PASSED
cli_web/chatgpt/tests/test_core.py::TestHandleErrors::test_server_error_exits_2 PASSED
cli_web/chatgpt/tests/test_core.py::TestHandleErrors::test_network_error_exits_2 PASSED
cli_web/chatgpt/tests/test_core.py::TestHandleErrors::test_keyboard_interrupt_exits_130 PASSED
cli_web/chatgpt/tests/test_core.py::TestHandleErrors::test_json_mode_outputs_json PASSED
cli_web/chatgpt/tests/test_core.py::TestHandleErrors::test_json_mode_rate_limit_includes_retry PASSED
cli_web/chatgpt/tests/test_core.py::TestJsonError::test_basic_error PASSED
cli_web/chatgpt/tests/test_core.py::TestJsonError::test_extra_fields PASSED
cli_web/chatgpt/tests/test_core.py::TestTruncate::test_short_text PASSED
cli_web/chatgpt/tests/test_core.py::TestTruncate::test_long_text PASSED
cli_web/chatgpt/tests/test_core.py::TestTruncate::test_none PASSED
cli_web/chatgpt/tests/test_core.py::TestTruncate::test_empty PASSED
cli_web/chatgpt/tests/test_core.py::TestClientErrorMapping::test_401_raises_auth_error PASSED
cli_web/chatgpt/tests/test_core.py::TestClientErrorMapping::test_403_raises_auth_error PASSED
cli_web/chatgpt/tests/test_core.py::TestClientErrorMapping::test_404_raises_not_found PASSED
cli_web/chatgpt/tests/test_core.py::TestClientErrorMapping::test_429_raises_rate_limit PASSED
cli_web/chatgpt/tests/test_core.py::TestClientErrorMapping::test_500_raises_server_error PASSED
cli_web/chatgpt/tests/test_core.py::TestClientErrorMapping::test_502_raises_server_error PASSED
cli_web/chatgpt/tests/test_core.py::TestClientErrorMapping::test_400_raises_chatgpt_error PASSED
cli_web/chatgpt/tests/test_core.py::TestAuth::test_load_auth_from_env PASSED
cli_web/chatgpt/tests/test_core.py::TestAuth::test_load_auth_missing_raises PASSED
cli_web/chatgpt/tests/test_core.py::TestAuth::test_save_and_load_auth PASSED
cli_web/chatgpt/tests/test_core.py::TestAuth::test_is_logged_in_false PASSED
cli_web/chatgpt/tests/test_core.py::TestAuth::test_clear_auth PASSED
cli_web/chatgpt/tests/test_core.py::TestSentinel::test_solve_proof_of_work PASSED
cli_web/chatgpt/tests/test_core.py::TestSentinel::test_build_proof_token_format PASSED
34 passed in 0.32s
```

### E2E + Subprocess Tests (test_e2e.py): 19/19 PASSED
```
cli_web/chatgpt/tests/test_e2e.py::TestE2EReadOnly::test_get_me PASSED
cli_web/chatgpt/tests/test_e2e.py::TestE2EReadOnly::test_get_models PASSED
cli_web/chatgpt/tests/test_e2e.py::TestE2EReadOnly::test_list_conversations PASSED
cli_web/chatgpt/tests/test_e2e.py::TestE2EReadOnly::test_list_conversations_pagination PASSED
cli_web/chatgpt/tests/test_e2e.py::TestE2EReadOnly::test_list_recent_images PASSED
cli_web/chatgpt/tests/test_e2e.py::TestE2EReadOnly::test_get_image_styles PASSED
cli_web/chatgpt/tests/test_e2e.py::TestE2EChat::test_ask_simple_question PASSED
cli_web/chatgpt/tests/test_e2e.py::TestE2EChat::test_ask_math_question PASSED
cli_web/chatgpt/tests/test_e2e.py::TestE2EChat::test_generate_image PASSED
cli_web/chatgpt/tests/test_e2e.py::TestE2EChat::test_download_generated_image PASSED
cli_web/chatgpt/tests/test_e2e.py::TestE2EFileDownload::test_download_recent_image PASSED
cli_web/chatgpt/tests/test_e2e.py::TestCLISubprocess::test_help PASSED
cli_web/chatgpt/tests/test_e2e.py::TestCLISubprocess::test_json_me PASSED
cli_web/chatgpt/tests/test_e2e.py::TestCLISubprocess::test_json_models PASSED
cli_web/chatgpt/tests/test_e2e.py::TestCLISubprocess::test_json_conversations_list PASSED
cli_web/chatgpt/tests/test_e2e.py::TestCLISubprocess::test_json_images_list PASSED
cli_web/chatgpt/tests/test_e2e.py::TestCLISubprocess::test_json_auth_status PASSED
cli_web/chatgpt/tests/test_e2e.py::TestCLISubprocess::test_json_chat_ask PASSED
cli_web/chatgpt/tests/test_e2e.py::TestCLISubprocess::test_plain_conversations_list PASSED
19 passed in ~166s
```

### Summary
| Metric | Value |
|--------|-------|
| Total tests | 53 |
| Passed | 53 |
| Failed | 0 |
| Pass rate | 100% |
| Unit test time | 0.32s |
| E2E test time | ~166s (includes browser chat + image gen) |
