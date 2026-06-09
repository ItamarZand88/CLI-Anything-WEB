"""Profile-matrix ("golden") tests for scaffold-cli.py Generation v2.

Scaffolds a synthetic CLI for every supported profile combination
(protocol x http_client x auth_type) and asserts structural invariants:

- every generated .py file compiles
- no literal "${" placeholder or "{%" Jinja block tag survives in any output
- exceptions.py defines the full typed hierarchy
- setup.py declares the correct dependencies for the profile
- .manifest.json is valid, devkit-shaped, and stamped with TEMPLATE_VERSION
"""

from __future__ import annotations

import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SCAFFOLD = SCRIPTS_DIR / "scaffold-cli.py"

PLACEHOLDER_RE = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}")

PROTOCOLS = ["rest", "graphql", "html-scraping", "batchexecute"]
AUTH_TYPES = ["none", "cookie", "google-sso"]


def _http_clients_for(protocol: str) -> list[str]:
    # batchexecute is httpx-only (Google RPC template hardcodes httpx).
    if protocol == "batchexecute":
        return ["httpx"]
    return ["httpx", "curl_cffi"]


PROFILES = [
    (protocol, http_client, auth_type)
    for protocol in PROTOCOLS
    for http_client in _http_clients_for(protocol)
    for auth_type in AUTH_TYPES
]


def _scaffold(out_dir: Path, protocol: str, http_client: str, auth_type: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCAFFOLD),
            str(out_dir),
            "--app-name",
            "golden",
            "--protocol",
            protocol,
            "--http-client",
            http_client,
            "--auth-type",
            auth_type,
            "--resources",
            "items",
            "--resource",
            "items",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"scaffold failed: {result.stderr}"


@pytest.fixture(scope="module")
def scaffolded(tmp_path_factory):
    """Scaffold every profile once; tests below assert against the outputs."""
    outputs: dict[tuple[str, str, str], Path] = {}
    base = tmp_path_factory.mktemp("golden")
    for protocol, http_client, auth_type in PROFILES:
        out_dir = base / f"{protocol}-{http_client}-{auth_type}"
        _scaffold(out_dir, protocol, http_client, auth_type)
        outputs[(protocol, http_client, auth_type)] = out_dir
    return outputs


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_all_python_files_compile(scaffolded, profile):
    out_dir = scaffolded[profile]
    errors = []
    for py in out_dir.rglob("*.py"):
        try:
            py_compile.compile(str(py), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{py}: {exc}")
    assert not errors, "Generated Python has syntax errors:\n" + "\n".join(errors)


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_no_template_syntax_leaks(scaffolded, profile):
    """No literal ${name} placeholder or {% block tag in ANY generated file."""
    out_dir = scaffolded[profile]
    offenders = []
    for path in out_dir.rglob("*"):
        # Skip bytecode caches left behind by the compile test.
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if PLACEHOLDER_RE.search(text):
            offenders.append(f"{path}: unresolved ${{...}} placeholder")
        if "{%" in text:
            offenders.append(f"{path}: raw Jinja block tag")
    assert not offenders, "\n".join(offenders)


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_exceptions_define_expected_classes(scaffolded, profile):
    out_dir = scaffolded[profile]
    src = (out_dir / "cli_web" / "golden" / "core" / "exceptions.py").read_text()
    for cls in (
        "class GoldenError",
        "class AuthError",
        "class RateLimitError",
        "class NetworkError",
        "class ServerError",
        "class NotFoundError",
        "class RPCError",
    ):
        assert cls in src, f"exceptions.py missing {cls!r}"
    assert "def raise_for_status" in src
    assert "def to_dict" in src


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_setup_py_declares_profile_dependencies(scaffolded, profile):
    protocol, http_client, auth_type = profile
    setup_src = (scaffolded[profile] / "setup.py").read_text()

    assert ("curl_cffi" in setup_src) is (http_client == "curl_cffi")
    assert ('"httpx"' in setup_src) is (http_client == "httpx")
    assert ("beautifulsoup4" in setup_src) is (protocol == "html-scraping")
    assert ("playwright" in setup_src) is (auth_type in ("cookie", "google-sso"))
    # Always-on deps
    assert '"click>=8.0"' in setup_src
    assert '"rich>=13.0"' in setup_src
    assert "cli-web-golden=cli_web.golden.golden_cli:main" in setup_src


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_manifest_is_valid_and_versioned(scaffolded, profile):
    protocol, http_client, auth_type = profile
    manifest_path = scaffolded[profile] / ".manifest.json"
    assert manifest_path.exists(), ".manifest.json not generated"
    manifest = json.loads(manifest_path.read_text())

    assert manifest["manifest_version"] == 1
    assert manifest["cli"] == "cli-web-golden"
    generator = manifest["generator"]
    assert generator["template_version"] == "2.0.0"
    assert generator["plugin_version"]
    assert generator["generated_at"]
    assert manifest["profile"] == {
        "protocol": protocol,
        "http_client": http_client,
        "auth_type": auth_type,
    }
    assert manifest["shared_files"] == {}
    assert manifest["overrides"] == []


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_expected_file_set(scaffolded, profile):
    protocol, _http_client, auth_type = profile
    out_dir = scaffolded[profile]
    pkg = out_dir / "cli_web" / "golden"

    expected = [
        pkg / "__init__.py",
        pkg / "__main__.py",
        pkg / "golden_cli.py",
        pkg / "core" / "exceptions.py",
        pkg / "core" / "client.py",
        pkg / "utils" / "helpers.py",
        pkg / "utils" / "output.py",
        pkg / "utils" / "repl_skin.py",
        pkg / "commands" / "items.py",
        pkg / "tests" / "conftest.py",
        pkg / "tests" / "test_e2e.py",
        out_dir / "setup.py",
        out_dir / "README.md",
        out_dir / "skill" / "SKILL.md",
        out_dir / ".manifest.json",
    ]
    for path in expected:
        assert path.exists(), f"missing generated file: {path.relative_to(out_dir)}"

    # auth.py only for authenticated profiles
    assert (pkg / "core" / "auth.py").exists() is (auth_type != "none")
    # rpc/ subpackage only for batchexecute
    assert (pkg / "core" / "rpc" / "decoder.py").exists() is (protocol == "batchexecute")


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_client_protocol_methods(scaffolded, profile):
    protocol, _http_client, _auth_type = profile
    client_src = (scaffolded[profile] / "cli_web" / "golden" / "core" / "client.py").read_text()

    if protocol == "batchexecute":
        assert "def _rpc(" in client_src
        return
    assert ("def _graphql(" in client_src) is (protocol == "graphql")
    assert ("def _parse_html(" in client_src) is (protocol == "html-scraping")
    assert ("def _get_html(" in client_src) is (protocol == "html-scraping")


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_auth_variant_matches_auth_type(scaffolded, profile):
    _protocol, _http_client, auth_type = profile
    if auth_type == "none":
        return
    auth_src = (scaffolded[profile] / "cli_web" / "golden" / "core" / "auth.py").read_text()
    if auth_type == "google-sso":
        assert "GOOGLE_REGIONAL_CCTLDS" in auth_src
        assert 'domain == ".google.com"' in auth_src
        assert "def login_browser" in auth_src
        assert "def load_cookies" in auth_src
    else:
        assert "GOOGLE_REGIONAL_CCTLDS" not in auth_src
        assert "def save_auth" in auth_src
        assert "def load_auth" in auth_src
        assert "def refresh_auth" in auth_src


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_command_module_scaffold(scaffolded, profile):
    src = (scaffolded[profile] / "cli_web" / "golden" / "commands" / "items.py").read_text()
    assert "import click" in src
    assert "def items()" in src
    assert "handle_errors" in src
    assert "# FILL_IN:" in src
    assert "json_mode" in src


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_e2e_skeleton_has_canonical_fixtures(scaffolded, profile):
    src = (scaffolded[profile] / "cli_web" / "golden" / "tests" / "test_e2e.py").read_text()
    assert "def _resolve_cli(" in src
    assert "def _run(" in src
    assert "def _parse_json(" in src
    assert 'CLI_WEB_FORCE_INSTALLED" ' in src or 'CLI_WEB_FORCE_INSTALLED")' in src
    assert "test_help_loads" in src
    assert "test_version_works" in src
    assert "test_repl_exits_cleanly" in src
    assert "# FILL_IN:" in src


@pytest.mark.parametrize("profile", PROFILES, ids=lambda p: "-".join(p))
def test_docs_skeletons(scaffolded, profile):
    _protocol, _http_client, auth_type = profile
    out_dir = scaffolded[profile]
    readme = (out_dir / "README.md").read_text()
    skill = (out_dir / "skill" / "SKILL.md").read_text()

    assert "# cli-web-golden" in readme
    assert ("auth login" in readme) is (auth_type != "none")
    assert "name: golden-cli" in skill
    assert "FILL_IN" in readme
    assert "FILL_IN" in skill
