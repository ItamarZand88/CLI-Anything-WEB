# Test Code Examples

Unit test patterns, RPC codec testing, and browser-delegated auth test flows.

## Unit Test Pattern

```python
from unittest.mock import patch, MagicMock

def test_client_get_boards():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"boards": [{"id": 1, "name": "Sprint"}]}

    with patch("cli_web.<app>.core.client.httpx.get", return_value=mock_response):
        result = get_boards()
        assert len(result["boards"]) == 1
        assert result["boards"][0]["name"] == "Sprint"
```

## Testing with Browser-Delegated Auth

For apps that use browser-delegated auth (Google batchexecute, etc.), tests need
more than just cookies -- they need fresh CSRF and session tokens too.

**Test setup flow:**
1. Ensure playwright-cli is available (`npx @playwright/cli@latest --version`)
2. `cli-web-<app> auth login` -- captures auth state via playwright-cli state-save
3. Auth module automatically fetches CSRF + session tokens via HTTP GET
4. `cli-web-<app> auth status` -- must show cookies, CSRF token, AND session ID
5. If first API call gets 401, the client should auto-refresh tokens before failing

## Unit Tests for RPC Protocols

When the app uses batchexecute or custom RPC, add unit tests for the codec:
- Test `rpc/encoder.py`: verify triple-nested array format, URL encoding
- Test `rpc/decoder.py`: verify anti-XSSI stripping, chunked parsing, double-JSON decode
- Use captured response fixtures in `tests/fixtures/` for decoder tests
- Test error response detection (`"er"` entries in batchexecute)
- Test auth error detection and refresh trigger
