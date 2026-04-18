#!/usr/bin/env python3
"""Scaffold a cli-web-* CLI from templates.

Generates the full boilerplate directory structure for a new CLI-Anything-WEB
project, replacing placeholder variables and selecting the correct client
variant based on protocol/http_client.

Usage:
    python scaffold-cli.py <output-dir> \
      --app-name hackernews \
      --protocol rest \
      --http-client httpx \
      --auth-type cookie \
      --resources stories,users,search \
      --has-polling \
      --has-context \
      --has-partial-ids

Output:
    Creates <output-dir>/cli_web/<app>/ with full boilerplate structure,
    plus <output-dir>/setup.py.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# Ensure sibling modules resolve whether invoked as a script or via importlib.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from plugin_paths import get_plugin_root, get_scripts_dir, get_templates_dir  # noqa: E402

SCRIPT_DIR = get_scripts_dir()
PLUGIN_DIR = get_plugin_root()
TEMPLATES_DIR = get_templates_dir()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_pascal(name: str) -> str:
    """Convert app-name or app_name to PascalCase.

    Examples:
        hackernews -> HackerNews  (single word, just capitalize)
        gh-trending -> GhTrending
        notebooklm -> Notebooklm
    """
    parts = re.split(r"[-_]", name)
    return "".join(p.capitalize() for p in parts)


def to_upper_snake(name: str) -> str:
    """Convert app-name to UPPER_SNAKE.

    Examples:
        hackernews -> HACKERNEWS
        gh-trending -> GH_TRENDING
    """
    return name.replace("-", "_").upper()


def to_underscore(name: str) -> str:
    """Convert app-name to underscore form for Python identifiers.

    Examples:
        hackernews -> hackernews
        gh-trending -> gh_trending
    """
    return name.replace("-", "_")


# Matches ${Name}, ${name_thing}, ${APP_NAME}. Python f-strings use {name} (no $),
# so this only catches genuine template placeholders.
_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def render_string(content: str, variables: dict[str, str]) -> str:
    """Substitute ${name} placeholders in a string."""
    for key, value in variables.items():
        content = content.replace(f"${{{key}}}", value)
    return content


def find_unresolved_placeholders(content: str) -> list[str]:
    """Return list of any ${...} placeholders still present in rendered output."""
    return sorted(set(_PLACEHOLDER_RE.findall(content)))


def render_template(tpl_path: Path, variables: dict[str, str]) -> str:
    """Read a .tpl file, substitute ${name} placeholders, and validate.

    Raises ValueError if the rendered output still contains unresolved ${name}
    placeholders — this catches typos and newly-added template vars that weren't
    wired into the variables dict.
    """
    content = tpl_path.read_text(encoding="utf-8")
    rendered = render_string(content, variables)
    unresolved = find_unresolved_placeholders(rendered)
    if unresolved:
        raise ValueError(
            f"Template {tpl_path.name} has unresolved placeholders after render: "
            f"{', '.join('${' + p + '}' for p in unresolved)}. "
            f"Add them to the variables dict or fix the template."
        )
    return rendered


def write_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent dirs.

    Validates that no ${name} placeholders remain — protects against fragments
    built without render_template (e.g., build_client's injected methods).
    """
    unresolved = find_unresolved_placeholders(content)
    if unresolved:
        raise ValueError(
            f"Refusing to write {path}: unresolved placeholders "
            f"{', '.join('${' + p + '}' for p in unresolved)}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Created: {path}")


# ---------------------------------------------------------------------------
# Client variant selection
# ---------------------------------------------------------------------------

def build_client(variables: dict, protocol: str, http_client: str) -> str:
    """Render client.py from a base template + conditional method injection."""
    valid_protocols = ("rest", "graphql", "html-scraping", "batchexecute")
    if protocol not in valid_protocols:
        raise ValueError(f"Unknown protocol '{protocol}'. Must be one of: {', '.join(valid_protocols)}")

    if protocol == "batchexecute":
        return render_template(TEMPLATES_DIR / "client_batchexecute.py.tpl", variables)

    # REST-based protocols: select base by http_client, then inject extra methods
    base_tpl = "client_rest_curl.py.tpl" if http_client == "curl_cffi" else "client_rest_httpx.py.tpl"
    content = render_template(TEMPLATES_DIR / base_tpl, variables)

    # Inject protocol-specific helper methods before the close() method
    extra_methods = ""
    if protocol == "html-scraping":
        extra_methods = '''
    def _parse_html(self, html: str):
        """Parse HTML response with BeautifulSoup."""
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    def _get_html(self, path: str, **kwargs):
        """GET a page and return parsed HTML."""
        resp = self._request("GET", path, **kwargs)
        return self._parse_html(resp.text)

'''
    elif protocol == "graphql":
        extra_methods = '''
    def _graphql(self, query: str, variables: dict | None = None, **kwargs):
        """Execute a GraphQL query/mutation."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = self._request("POST", "/graphql", json=payload, **kwargs)
        data = resp.json()
        if "errors" in data:
            raise ${AppName}Error(data["errors"][0].get("message", "GraphQL error"))
        return data.get("data", data)

'''

    if extra_methods:
        # Route injected methods through the same substitution pipeline so any
        # ${placeholder} resolves consistently and write_file's validator runs.
        extra_methods = render_string(extra_methods, variables)
        anchor = "    def close(self):"
        if anchor not in content:
            raise ValueError(
                f"Base client template {base_tpl!r} is missing required anchor "
                f"{anchor!r} — protocol={protocol} injection would be silently "
                f"dropped. If you renamed close(), update build_client()."
            )
        content = content.replace(anchor, extra_methods + anchor)

    return content


# ---------------------------------------------------------------------------
# Helpers.py conditional sections
# ---------------------------------------------------------------------------

# Each feature flag maps to a fragment template under templates/. Fragments
# are rendered via the normal template pipeline (validated for unresolved
# placeholders, no f-string quote hazards). Add a new flag by creating a
# `helpers_<flag>.py.tpl` file and registering it here.
_HELPER_FRAGMENTS = [
    ("has_partial_ids", "helpers_partial_ids.py.tpl"),
    ("has_polling", "helpers_polling.py.tpl"),
    ("has_context", "helpers_context.py.tpl"),
]


def build_helpers(variables: dict, has_polling: bool, has_context: bool, has_partial_ids: bool) -> str:
    """Render helpers.py by composing the base template with feature fragments."""
    flags = {
        "has_partial_ids": has_partial_ids,
        "has_polling": has_polling,
        "has_context": has_context,
    }
    content = render_template(TEMPLATES_DIR / "helpers.py.tpl", variables)
    for flag_name, fragment_name in _HELPER_FRAGMENTS:
        if flags[flag_name]:
            content += render_template(TEMPLATES_DIR / fragment_name, variables)
    return content


# ---------------------------------------------------------------------------
# Setup.py generation
# ---------------------------------------------------------------------------

def build_setup_py(variables: dict, http_client: str, auth_type: str, protocol: str) -> str:
    """Render setup.py with correct dependencies."""
    # Build install_requires line
    deps = []
    if http_client == "curl_cffi":
        deps.append('"curl_cffi",')
    else:
        deps.append('"httpx",')

    if protocol in ("html-scraping",):
        deps.append('"beautifulsoup4>=4.12",')

    install_requires = "\n        ".join(deps)

    # Build extras_require as a complete block so we emit nothing when empty
    # (setup.py treats an empty `extras_require={}` as clutter).
    extras = []
    if auth_type in ("cookie", "google-sso"):
        extras.append('"browser": ["playwright>=1.40.0"],')

    if extras:
        extras_body = "\n        ".join(extras)
        extras_require_block = f"extras_require={{\n        {extras_body}\n    }},"
    else:
        extras_require_block = ""

    variables = {
        **variables,
        "install_requires": install_requires,
        "extras_require_block": extras_require_block,
    }
    return render_template(TEMPLATES_DIR / "setup.py.tpl", variables)


# ---------------------------------------------------------------------------
# Main scaffold
# ---------------------------------------------------------------------------

def scaffold(
    output_dir: Path,
    app_name: str,
    protocol: str,
    http_client: str,
    auth_type: str,
    resources: list[str],
    has_polling: bool,
    has_context: bool,
    has_partial_ids: bool,
) -> None:
    """Generate the full boilerplate structure."""
    app_underscore = to_underscore(app_name)
    variables = {
        "app_name": app_name,
        "app_name_underscore": app_underscore,
        "APP_NAME": to_upper_snake(app_name),
        "AppName": to_pascal(app_name),
    }

    # Base paths
    pkg_dir = output_dir / "cli_web" / app_underscore
    core_dir = pkg_dir / "core"
    utils_dir = pkg_dir / "utils"
    commands_dir = pkg_dir / "commands"
    tests_dir = pkg_dir / "tests"

    print(f"\nScaffolding cli-web-{app_name} into {output_dir}/")
    print(f"  Protocol: {protocol}, HTTP client: {http_client}")
    print(f"  Auth: {auth_type}, Resources: {resources}")
    print(f"  Polling: {has_polling}, Context: {has_context}, Partial IDs: {has_partial_ids}")
    print()

    # ── 1. Namespace package (NO __init__.py) ──────────────────────────────
    (output_dir / "cli_web").mkdir(parents=True, exist_ok=True)

    # ── 2. Sub-package __init__.py ─────────────────────────────────────────
    write_file(
        pkg_dir / "__init__.py",
        f'"""cli-web-{app_name}: CLI for {variables["AppName"]}."""\n\n__version__ = "0.1.0"\n',
    )

    # ── 3. __main__.py ─────────────────────────────────────────────────────
    write_file(
        pkg_dir / "__main__.py",
        f'"""Allow running as: python -m cli_web.{app_underscore}"""\n'
        f"from .{app_underscore}_cli import cli\n\n"
        f'if __name__ == "__main__":\n    cli()\n',
    )

    # ── 4. core/ ───────────────────────────────────────────────────────────
    write_file(core_dir / "__init__.py", "")

    # exceptions.py
    write_file(
        core_dir / "exceptions.py",
        render_template(TEMPLATES_DIR / "exceptions.py.tpl", variables),
    )

    # client.py (variant based on protocol + http_client)
    write_file(
        core_dir / "client.py",
        build_client(variables, protocol, http_client),
    )

    # auth.py (conditional + variant by auth_type)
    # google-sso needs the regional-cookie-priority + login_browser scaffold;
    # cookie and api-key use the generic thin template.
    if auth_type != "none":
        auth_tpl_name = "auth_google_sso.py.tpl" if auth_type == "google-sso" else "auth.py.tpl"
        write_file(
            core_dir / "auth.py",
            render_template(TEMPLATES_DIR / auth_tpl_name, variables),
        )

    # rpc/ subpackage (batchexecute only)
    if protocol == "batchexecute":
        rpc_dir = core_dir / "rpc"
        write_file(
            rpc_dir / "__init__.py",
            '"""RPC encoding/decoding for Google batchexecute protocol."""\n',
        )
        write_file(
            rpc_dir / "types.py",
            render_template(TEMPLATES_DIR / "rpc_types.py.tpl", variables),
        )
        write_file(
            rpc_dir / "encoder.py",
            render_template(TEMPLATES_DIR / "rpc_encoder.py.tpl", variables),
        )
        write_file(
            rpc_dir / "decoder.py",
            render_template(TEMPLATES_DIR / "rpc_decoder.py.tpl", variables),
        )

    # ── 5. utils/ ──────────────────────────────────────────────────────────
    write_file(utils_dir / "__init__.py", "")

    # helpers.py (with conditional sections)
    write_file(
        utils_dir / "helpers.py",
        build_helpers(variables, has_polling, has_context, has_partial_ids),
    )

    # output.py
    write_file(
        utils_dir / "output.py",
        render_template(TEMPLATES_DIR / "output.py.tpl", variables),
    )

    # repl_skin.py (copy from scripts/)
    repl_skin_src = SCRIPT_DIR / "repl_skin.py"
    if repl_skin_src.exists():
        repl_skin_dst = utils_dir / "repl_skin.py"
        repl_skin_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repl_skin_src, repl_skin_dst)
        print(f"  Copied:  {repl_skin_dst}")
    else:
        print(f"  WARNING: repl_skin.py not found at {repl_skin_src}")

    # ── 6. commands/ ───────────────────────────────────────────────────────
    write_file(commands_dir / "__init__.py", "")

    # ── 7. tests/ ──────────────────────────────────────────────────────────
    write_file(tests_dir / "__init__.py", "")
    write_file(
        tests_dir / "conftest.py",
        render_template(TEMPLATES_DIR / "conftest.py.tpl", variables),
    )

    # ── 8. CLI entry point ─────────────────────────────────────────────────
    write_file(
        pkg_dir / f"{app_underscore}_cli.py",
        render_template(TEMPLATES_DIR / "cli_entry.py.tpl", variables),
    )

    # ── 9. setup.py ────────────────────────────────────────────────────────
    write_file(
        output_dir / "setup.py",
        build_setup_py(variables, http_client, auth_type, protocol),
    )

    # ── Summary ────────────────────────────────────────────────────────────
    total = sum(1 for _ in output_dir.rglob("*.py"))
    print(f"\nDone! Generated {total} Python files.")
    print(f"\nNext steps:")
    print(f"  1. Fill in FILL_IN_BASE_URL in core/client.py")
    print(f"  2. Add endpoint methods to core/client.py")
    print(f"  3. Create command modules in commands/")
    print(f"  4. Register commands in {app_underscore}_cli.py")
    print(f"  5. Fill in REPL help text")
    if auth_type != "none":
        print(f"  6. Implement login flow in core/auth.py")
    if protocol == "batchexecute":
        print(f"  7. Add RPC method IDs to core/rpc/types.py")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a cli-web-* CLI from templates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # REST API with httpx, cookie auth
  python scaffold-cli.py hackernews/agent-harness \\
    --app-name hackernews --protocol rest --http-client httpx --auth-type cookie \\
    --resources stories,users,search

  # HTML scraping with curl_cffi, no auth
  python scaffold-cli.py gh-trending/agent-harness \\
    --app-name gh-trending --protocol html-scraping --http-client curl_cffi \\
    --auth-type none --resources repos,developers

  # Google batchexecute RPC with SSO
  python scaffold-cli.py notebooklm/agent-harness \\
    --app-name notebooklm --protocol batchexecute --http-client httpx \\
    --auth-type google-sso --resources notebooks,sources,chat \\
    --has-context --has-polling
        """,
    )
    parser.add_argument("output_dir", type=Path, help="Output directory (e.g., <app>/agent-harness)")
    parser.add_argument("--app-name", required=True, help="CLI app name (e.g., hackernews, gh-trending)")
    parser.add_argument(
        "--protocol",
        required=True,
        choices=["rest", "graphql", "html-scraping", "batchexecute"],
        help="API protocol type",
    )
    parser.add_argument(
        "--http-client",
        required=True,
        choices=["httpx", "curl_cffi"],
        help="HTTP client library",
    )
    parser.add_argument(
        "--auth-type",
        required=True,
        choices=["none", "cookie", "api-key", "google-sso"],
        help="Authentication type",
    )
    parser.add_argument(
        "--resources",
        required=True,
        help="Comma-separated resource names (e.g., stories,users,search)",
    )
    parser.add_argument("--has-polling", action="store_true", help="Include polling/backoff helpers")
    parser.add_argument("--has-context", action="store_true", help="Include persistent context helpers")
    parser.add_argument("--has-partial-ids", action="store_true", help="Include partial ID resolution")

    args = parser.parse_args()

    # --app-name must convert to a valid Python identifier — generated code
    # uses it for package names, module imports, and env var suffixes.
    app_underscore = to_underscore(args.app_name)
    if not app_underscore.isidentifier() or app_underscore.startswith("_"):
        parser.error(
            f"--app-name {args.app_name!r} converts to {app_underscore!r}, which "
            f"is not a valid Python package name. Use only letters, digits, "
            f"underscores, or hyphens; must start with a letter."
        )
    if not args.app_name[0].isalpha():
        parser.error(
            f"--app-name {args.app_name!r} must start with a letter "
            f"(generated Python packages cannot start with a digit)."
        )

    resources = [r.strip() for r in args.resources.split(",") if r.strip()]
    if not resources:
        parser.error("--resources must not be empty; pass at least one resource name.")

    scaffold(
        output_dir=args.output_dir.resolve(),
        app_name=args.app_name,
        protocol=args.protocol,
        http_client=args.http_client,
        auth_type=args.auth_type,
        resources=resources,
        has_polling=args.has_polling,
        has_context=args.has_context,
        has_partial_ids=args.has_partial_ids,
    )


if __name__ == "__main__":
    main()
