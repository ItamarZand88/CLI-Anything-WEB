import sys

import pytest
from cli_web_core.testing import (
    assert_json_envelope,
    assert_no_protocol_leaks,
    parse_json_output,
    resolve_cli,
    run_cli,
)


def test_resolve_cli_falls_back_to_module(monkeypatch):
    monkeypatch.delenv("CLI_WEB_FORCE_INSTALLED", raising=False)
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert resolve_cli("cli-web-gh-trending") == [sys.executable, "-m", "cli_web.gh_trending"]


def test_resolve_cli_forced_raises(monkeypatch):
    monkeypatch.setenv("CLI_WEB_FORCE_INSTALLED", "1")
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="not found on PATH"):
        resolve_cli("cli-web-nonexistent")


def test_resolve_cli_prefers_binary(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/cli-web-demo")
    assert resolve_cli("cli-web-demo") == ["/usr/bin/cli-web-demo"]


def test_run_cli_executes():
    proc = run_cli([sys.executable], "-c", "print('hello')")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "hello"


def test_parse_json_output_plain():
    assert parse_json_output('{"a": 1}') == {"a": 1}


def test_parse_json_output_with_spinner_noise():
    noisy = 'Fetching...\ndone\n{\n  "a": 1\n}'
    assert parse_json_output(noisy) == {"a": 1}


def test_parse_json_output_rejects_garbage():
    with pytest.raises(ValueError, match="No JSON"):
        parse_json_output("nothing here")


def test_assert_json_envelope_success():
    assert_json_envelope('{"success": true, "data": []}')


def test_assert_json_envelope_error():
    assert_json_envelope('{"error": true, "code": "NOT_FOUND", "message": "x"}')


def test_assert_json_envelope_rejects_malformed():
    with pytest.raises(AssertionError):
        assert_json_envelope('{"error": true}')
    with pytest.raises(AssertionError):
        assert_json_envelope('{"data": []}')


def test_protocol_leak_detection():
    assert_no_protocol_leaks("clean output")
    with pytest.raises(AssertionError, match="wrb.fr"):
        assert_no_protocol_leaks('[["wrb.fr", ...]]')
