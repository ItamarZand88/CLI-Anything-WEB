import json

import pytest
from cli_web_core import (
    AppError,
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    error_code_for,
    json_error,
    json_success,
    poll_until_complete,
)
from cli_web_core.exceptions import raise_for_status


class FakeResponse:
    def __init__(self, status_code: int, text: str = "", headers: dict | None = None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


# ── exceptions ──────────────────────────────────────────────────────────────


def test_error_codes_map_per_harness_spec():
    assert error_code_for(AuthError("x")) == "AUTH_EXPIRED"
    assert error_code_for(RateLimitError("x")) == "RATE_LIMITED"
    assert error_code_for(NotFoundError("x")) == "NOT_FOUND"
    assert error_code_for(ServerError("x")) == "SERVER_ERROR"
    assert error_code_for(NetworkError("x")) == "NETWORK_ERROR"
    assert error_code_for(AppError("x")) == "UNKNOWN_ERROR"


def test_to_dict_envelope():
    d = RateLimitError("slow down", retry_after=60).to_dict()
    assert d == {"error": True, "code": "RATE_LIMITED", "message": "slow down", "retry_after": 60}


def test_auth_error_recoverable_flag():
    assert AuthError("x").recoverable is True
    assert AuthError("x", recoverable=False).recoverable is False


@pytest.mark.parametrize(
    ("status", "exc_type"),
    [
        (401, AuthError),
        (403, AuthError),
        (404, NotFoundError),
        (429, RateLimitError),
        (500, ServerError),
        (503, ServerError),
    ],
)
def test_raise_for_status_mapping(status, exc_type):
    with pytest.raises(exc_type):
        raise_for_status(FakeResponse(status))


def test_raise_for_status_passes_below_400():
    raise_for_status(FakeResponse(200))
    raise_for_status(FakeResponse(302))


def test_raise_for_status_extracts_retry_after():
    with pytest.raises(RateLimitError) as exc_info:
        raise_for_status(FakeResponse(429, headers={"Retry-After": "30"}))
    assert exc_info.value.retry_after == 30.0


def test_raise_for_status_server_error_carries_status():
    with pytest.raises(ServerError) as exc_info:
        raise_for_status(FakeResponse(502))
    assert exc_info.value.status_code == 502


# ── output envelope ─────────────────────────────────────────────────────────


def test_json_success_envelope():
    payload = json.loads(json_success({"id": 1}, count=1))
    assert payload == {"success": True, "data": {"id": 1}, "count": 1}


def test_json_error_envelope():
    payload = json.loads(json_error("AUTH_EXPIRED", "run auth login", retry_after=5))
    assert payload == {
        "error": True,
        "code": "AUTH_EXPIRED",
        "message": "run auth login",
        "retry_after": 5,
    }


def test_json_output_handles_non_serializable():
    from datetime import datetime

    payload = json.loads(json_success({"when": datetime(2026, 1, 1)}))
    assert "2026" in payload["data"]["when"]


# ── polling ─────────────────────────────────────────────────────────────────


def test_poll_returns_result_with_backoff():
    sleeps: list[float] = []
    attempts = iter([None, None, None, "done"])
    result = poll_until_complete(
        lambda: next(attempts),
        timeout=100,
        initial_delay=2,
        backoff_factor=1.5,
        max_delay=10,
        sleep=sleeps.append,
    )
    assert result == "done"
    assert sleeps == [2, 3.0, 4.5]  # exponential, not fixed


def test_poll_times_out_with_app_error():
    with pytest.raises(AppError, match="timed out"):
        poll_until_complete(lambda: None, timeout=5, initial_delay=2, sleep=lambda _: None)


def test_poll_caps_delay():
    sleeps: list[float] = []
    counter = {"n": 0}

    def check():
        counter["n"] += 1
        return "x" if counter["n"] > 6 else None

    poll_until_complete(check, timeout=1000, initial_delay=4, max_delay=10, sleep=sleeps.append)
    assert max(sleeps) == 10


# ── exit-code contract ──────────────────────────────────────────────────────


def test_exit_codes_per_contract():
    from cli_web_core import (
        EXIT_AUTH,
        EXIT_NETWORK,
        EXIT_NOT_FOUND,
        EXIT_RATE_LIMIT,
        EXIT_SERVER,
        EXIT_UNKNOWN,
        exit_code_for,
    )

    assert exit_code_for(AuthError("x")) == EXIT_AUTH == 3
    assert exit_code_for(NotFoundError("x")) == EXIT_NOT_FOUND == 4
    assert exit_code_for(RateLimitError("x")) == EXIT_RATE_LIMIT == 5
    assert exit_code_for(ServerError("x")) == EXIT_SERVER == 6
    assert exit_code_for(NetworkError("x")) == EXIT_NETWORK == 7
    assert exit_code_for(AppError("x")) == EXIT_UNKNOWN == 1
    assert exit_code_for(ValueError("x")) == EXIT_UNKNOWN == 1


# ── jsonl ───────────────────────────────────────────────────────────────────


def test_json_lines_one_compact_object_per_line():
    from cli_web_core import json_lines

    out = json_lines([{"id": 1, "name": "a"}, {"id": 2}])
    lines = out.splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"id": 1, "name": "a"}
    assert ": " not in lines[0]  # compact separators


def test_json_lines_empty():
    from cli_web_core import json_lines

    assert json_lines([]) == ""
