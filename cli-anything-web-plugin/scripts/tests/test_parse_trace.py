"""Tests for parse-trace.py: .network file parsing, static-asset filtering."""
from __future__ import annotations

import json
from pathlib import Path


def _write_trace(traces_dir: Path, entries: list[dict]) -> Path:
    """Write a minimal .network file + resources/ structure."""
    traces_dir.mkdir(parents=True, exist_ok=True)
    resources_dir = traces_dir / "resources"
    resources_dir.mkdir(exist_ok=True)

    lines = []
    for entry in entries:
        body = entry.pop("_body", None)
        sha1 = None
        if body is not None:
            sha1 = f"sha_{len(lines)}"
            (resources_dir / sha1).write_text(
                body if isinstance(body, str) else json.dumps(body)
            )
        resp = entry.get("snapshot", {}).get("response", {})
        if sha1:
            resp.setdefault("content", {})["_sha1"] = sha1
        lines.append(json.dumps(entry))

    network_file = traces_dir / "test.network"
    network_file.write_text("\n".join(lines) + "\n")
    return network_file


def _make_entry(url: str, method: str = "GET", status: int = 200, body=None) -> dict:
    entry = {
        "type": "resource-snapshot",
        "snapshot": {
            "request": {
                "url": url,
                "method": method,
                "headers": [{"name": "User-Agent", "value": "test"}],
            },
            "response": {
                "status": status,
                "headers": [{"name": "Content-Type", "value": "application/json"}],
                "content": {"mimeType": "application/json"},
            },
            "time": 12.3,
        },
    }
    if body is not None:
        entry["_body"] = body
    return entry


def test_parse_single_json_entry(parse_trace, tmp_path):
    _write_trace(tmp_path, [_make_entry("https://api.example.com/items", body={"ok": True})])

    entries = parse_trace.parse_traces(tmp_path)
    assert len(entries) == 1
    assert entries[0]["url"] == "https://api.example.com/items"
    assert entries[0]["method"] == "GET"
    assert entries[0]["status"] == 200
    assert entries[0]["response_body"] == {"ok": True}


def test_parse_filters_static_assets_by_default(parse_trace, tmp_path):
    _write_trace(tmp_path, [
        _make_entry("https://cdn.example.com/style.css"),
        _make_entry("https://cdn.example.com/script.js"),
        _make_entry("https://cdn.example.com/logo.png"),
        _make_entry("https://api.example.com/data", body={"ok": True}),
    ])

    entries = parse_trace.parse_traces(tmp_path, filter_static=True)
    assert len(entries) == 1
    assert entries[0]["url"].endswith("/data")


def test_parse_includes_static_when_requested(parse_trace, tmp_path):
    _write_trace(tmp_path, [
        _make_entry("https://cdn.example.com/style.css"),
        _make_entry("https://api.example.com/data"),
    ])

    entries = parse_trace.parse_traces(tmp_path, filter_static=False)
    assert len(entries) == 2


def test_parse_ignores_non_snapshot_events(parse_trace, tmp_path):
    tmp_path.mkdir(exist_ok=True)
    net = tmp_path / "x.network"
    net.write_text(json.dumps({"type": "other-event"}) + "\n")

    entries = parse_trace.parse_traces(tmp_path)
    assert entries == []


def test_parse_handles_empty_network_file(parse_trace, tmp_path):
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "empty.network").write_text("")

    entries = parse_trace.parse_traces(tmp_path)
    assert entries == []


def test_parse_skips_malformed_json_lines(parse_trace, tmp_path):
    tmp_path.mkdir(exist_ok=True)
    good = _make_entry("https://api.example.com/items", body={"ok": True})
    net = tmp_path / "x.network"
    net.write_text("not-json-at-all\n" + json.dumps(good) + "\n")

    # Need to put the body file in resources/
    (tmp_path / "resources").mkdir(exist_ok=True)

    entries = parse_trace.parse_traces(tmp_path)
    assert len(entries) == 1


def test_parse_falls_back_to_text_body_when_not_json(parse_trace, tmp_path):
    _write_trace(tmp_path, [_make_entry("https://api.example.com/p", body="<html>plain</html>")])
    entries = parse_trace.parse_traces(tmp_path)
    assert entries[0]["response_body"] == "<html>plain</html>"


def test_parse_latest_only_picks_newest(parse_trace, tmp_path):
    import os, time
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "resources").mkdir(exist_ok=True)

    old = _make_entry("https://api.example.com/old")
    (tmp_path / "1.network").write_text(json.dumps(old) + "\n")
    time.sleep(0.05)
    new = _make_entry("https://api.example.com/new")
    (tmp_path / "2.network").write_text(json.dumps(new) + "\n")
    # Force 2.network to be newer
    os.utime(tmp_path / "1.network", (1, 1))

    entries = parse_trace.parse_traces(tmp_path, latest_only=True)
    assert len(entries) == 1
    assert "/new" in entries[0]["url"]


def test_parse_empty_dir_returns_empty(parse_trace, tmp_path):
    assert parse_trace.parse_traces(tmp_path) == []
