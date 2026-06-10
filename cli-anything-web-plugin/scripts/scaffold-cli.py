#!/usr/bin/env python3
"""Scaffold a cli-web-* CLI from Jinja2 templates.

Generates the full boilerplate directory structure for a new CLI-Anything-WEB
project. Templates use Jinja2 with ``${name}`` variable delimiters (so the
historic placeholder syntax keeps working) plus ``{% if %}`` blocks for
profile-conditional sections (protocol, http_client, auth_type).

Usage:
    python scaffold-cli.py <output-dir> \
      --app-name hackernews \
      --protocol rest \
      --http-client httpx \
      --auth-type cookie \
      --resources stories,users,search \
      --resource stories --resource users \
      --has-polling \
      --has-context \
      --has-partial-ids

Output:
    Creates <output-dir>/cli_web/<app>/ with full boilerplate structure,
    plus <output-dir>/setup.py, README.md, skill/SKILL.md, and a
    .manifest.json provenance record.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure sibling modules resolve whether invoked as a script or via importlib.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from plugin_paths import get_plugin_root, get_scripts_dir, get_templates_dir  # noqa: E402

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    from jinja2.exceptions import UndefinedError
except ImportError:  # pragma: no cover - exercised only when jinja2 is absent
    sys.exit("scaffold-cli.py requires jinja2 — run: pip install jinja2 (or bash scripts/setup.sh)")

SCRIPT_DIR = get_scripts_dir()
PLUGIN_DIR = get_plugin_root()
TEMPLATES_DIR = get_templates_dir()

#: Bumped whenever templates change shape. Recorded in every generated
#: .manifest.json so fleet tooling (drift/resync) can tell which CLIs
#: predate a template fix.
TEMPLATE_VERSION = "2.1.0"
MANIFEST_NAME = ".manifest.json"
MANIFEST_VERSION = 1

#: Single shared Jinja2 environment. ``${name}`` variable delimiters keep all
#: pre-Jinja templates working unchanged; StrictUndefined turns any missing
#: variable into a render-time error (the old "unresolved placeholder" check).
_ENV = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    variable_start_string="${",
    variable_end_string="}",
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)


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


def find_unresolved_placeholders(content: str) -> list[str]:
    """Return list of any ${...} placeholders still present in rendered output."""
    return sorted(set(_PLACEHOLDER_RE.findall(content)))


def render_string(content: str, variables: dict) -> str:
    """Render a template string (``${name}`` variables, ``{% %}`` blocks).

    Raises ValueError if the string references a variable that is missing
    from the variables dict (StrictUndefined).
    """
    try:
        return _ENV.from_string(content).render(**variables)
    except UndefinedError as exc:
        raise ValueError(f"Template string has unresolved placeholders: {exc.message}") from exc


def render_template(tpl_name: str, variables: dict) -> str:
    """Render a template from templates/ by name and validate the output.

    Raises ValueError if the template references a variable missing from the
    variables dict (StrictUndefined), or if any literal ``${name}`` survives
    rendering — this catches typos and newly-added template vars that weren't
    wired into the variables dict.
    """
    try:
        rendered = _ENV.get_template(tpl_name).render(**variables)
    except UndefinedError as exc:
        raise ValueError(
            f"Template {tpl_name} has unresolved placeholders after render: {exc.message}. "
            f"Add them to the variables dict or fix the template."
        ) from exc
    unresolved = find_unresolved_placeholders(rendered)
    if unresolved:
        raise ValueError(
            f"Template {tpl_name} has unresolved placeholders after render: "
            f"{', '.join('${' + p + '}' for p in unresolved)}. "
            f"Add them to the variables dict or fix the template."
        )
    return rendered


def write_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent dirs.

    Validates that no ${name} placeholders and no raw Jinja ``{%`` block tags
    remain — protects against fragments built without render_template.
    """
    unresolved = find_unresolved_placeholders(content)
    if unresolved:
        raise ValueError(
            f"Refusing to write {path}: unresolved placeholders "
            f"{', '.join('${' + p + '}' for p in unresolved)}"
        )
    if "{%" in content:
        raise ValueError(f"Refusing to write {path}: raw Jinja block tag '{{%' in content")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Created: {path}")


# ---------------------------------------------------------------------------
# Client variant selection
# ---------------------------------------------------------------------------

VALID_PROTOCOLS = ("rest", "graphql", "html-scraping", "batchexecute")


def build_client(variables: dict, protocol: str, http_client: str) -> str:
    """Render client.py for the requested protocol/http_client profile.

    Protocol-specific helper methods (_graphql, _parse_html/_get_html) live in
    the client templates behind ``{% if protocol == ... %}`` blocks; the
    ``protocol`` value in the render context selects them.
    """
    if protocol not in VALID_PROTOCOLS:
        raise ValueError(
            f"Unknown protocol '{protocol}'. Must be one of: {', '.join(VALID_PROTOCOLS)}"
        )

    if protocol == "batchexecute":
        return render_template("client_batchexecute.py.tpl", variables)

    base_tpl = (
        "client_rest_curl.py.tpl" if http_client == "curl_cffi" else "client_rest_httpx.py.tpl"
    )
    return render_template(base_tpl, variables)


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


def build_helpers(
    variables: dict, has_polling: bool, has_context: bool, has_partial_ids: bool
) -> str:
    """Render helpers.py by composing the base template with feature fragments."""
    flags = {
        "has_partial_ids": has_partial_ids,
        "has_polling": has_polling,
        "has_context": has_context,
    }
    content = render_template("helpers.py.tpl", variables)
    for flag_name, fragment_name in _HELPER_FRAGMENTS:
        if flags[flag_name]:
            content += render_template(fragment_name, variables)
    return content


# ---------------------------------------------------------------------------
# Provenance manifest
# ---------------------------------------------------------------------------


def _plugin_version() -> str:
    """Read the plugin version from .claude-plugin/plugin.json."""
    manifest = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
    try:
        version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
        return str(version) if version else "unknown"
    except (OSError, json.JSONDecodeError):
        return "unknown"


def build_manifest(app_name: str, protocol: str, http_client: str, auth_type: str) -> dict:
    """Build the .manifest.json provenance record (devkit-compatible shape)."""
    return {
        "manifest_version": MANIFEST_VERSION,
        "cli": f"cli-web-{app_name}",
        "generator": {
            "plugin_version": _plugin_version(),
            "template_version": TEMPLATE_VERSION,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "profile": {
            "protocol": protocol,
            "http_client": http_client,
            "auth_type": auth_type,
        },
        "shared_files": {},
        "overrides": [],
    }


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
    resource_modules: list[str] | None = None,
) -> None:
    """Generate the full boilerplate structure."""
    resource_modules = resource_modules or []
    app_underscore = to_underscore(app_name)
    # auth_type is normalized to underscore form (google-sso -> google_sso)
    # so templates can use Python-identifier-style comparisons.
    variables = {
        "app_name": app_name,
        "app_name_underscore": app_underscore,
        "APP_NAME": to_upper_snake(app_name),
        "AppName": to_pascal(app_name),
        "protocol": protocol,
        "http_client": http_client,
        "auth_type": auth_type.replace("-", "_"),
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
    if resource_modules:
        print(f"  Command modules: {resource_modules}")
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
        render_template("exceptions.py.tpl", variables),
    )

    # client.py (variant based on protocol + http_client)
    write_file(
        core_dir / "client.py",
        build_client(variables, protocol, http_client),
    )

    # auth.py — single template; {% if auth_type == "google_sso" %} selects the
    # regional-cookie-priority + login_browser SSO scaffold, otherwise the
    # generic thin variant (cookie / api-key).
    if auth_type != "none":
        write_file(
            core_dir / "auth.py",
            render_template("auth.py.tpl", variables),
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
            render_template("rpc_types.py.tpl", variables),
        )
        write_file(
            rpc_dir / "encoder.py",
            render_template("rpc_encoder.py.tpl", variables),
        )
        write_file(
            rpc_dir / "decoder.py",
            render_template("rpc_decoder.py.tpl", variables),
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
        render_template("output.py.tpl", variables),
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

    # One scaffold module per --resource. Registration is intentionally NOT
    # automatic — the agent wires `cli.add_command(...)` in the entry point
    # (see the FILL_IN marker in <app>_cli.py).
    for resource in resource_modules:
        resource_underscore = to_underscore(resource)
        write_file(
            commands_dir / f"{resource_underscore}.py",
            render_template(
                "command_group.py.tpl",
                {
                    **variables,
                    "resource": resource,
                    "resource_underscore": resource_underscore,
                },
            ),
        )

    # ── 7. tests/ ──────────────────────────────────────────────────────────
    write_file(tests_dir / "__init__.py", "")
    write_file(
        tests_dir / "conftest.py",
        render_template("conftest.py.tpl", variables),
    )
    write_file(
        tests_dir / "test_e2e.py",
        render_template("test_e2e.py.tpl", variables),
    )

    # ── 8. CLI entry point ─────────────────────────────────────────────────
    write_file(
        pkg_dir / f"{app_underscore}_cli.py",
        render_template("cli_entry.py.tpl", variables),
    )

    # ── 9. setup.py ────────────────────────────────────────────────────────
    write_file(
        output_dir / "setup.py",
        render_template("setup.py.tpl", variables),
    )

    # ── 10. Docs skeletons (README + skill) ────────────────────────────────
    write_file(
        output_dir / "README.md",
        render_template("README.md.tpl", variables),
    )
    write_file(
        output_dir / "skill" / "SKILL.md",
        render_template("SKILL.md.tpl", variables),
    )

    # ── 11. Provenance manifest ────────────────────────────────────────────
    manifest = build_manifest(app_name, protocol, http_client, auth_type)
    write_file(
        output_dir / MANIFEST_NAME,
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
    )

    # ── Summary ────────────────────────────────────────────────────────────
    total = sum(1 for _ in output_dir.rglob("*.py"))
    print(f"\nDone! Generated {total} Python files.")
    print("\nNext steps:")
    print("  1. Fill in FILL_IN_BASE_URL in core/client.py")
    print("  2. Add endpoint methods to core/client.py")
    print("  3. Flesh out command modules in commands/ (look for # FILL_IN: markers)")
    print(f"  4. Register commands in {app_underscore}_cli.py (# FILL_IN: cli.add_command)")
    print("  5. Fill in REPL help text")
    print("  6. Replace # FILL_IN: markers in tests/test_e2e.py, README.md, skill/SKILL.md")
    if auth_type != "none":
        print("  7. Implement login flow in core/auth.py")
    if protocol == "batchexecute":
        print("  8. Add RPC method IDs to core/rpc/types.py")


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
    --resources stories,users,search --resource stories --resource users

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
    parser.add_argument(
        "output_dir", type=Path, help="Output directory (e.g., <app>/agent-harness)"
    )
    parser.add_argument(
        "--app-name", required=True, help="CLI app name (e.g., hackernews, gh-trending)"
    )
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
    parser.add_argument(
        "--resource",
        action="append",
        default=[],
        dest="resource_modules",
        metavar="NAME",
        help="Render a commands/<NAME>.py scaffold module (repeatable). "
        "Registration is left to the agent (see FILL_IN marker in the CLI entry).",
    )
    parser.add_argument(
        "--has-polling", action="store_true", help="Include polling/backoff helpers"
    )
    parser.add_argument(
        "--has-context", action="store_true", help="Include persistent context helpers"
    )
    parser.add_argument(
        "--has-partial-ids", action="store_true", help="Include partial ID resolution"
    )

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

    # --resource values become Python module + function names.
    for resource in args.resource_modules:
        resource_underscore = to_underscore(resource)
        if (
            not resource_underscore.isidentifier()
            or resource_underscore.startswith("_")
            or not resource[0].isalpha()
        ):
            parser.error(
                f"--resource {resource!r} converts to {resource_underscore!r}, which "
                f"is not a valid Python module name. Use only letters, digits, "
                f"underscores, or hyphens; must start with a letter."
            )

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
        resource_modules=args.resource_modules,
    )


if __name__ == "__main__":
    main()
