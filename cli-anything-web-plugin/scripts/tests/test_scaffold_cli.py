"""Tests for scaffold-cli.py: placeholder rendering, validation, and scaffolding."""
from __future__ import annotations

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

@pytest.mark.parametrize(
    "protocol,http_client,auth_type",
    [
        ("rest", "httpx", "cookie"),
        ("graphql", "httpx", "cookie"),
        ("html-scraping", "curl_cffi", "none"),
        ("batchexecute", "httpx", "google-sso"),
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
