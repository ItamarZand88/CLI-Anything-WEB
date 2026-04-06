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
from string import Template

# Resolve template dir relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = PLUGIN_DIR / "templates"


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


def render_template(tpl_path: Path, variables: dict) -> str:
    """Read a .tpl file and substitute $-variables."""
    content = tpl_path.read_text(encoding="utf-8")
    # Use Template for safe substitution (ignores unknown $vars in code)
    # We need to be careful: Python code has $ in f-strings etc.
    # Use a custom approach: only replace our known placeholders
    for key, value in variables.items():
        content = content.replace(f"${{{key}}}", value)
    return content


def write_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Created: {path}")


# ---------------------------------------------------------------------------
# Client variant selection
# ---------------------------------------------------------------------------

def select_client_template(protocol: str, http_client: str) -> str:
    """Return the template filename for the client variant."""
    if protocol == "batchexecute":
        return "client_batchexecute.py.tpl"
    elif protocol == "graphql":
        if http_client == "curl_cffi":
            return "client_graphql_curl.py.tpl"
        return "client_graphql_httpx.py.tpl"
    elif protocol == "html-scraping":
        if http_client == "curl_cffi":
            return "client_html_curl.py.tpl"
        return "client_html_httpx.py.tpl"
    else:  # rest (default)
        if http_client == "curl_cffi":
            return "client_rest_curl.py.tpl"
        return "client_rest_httpx.py.tpl"


# ---------------------------------------------------------------------------
# Config template selection
# ---------------------------------------------------------------------------

def select_config_template(auth_type: str, has_context: bool) -> str:
    """Return the template filename for config.py."""
    has_auth = auth_type != "none"
    if has_auth and has_context:
        return "config_auth_context.py.tpl"
    elif has_auth:
        return "config_auth.py.tpl"
    elif has_context:
        return "config_context.py.tpl"
    else:
        return "config.py.tpl"


# ---------------------------------------------------------------------------
# Helpers.py conditional sections
# ---------------------------------------------------------------------------

def build_helpers(variables: dict, has_polling: bool, has_context: bool, has_partial_ids: bool) -> str:
    """Render helpers.py with conditional sections included/excluded."""
    content = render_template(TEMPLATES_DIR / "helpers.py.tpl", variables)

    # Add conditional sections
    sections = []

    if has_partial_ids:
        sections.append(f'''

def resolve_partial_id(partial: str, items: list[dict], key: str = "id") -> dict:
    """Resolve a partial ID prefix to a single item.

    Raises {variables["AppName"]}Error if zero or multiple matches.
    """
    from ..core.exceptions import {variables["AppName"]}Error

    matches = [item for item in items if str(item.get(key, "")).startswith(partial)]
    if len(matches) == 0:
        raise {variables["AppName"]}Error(f"No item found matching '{{partial}}'")
    if len(matches) > 1:
        ids = [str(m.get(key, "")) for m in matches[:5]]
        raise {variables["AppName"]}Error(f"Ambiguous ID '{{partial}}', matches: {{', '.join(ids)}}")
    return matches[0]''')

    if has_polling:
        sections.append(f'''

def poll_until_complete(
    check_fn,
    *,
    timeout: float = 300.0,
    initial_delay: float = 2.0,
    max_delay: float = 10.0,
    backoff_factor: float = 1.5,
):
    """Poll check_fn with exponential backoff until it returns a truthy value.

    Args:
        check_fn: Callable that returns a result (truthy = done) or None/falsy.
        timeout: Maximum total wait time in seconds.
        initial_delay: First sleep interval.
        max_delay: Cap on sleep interval.
        backoff_factor: Multiplier per iteration.

    Returns:
        The truthy result from check_fn.

    Raises:
        {variables["AppName"]}Error if timeout is exceeded.
    """
    import time

    from ..core.exceptions import {variables["AppName"]}Error

    elapsed = 0.0
    delay = initial_delay
    while elapsed < timeout:
        result = check_fn()
        if result:
            return result
        time.sleep(delay)
        elapsed += delay
        delay = min(delay * backoff_factor, max_delay)
    raise {variables["AppName"]}Error(f"Operation timed out after {{timeout}}s")''')

    if has_context:
        sections.append('''

def get_context_value(key: str) -> str | None:
    """Read a value from the persistent context file."""
    import json as _json

    from ..core.config import CONFIG_DIR, CONTEXT_FILE

    path = CONFIG_DIR / CONTEXT_FILE
    if not path.exists():
        return None
    data = _json.loads(path.read_text())
    return data.get(key)


def set_context_value(key: str, value: str) -> None:
    """Write a value to the persistent context file."""
    import json as _json

    from ..core.config import CONFIG_DIR, CONTEXT_FILE

    path = CONFIG_DIR / CONTEXT_FILE
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        data = _json.loads(path.read_text())
    data[key] = value
    path.write_text(_json.dumps(data, indent=2))''')

    if sections:
        content += "\n" + "\n".join(sections) + "\n"

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

    # Build extras_require
    extras = []
    if auth_type in ("cookie", "google-sso"):
        extras.append('"browser": ["playwright>=1.40.0"],')

    extras_require = "\n        ".join(extras) if extras else ""

    variables = {**variables, "install_requires": install_requires, "extras_require": extras_require}
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

    # config.py (conditional on auth_type + has_context)
    config_tpl = select_config_template(auth_type, has_context)
    write_file(
        core_dir / "config.py",
        render_template(TEMPLATES_DIR / config_tpl, variables),
    )

    # client.py (variant based on protocol + http_client)
    client_tpl = select_client_template(protocol, http_client)
    write_file(
        core_dir / "client.py",
        render_template(TEMPLATES_DIR / client_tpl, variables),
    )

    # auth.py (conditional)
    if auth_type != "none":
        write_file(
            core_dir / "auth.py",
            render_template(TEMPLATES_DIR / "auth.py.tpl", variables),
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

    resources = [r.strip() for r in args.resources.split(",") if r.strip()]

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
