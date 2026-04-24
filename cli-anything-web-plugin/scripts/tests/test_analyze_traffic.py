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


# Noise/header helpers live in traffic_utils and are tested directly in
# test_traffic_utils.py. Tests here focus on detect_protocol / analyze pipelines.


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
    # With only noise, confidence should be low.
    assert result["confidence"] <= 50


def test_detect_protocol_handles_null_url(analyze_traffic):
    """Entry with explicit `url: None` must not crash (was a regression)."""
    entries = [{"url": None, "method": "GET", "status": 200, "request_headers": {}}]
    result = analyze_traffic.detect_protocol(entries)
    assert "protocol" in result  # doesn't crash


def test_detect_protocol_handles_missing_url_field(analyze_traffic):
    """Entry without a `url` key at all must not crash."""
    entries = [{"method": "GET", "status": 200, "request_headers": {}}]
    result = analyze_traffic.detect_protocol(entries)
    assert "protocol" in result


def test_analyze_handles_null_url_entries(analyze_traffic):
    """Full analyze() pipeline must survive entries with null URLs."""
    entries = [{"url": None}, _entry("https://api.example.com/v1/users")]
    report = analyze_traffic.analyze(entries)
    assert report["stats"]["total_requests"] == 2


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
