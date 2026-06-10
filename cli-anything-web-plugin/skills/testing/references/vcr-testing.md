# VCR.py Integration Tests

Recorded-cassette tests sit between unit mocks and live E2E: real recorded
responses, replayed offline. Recommended for complex protocols (batchexecute,
GraphQL, custom RPC) where response parsing is the risk.

## Contents
- Setup
- Writing cassette tests
- Recording and replaying
- When to use VCR vs unit mocks
- Marker convention

## Setup

```bash
pip install vcrpy pytest-recording
```

## Writing cassette tests

```python
# test_integration.py
import pytest

@pytest.mark.vcr
def test_list_notebooks(authenticated_client):
    """Recorded against live API, replayed from cassette."""
    notebooks = authenticated_client.notebooks.list()
    assert len(notebooks) > 0
    assert notebooks[0].id
    assert notebooks[0].title
```

Cassettes live at `tests/cassettes/<test_name>.yaml`. Scrub auth headers and
cookies before committing cassettes.

## Recording and replaying

```bash
# Record mode — makes real API calls, saves responses
CLI_WEB_VCR_RECORD=1 pytest tests/test_integration.py -m vcr -v

# Normal mode — replays from cassettes (no network)
pytest tests/test_integration.py -m vcr -v
```

## When to use VCR vs unit mocks

- VCR: complex response parsing, RPC protocols, multi-step API flows
- Unit mocks: simple JSON APIs, error-handling paths, retry logic

## Marker convention

```python
@pytest.mark.vcr       # Replays from cassette
@pytest.mark.e2e       # Requires live API + auth
@pytest.mark.unit      # No network, fast
```
