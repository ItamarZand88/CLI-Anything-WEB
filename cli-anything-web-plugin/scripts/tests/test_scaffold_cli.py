"""Tests for scaffold-cli.py: placeholder rendering, validation, and scaffolding."""
from __future__ import annotations

import py_compile
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SCAFFOLD = SCRIPTS_DIR / "scaffold-cli.py"


# --- Helpers (string conversion) ---

def test_to_pascal_single_word(scaffold_cli):
    assert scaffold_cli.to_pascal("hackernews") == "Hackernews"


def test_to_pascal_hyphenated(scaffold_cli):
    assert scaffold_cli.to_pascal("gh-trending") == "GhTrending"


def test_to_pascal_underscore(scaffold_cli):
    assert scaffold_cli.to_pascal("my_app_name") == "MyAppName"


def test_to_upper_snake(scaffold_cli):
    assert scaffold_cli.to_upper_snake("gh-trending") == "GH_TRENDING"
    assert scaffold_cli.to_upper_snake("hackernews") == "HACKERNEWS"


def test_to_underscore(scaffold_cli):
    assert scaffold_cli.to_underscore("gh-trending") == "gh_trending"
    assert scaffold_cli.to_underscore("hackernews") == "hackernews"


# --- Placeholder rendering ---

def test_render_string_substitutes_known_keys(scaffold_cli):
    out = scaffold_cli.render_string("Hello ${Name}!", {"Name": "World"})
    assert out == "Hello World!"


def test_render_string_multiple_placeholders(scaffold_cli):
    out = scaffold_cli.render_string(
        "cli-web-${app_name} / ${AppName}Error",
        {"app_name": "foo", "AppName": "Foo"},
    )
    assert out == "cli-web-foo / FooError"


def test_render_string_preserves_unknown_placeholders(scaffold_cli):
    out = scaffold_cli.render_string("Known=${A}, unknown=${B}", {"A": "yes"})
    assert out == "Known=yes, unknown=${B}"


# --- Placeholder detection ---

def test_find_unresolved_detects_placeholders(scaffold_cli):
    found = scaffold_cli.find_unresolved_placeholders("foo ${Bar} baz ${Quux}")
    assert found == ["Bar", "Quux"]


def test_find_unresolved_deduplicates(scaffold_cli):
    found = scaffold_cli.find_unresolved_placeholders("${A} ${A} ${A}")
    assert found == ["A"]


def test_find_unresolved_empty_when_clean(scaffold_cli):
    assert scaffold_cli.find_unresolved_placeholders("no placeholders") == []


def test_find_unresolved_ignores_f_string_style(scaffold_cli):
    # Python f-strings use {name}, not ${name}. Must not trigger.
    assert scaffold_cli.find_unresolved_placeholders("f'{variable}'") == []


# --- write_file / render_template validation ---

def test_write_file_refuses_unresolved_content(scaffold_cli, tmp_path):
    with pytest.raises(ValueError, match="unresolved placeholders"):
        scaffold_cli.write_file(tmp_path / "out.py", "bad ${StillHere}")
    assert not (tmp_path / "out.py").exists()


def test_write_file_accepts_clean_content(scaffold_cli, tmp_path):
    scaffold_cli.write_file(tmp_path / "ok.py", "no placeholders here\n")
    assert (tmp_path / "ok.py").read_text() == "no placeholders here\n"


def test_render_template_raises_when_variable_missing(scaffold_cli, tmp_path):
    tpl = tmp_path / "fake.tpl"
    tpl.write_text("Hello ${Missing}")
    with pytest.raises(ValueError, match="unresolved placeholders"):
        scaffold_cli.render_template(tpl, {})


def test_render_template_succeeds_with_all_variables(scaffold_cli, tmp_path):
    tpl = tmp_path / "fake.tpl"
    tpl.write_text('name="${Name}", ver="${Ver}"')
    out = scaffold_cli.render_template(tpl, {"Name": "foo", "Ver": "1.0"})
    assert out == 'name="foo", ver="1.0"'


# --- End-to-end scaffold (subprocess invocation) ---

def test_batchexecute_client_retries_on_auth_error(tmp_path):
    """Regression: client_batchexecute.py.tpl must wire _refresh_tokens() into
    _rpc() on 401/403 (previously a stub method that was never called)."""
    out_dir = tmp_path / "gen"
    result = subprocess.run(
        [
            sys.executable, str(SCAFFOLD), str(out_dir),
            "--app-name", "beapp",
            "--protocol", "batchexecute",
            "--http-client", "httpx",
            "--auth-type", "google-sso",
            "--resources", "notebooks",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    client_src = (out_dir / "cli_web" / "beapp" / "core" / "client.py").read_text()

    # Signature must expose retry_on_auth (new production-parity API uses rpc_id: str)
    assert "retry_on_auth: bool = True" in client_src
    # Retry branch must call _refresh_tokens on 401/403 and recurse with retry_on_auth=False
    assert "resp.status_code in (401, 403) and retry_on_auth" in client_src
    assert "self._refresh_tokens()" in client_src
    assert "retry_on_auth=False" in client_src
    # Must import the production-parity encoder/decoder
    assert "from .rpc.encoder import build_url, encode_request" in client_src
    assert "from .rpc.decoder import decode_response" in client_src


@pytest.mark.parametrize(
    "protocol,http_client,auth_type",
    [
        # Core protocol × client combos
        ("rest", "httpx", "cookie"),
        ("rest", "curl_cffi", "cookie"),
        ("rest", "httpx", "api-key"),
        ("rest", "httpx", "none"),
        ("graphql", "httpx", "cookie"),
        ("graphql", "curl_cffi", "cookie"),
        ("html-scraping", "curl_cffi", "none"),
        ("html-scraping", "httpx", "none"),
        # batchexecute typically pairs with google-sso but also works with cookie auth
        ("batchexecute", "httpx", "google-sso"),
        ("batchexecute", "httpx", "cookie"),
        # google-sso with REST/html-scraping (for non-batchexecute Google apps)
        ("rest", "httpx", "google-sso"),
    ],
)
def test_scaffold_end_to_end_no_unresolved_placeholders(
    tmp_path, protocol, http_client, auth_type
):
    """Run the full scaffold pipeline; no generated file may contain ${...}."""
    out_dir = tmp_path / "gen"
    result = subprocess.run(
        [
            sys.executable, str(SCAFFOLD), str(out_dir),
            "--app-name", "testcli",
            "--protocol", protocol,
            "--http-client", http_client,
            "--auth-type", auth_type,
            "--resources", "items",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"scaffold failed: {result.stderr}"

    offenders = []
    for path in out_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "${" in text and any(
            c.isalpha() or c == "_"
            for c in text[text.index("${") + 2: text.index("${") + 3]
        ):
            # Stricter: re-run the detector to confirm
            import re
            matches = re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", text)
            if matches:
                offenders.append((path.name, matches))

    assert not offenders, f"Unresolved placeholders: {offenders}"

    # Sanity: setup.py must exist for every variant
    assert (out_dir / "setup.py").exists()

    # Every generated .py file must be syntactically valid. Catches indentation
    # hazards and quote/escape bugs in the f-string code-gen paths that the
    # placeholder-only check misses.
    syntax_errors = []
    for py in out_dir.rglob("*.py"):
        try:
            py_compile.compile(str(py), doraise=True)
        except py_compile.PyCompileError as exc:
            syntax_errors.append(f"{py}: {exc}")
    assert not syntax_errors, "Generated Python has syntax errors:\n" + "\n".join(syntax_errors)


@pytest.mark.parametrize(
    "has_polling,has_context,has_partial_ids",
    [
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, True),
    ],
)
def test_scaffold_feature_flags_produce_valid_python(
    tmp_path, has_polling, has_context, has_partial_ids
):
    """Each feature flag combination must emit syntactically valid helpers.py."""
    out_dir = tmp_path / "gen"
    flags = []
    if has_polling:
        flags.append("--has-polling")
    if has_context:
        flags.append("--has-context")
    if has_partial_ids:
        flags.append("--has-partial-ids")
    result = subprocess.run(
        [
            sys.executable, str(SCAFFOLD), str(out_dir),
            "--app-name", "flagtest",
            "--protocol", "rest",
            "--http-client", "httpx",
            "--auth-type", "cookie",
            "--resources", "items",
            *flags,
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"scaffold failed: {result.stderr}"

    helpers = (out_dir / "cli_web" / "flagtest" / "utils" / "helpers.py").read_text()
    py_compile.compile(
        str(out_dir / "cli_web" / "flagtest" / "utils" / "helpers.py"),
        doraise=True,
    )

    assert ("def poll_until_complete" in helpers) is has_polling
    assert ("def get_context_value" in helpers) is has_context
    assert ("def resolve_partial_id" in helpers) is has_partial_ids


def test_app_name_validation_rejects_numeric_start(tmp_path):
    result = subprocess.run(
        [
            sys.executable, str(SCAFFOLD), str(tmp_path / "out"),
            "--app-name", "123bad",
            "--protocol", "rest",
            "--http-client", "httpx",
            "--auth-type", "none",
            "--resources", "x",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "must start with a letter" in result.stderr or "not a valid Python" in result.stderr


def test_app_name_validation_rejects_dots(tmp_path):
    result = subprocess.run(
        [
            sys.executable, str(SCAFFOLD), str(tmp_path / "out"),
            "--app-name", "my.app",
            "--protocol", "rest",
            "--http-client", "httpx",
            "--auth-type", "none",
            "--resources", "x",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "not a valid Python" in result.stderr


def test_resources_must_not_be_empty(tmp_path):
    result = subprocess.run(
        [
            sys.executable, str(SCAFFOLD), str(tmp_path / "out"),
            "--app-name", "goodapp",
            "--protocol", "rest",
            "--http-client", "httpx",
            "--auth-type", "none",
            "--resources", "",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "resources" in result.stderr.lower()


def test_google_sso_auth_has_regional_cookie_priority(tmp_path):
    """google-sso variant must include the CLAUDE.md-mandated domain priority."""
    out_dir = tmp_path / "gen"
    result = subprocess.run(
        [
            sys.executable, str(SCAFFOLD), str(out_dir),
            "--app-name", "gsso",
            "--protocol", "batchexecute",
            "--http-client", "httpx",
            "--auth-type", "google-sso",
            "--resources", "items",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    auth_src = (out_dir / "cli_web" / "gsso" / "core" / "auth.py").read_text()
    # Regional cctld set + priority logic must both be present
    assert "GOOGLE_REGIONAL_CCTLDS" in auth_src
    assert "google.co.il" in auth_src  # spot-check one regional
    assert 'domain == ".google.com"' in auth_src  # priority rule
    assert "_windows_playwright_event_loop" in auth_src
    assert "login_browser" in auth_src


def test_cookie_auth_uses_thin_template(tmp_path):
    """Non-google-sso auth_type should still use the thin auth.py.tpl."""
    out_dir = tmp_path / "gen"
    result = subprocess.run(
        [
            sys.executable, str(SCAFFOLD), str(out_dir),
            "--app-name", "thin",
            "--protocol", "rest",
            "--http-client", "httpx",
            "--auth-type", "cookie",
            "--resources", "items",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    auth_src = (out_dir / "cli_web" / "thin" / "core" / "auth.py").read_text()
    assert "GOOGLE_REGIONAL_CCTLDS" not in auth_src  # NOT the google-sso variant
    assert "def save_auth" in auth_src
    assert "def load_auth" in auth_src


def test_no_config_py_generated(tmp_path):
    """core/config.py was removed — no CLI should receive one anymore."""
    out_dir = tmp_path / "gen"
    subprocess.check_call([
        sys.executable, str(SCAFFOLD), str(out_dir),
        "--app-name", "noconfig",
        "--protocol", "rest",
        "--http-client", "httpx",
        "--auth-type", "cookie",
        "--resources", "items",
    ])
    assert not (out_dir / "cli_web" / "noconfig" / "core" / "config.py").exists()
