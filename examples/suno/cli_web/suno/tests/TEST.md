# TEST.md — cli-web-suno Test Plan & Results

## Part 1: Test Plan

### Test Inventory

- `test_core.py`: ~15 unit tests planned
- `test_e2e.py`: ~8 E2E live tests + ~4 subprocess tests

### Unit Test Plan (test_core.py)

**Module: core/client.py**
- Test GET request with mocked httpx
- Test POST request with JSON body
- Test 401 auto-refresh retry
- Test 429 rate limit error
- Test 500 server error
- Test get_feed() builds correct request body
- Expected: 6 tests

**Module: core/auth.py**
- Test save_auth / load_auth round-trip
- Test get_auth_headers with valid JWT
- Test get_auth_headers raises without auth
- Test browser_token format
- Test device_id persistence
- Expected: 5 tests

**Module: core/models.py**
- Test Clip.from_dict with full data
- Test Clip.from_dict with minimal data
- Test Clip.to_summary
- Test BillingInfo.from_dict
- Expected: 4 tests

### E2E Test Plan (test_e2e.py)

**Live tests (require auth):**
1. Auth status — validate_auth returns session with user info
2. Songs list — get_feed returns clips array with expected fields
3. Billing info — get_billing_info returns credits and plans
4. Explore tags — recommend_tags returns recommended_tags array
5. Projects list — list_projects returns projects array
6. Prompts suggestions — get_prompt_suggestions returns prompts
7. Generation status — get_concurrent_status returns running/max
8. Song get — fetch single clip by ID from feed

**Subprocess tests (require pip install -e .):**
1. `cli-web-suno --help` exits 0 with expected text
2. `cli-web-suno --json auth status` returns valid JSON
3. `cli-web-suno --json songs list --limit 1` returns JSON array
4. `cli-web-suno --json billing info` returns credits JSON

### Realistic Workflow Scenarios

**Scenario 1: Auth → Status → Songs**
- Simulates: New user setting up CLI and browsing their library
- Operations: auth status → songs list → songs get (first clip ID)
- Verified: session has user.email, feed has clips, clip has audio_url

**Scenario 2: Explore → Tags → Generate**
- Simulates: User exploring styles and generating a song
- Operations: explore tags → prompts suggestions → (would generate but skip to preserve credits)
- Verified: tags has recommended_tags, suggestions has prompts array

**Scenario 3: Billing → Projects**
- Simulates: User checking their account and workspace
- Operations: billing info → projects list → projects get default
- Verified: billing has credits, projects has at least default workspace

---

## Part 2: Test Results

**Execution date:** 2026-03-15
**Auth method:** from-browser (Chrome debug profile, port 9222)
**Auth status:** Live validation OK (zanditamar@gmail.com / @gigijdjd)

### Unit Tests (test_core.py) — 16/16 PASSED

```
cli_web/suno/tests/test_core.py::TestAuthSaveLoad::test_save_and_load_roundtrip PASSED
cli_web/suno/tests/test_core.py::TestAuthSaveLoad::test_load_returns_none_when_missing PASSED
cli_web/suno/tests/test_core.py::TestAuthHeaders::test_get_auth_headers_with_jwt PASSED
cli_web/suno/tests/test_core.py::TestAuthHeaders::test_get_auth_headers_raises_without_auth PASSED
cli_web/suno/tests/test_core.py::TestAuthHeaders::test_browser_token_is_valid_json PASSED
cli_web/suno/tests/test_core.py::TestAuthHeaders::test_device_id_persists PASSED
cli_web/suno/tests/test_core.py::TestSunoClient::test_get_request PASSED
cli_web/suno/tests/test_core.py::TestSunoClient::test_post_request_with_body PASSED
cli_web/suno/tests/test_core.py::TestSunoClient::test_401_raises_auth_error PASSED
cli_web/suno/tests/test_core.py::TestSunoClient::test_429_raises_rate_limit_error PASSED
cli_web/suno/tests/test_core.py::TestSunoClient::test_500_raises_client_error PASSED
cli_web/suno/tests/test_core.py::TestSunoClient::test_get_feed_builds_correct_body PASSED
cli_web/suno/tests/test_core.py::TestModels::test_clip_from_dict_full PASSED
cli_web/suno/tests/test_core.py::TestModels::test_clip_from_dict_minimal PASSED
cli_web/suno/tests/test_core.py::TestModels::test_clip_to_summary PASSED
cli_web/suno/tests/test_core.py::TestModels::test_billing_info_from_dict PASSED

16 passed in 0.34s
```

### E2E Tests (test_e2e.py) — 12/12 PASSED

```
cli_web/suno/tests/test_e2e.py::TestLiveAuth::test_validate_auth_returns_session PASSED
  [verify] user=zanditamar@gmail.com handle=gigijdjd
cli_web/suno/tests/test_e2e.py::TestLiveSongs::test_list_songs PASSED
  [verify] First clip id=a9a521b7-40dc-4260-9e37-df6417b89a24
cli_web/suno/tests/test_e2e.py::TestLiveSongs::test_get_song_by_id PASSED
  [verify] Got clip with audio_url=https://cdn1.suno.ai/...
cli_web/suno/tests/test_e2e.py::TestLiveBilling::test_billing_info PASSED
  [verify] credits=70 total=120
cli_web/suno/tests/test_e2e.py::TestLiveExplore::test_recommend_tags PASSED
  [verify] Got 20 recommended tags
cli_web/suno/tests/test_e2e.py::TestLiveProjects::test_list_projects PASSED
  [verify] Project id=default name=My Workspace clips=353
cli_web/suno/tests/test_e2e.py::TestLivePrompts::test_prompt_suggestions PASSED
  [verify] Got 10 prompt suggestions
cli_web/suno/tests/test_e2e.py::TestLiveGeneration::test_concurrent_status PASSED
  [verify] Running=0/2
cli_web/suno/tests/test_e2e.py::TestCLISubprocess::test_help PASSED
  [_resolve_cli] Using installed command
cli_web/suno/tests/test_e2e.py::TestCLISubprocess::test_json_auth_status PASSED
cli_web/suno/tests/test_e2e.py::TestCLISubprocess::test_json_songs_list PASSED
cli_web/suno/tests/test_e2e.py::TestCLISubprocess::test_json_billing_info PASSED

12 passed in 11.79s
```

### Summary

| Test file | Tests | Passed | Failed | Pass rate |
|-----------|-------|--------|--------|-----------|
| test_core.py | 16 | 16 | 0 | 100% |
| test_e2e.py | 12 | 12 | 0 | 100% |
| **Total** | **28** | **28** | **0** | **100%** |
