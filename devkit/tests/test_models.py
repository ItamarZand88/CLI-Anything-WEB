import pytest
from cli_web_devkit.models import (
    Phase,
    PhaseStatus,
    PipelineState,
    TrafficEntry,
    load_entries,
)


def test_traffic_entry_roundtrip():
    raw = {
        "url": "https://api.example.com/v1/items",
        "method": "POST",
        "status": 201,
        "request_headers": {"content-type": "application/json"},
        "response_headers": {},
        "post_data": '{"a": 1}',
        "response_body": {"id": 42},
        "mime_type": "application/json",
        "time_ms": 12.5,
    }
    entry = TrafficEntry.from_dict(raw)
    assert entry.is_write
    assert not entry.is_error
    assert entry.to_dict() == raw


def test_traffic_entry_enhanced_fields_preserved():
    entry = TrafficEntry.from_dict(
        {"url": "https://x.test", "timestamp": 1.0, "response_body_size": 10}
    )
    d = entry.to_dict()
    assert d["timestamp"] == 1.0
    assert d["response_body_size"] == 10
    assert "request_cookies" not in d  # unset enhanced fields are dropped


def test_traffic_entry_requires_url():
    with pytest.raises(ValueError, match="url"):
        TrafficEntry.from_dict({"method": "GET"})


def test_traffic_entry_ignores_unknown_fields():
    entry = TrafficEntry.from_dict({"url": "https://x.test", "status": "404", "bogus": True})
    assert entry.status == 404
    assert entry.is_error


def test_load_entries():
    entries = load_entries(
        [{"url": "https://a.test"}, {"url": "https://b.test", "method": "DELETE"}]
    )
    assert [e.is_write for e in entries] == [False, True]


def test_pipeline_state_roundtrip(tmp_path):
    state = PipelineState(app_dir="/tmp/demo", created_at="2026-01-01T00:00:00Z")
    state.phases[Phase.CAPTURE].status = PhaseStatus.DONE
    state.phases[Phase.CAPTURE].completed_at = "2026-01-01T01:00:00Z"
    path = tmp_path / "phase-state.json"
    state.save(path)

    loaded = PipelineState.load(path)
    assert loaded.phases[Phase.CAPTURE].status is PhaseStatus.DONE
    assert loaded.phases[Phase.METHODOLOGY].status is PhaseStatus.PENDING
    assert loaded.next_phase() is Phase.METHODOLOGY


def test_pipeline_state_matches_phase_state_script_schema(tmp_path):
    """The model must read what scripts/phase-state.py writes."""
    raw = {
        "app_dir": "/work/demo",
        "created_at": "2026-01-01T00:00:00Z",
        "phases": {
            "capture": {
                "status": "done",
                "completed_at": "x",
                "output": "raw-traffic.json",
                "notes": None,
            },
            "methodology": {
                "status": "failed",
                "failed_at": "y",
                "error": "boom",
                "error_type": "transient",
            },
            "testing": {"status": "pending"},
            "standards": {"status": "pending"},
        },
    }
    path = tmp_path / "phase-state.json"
    path.write_text(__import__("json").dumps(raw))
    state = PipelineState.load(path)
    assert state.phases[Phase.METHODOLOGY].status is PhaseStatus.FAILED
    assert state.phases[Phase.METHODOLOGY].error_type == "transient"
    assert state.next_phase() is Phase.METHODOLOGY


def test_pipeline_state_all_done(tmp_path):
    state = PipelineState(app_dir="demo")
    for phase in Phase.ordered():
        state.phases[phase].status = PhaseStatus.DONE
    assert state.next_phase() is None
