"""Tests for analyze-traffic.py: protocol detection, noise filtering, helpers."""
from __future__ import annotations


def _entry(url, method="GET", status=200, post_data=None, req_headers=None, resp_headers=None, mime="application/json"):
    """Build a traffic entry in the shape produced by parse-trace.py."""
    return {
        "url": url,
        "method": method,
        "status": status,
        "mime_type": mime,
        "post_data": post_data,
        "request_headers": req_headers or {},
        "response_headers": resp_headers or {},
        "response_body": None,
    }


# --- Header normalization ---

def test_normalize_headers_accepts_dict(analyze_traffic):
    assert analyze_traffic._normalize_headers({"A": "1"}) == {"A": "1"}


def test_normalize_headers_accepts_list_format(analyze_traffic):
    playwright_style = [{"name": "A", "value": "1"}, {"name": "B", "value": "2"}]
    assert analyze_traffic._normalize_headers(playwright_style) == {"A": "1", "B": "2"}


def test_normalize_headers_handles_none(analyze_traffic):
    assert analyze_traffic._normalize_headers(None) == {}


def test_normalize_headers_handles_malformed_list(analyze_traffic):
    # Non-dict list items must not crash the normalizer
    result = analyze_traffic._normalize_headers([{"name": "A", "value": "1"}, "not-a-dict"])
    assert result == {"A": "1"}


# --- Noise detection ---

def test_noise_detects_google_analytics(analyze_traffic):
    assert analyze_traffic._is_noise_url("https://google-analytics.com/collect") is True


def test_noise_detects_facebook_tracking(analyze_traffic):
    assert analyze_traffic._is_noise_url("https://facebook.com/tr?id=1") is True


def test_noise_detects_datadog(analyze_traffic):
    assert analyze_traffic._is_noise_url("https://browser-intake-datadoghq.com/v1/input") is True


def test_noise_rejects_real_api(analyze_traffic):
    assert analyze_traffic._is_noise_url("https://api.example.com/v1/users") is False


def test_noise_rejects_graphql_endpoint(analyze_traffic):
    assert analyze_traffic._is_noise_url("https://example.com/graphql") is False


# --- Protocol detection ---

def test_detect_protocol_graphql(analyze_traffic):
    entries = [
        _entry("https://api.example.com/graphql", method="POST",
               post_data='{"operationName":"GetUser","query":"query GetUser {user{id}}"}'),
        _entry("https://api.example.com/graphql", method="POST",
               post_data='{"operationName":"UpdateUser","query":"mutation UpdateUser {updateUser(id:1){id}}"}'),
    ]
    result = analyze_traffic.detect_protocol(entries)
    assert result["protocol"] == "graphql"
    op_names = [op["name"] for op in result["graphql_operations"]]
    assert "GetUser" in op_names
    assert "UpdateUser" in op_names


def test_detect_protocol_batchexecute(analyze_traffic):
    entries = [
        _entry(
            "https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute?rpcids=abc123&source=bl",
            method="POST",
            post_data='f.req=%5B%5B%5B%22abc123%22%2C%22%5B%5D%22%2Cnull%2C%22generic%22%5D%5D%5D',
        )
    ]
    result = analyze_traffic.detect_protocol(entries)
    assert result["protocol"] == "batchexecute"
    assert "abc123" in result["batchexecute_rpc_ids"]


def test_detect_protocol_rest(analyze_traffic):
    entries = [
        _entry("https://api.example.com/v1/users"),
        _entry("https://api.example.com/v1/users/1"),
        _entry("https://api.example.com/v1/posts"),
    ]
    result = analyze_traffic.detect_protocol(entries)
    assert result["protocol"] == "rest"


def test_detect_protocol_ignores_noise(analyze_traffic):
    """Pure tracking traffic must not be classified as a real protocol."""
    entries = [
        _entry("https://google-analytics.com/collect", method="POST"),
        _entry("https://facebook.com/tr?id=1", method="POST"),
    ]
    result = analyze_traffic.detect_protocol(entries)
    # With only noise, confidence should be low or protocol "unknown"
    assert result["confidence"] <= 50 or result["protocol"] in ("unknown", "rest")


# --- End-to-end analyze() ---

def test_analyze_empty_input(analyze_traffic):
    report = analyze_traffic.analyze([])
    assert "protocol" in report
    assert "auth" in report
    assert "stats" in report
    assert report["stats"]["total_requests"] == 0


def test_analyze_returns_all_sections(analyze_traffic):
    entries = [_entry("https://api.example.com/v1/users")]
    report = analyze_traffic.analyze(entries)
    for key in (
        "_meta", "protocol", "auth", "protections", "endpoints",
        "rate_limits", "pagination", "stats", "suggested_commands",
        "request_sequence", "session_lifecycle", "endpoint_sizes",
    ):
        assert key in report, f"missing section: {key}"


def test_analyze_meta_reports_version(analyze_traffic):
    report = analyze_traffic.analyze([])
    assert report["_meta"]["tool"] == "analyze-traffic.py"
    assert "version" in report["_meta"]
