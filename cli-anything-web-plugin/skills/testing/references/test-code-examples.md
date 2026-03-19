# Test Code Examples

## HTML Scraper Fixture Realism

Unit test fixtures for HTML-parsed endpoints must mirror the real page's CSS class
structure — not a generic simplified table. The parser was written to match specific
CSS classes; if the fixture doesn't have those classes, it won't catch parser bugs.

**Wrong** — generic structure, passes even with a completely broken parser:
```python
PLAYER_LIST_HTML = """
<table>
  <tr><td>Mbappe</td><td>ST</td><td>91</td><td>1000000</td></tr>
</table>
"""
```

**Right** — matches the real CSS classes the parser targets:
```python
PLAYER_LIST_HTML = """
<table id="repTb">
  <thead><tr><th>Name</th><th>Rating</th><th>Pos</th><th>PS Price</th></tr></thead>
  <tbody>
    <tr>
      <td class="table-name">
        <a class="player-row-playercard" href="/26/player/40/kylian-mbappe">91</a>
        <a class="table-player-name" href="/26/player/40/kylian-mbappe">Kylian Mbappé</a>
      </td>
      <td class="table-rating">91</td>
      <td class="table-pos">
        <div class="table-pos-main"><span>ST</span></div>
      </td>
      <td class="platform-ps-only">
        <div class="price">1.07M<img alt="Coin"></div>
      </td>
    </tr>
  </tbody>
</table>
"""

def test_parse_player_table():
    soup = BeautifulSoup(PLAYER_LIST_HTML, "html.parser")
    players = client._parse_player_table(soup, year=26)
    assert len(players) == 1
    assert players[0].name == "Kylian Mbappé"   # not "91"
    assert players[0].position == "ST"            # not "ST++" or ""
    assert players[0].ps_price == 1_070_000       # not None
```

**When to apply:** any parser that calls `.find(class_=...)` or `.find_all(...)`.
If the module only parses JSON (`resp.json()`), skip this — JSON fixtures are
naturally structural.

**Practical check:** look at your parser's `.find(class_="...")` calls. If the
fixture HTML doesn't contain those exact class names, the fixture is not testing
the real code path.

## Asserting List/Search Results

`assert isinstance(results, list)` doesn't catch a broken parser — an empty list
or a list of objects with `name=""` and `price=None` both pass it.

**Wrong:**
```python
results = client.list_players(position="GK")
assert isinstance(results, list)   # passes even if all names are "" and prices are None
```

**Right** — assert on actual field values:
```python
results = client.list_players(position="GK", rating_min=85)
assert len(results) > 0, "Expected results for GK filter"
p = results[0]
assert p.name != "" and not p.name.isdigit(), f"Bad name: {p.name!r}"
assert p.position == "GK", f"Bad position: {p.position!r}"
assert p.ps_price is not None and p.ps_price > 0, f"Bad price: {p.ps_price}"
```

**When to apply:** HTML-scraped list endpoints where the parser can silently return
wrong values without raising exceptions. For JSON APIs that deserialize into typed
models, a type check is often sufficient.

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
