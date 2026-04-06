#!/usr/bin/env python3
"""Generate TEST.md for a cli-web-* CLI.

Parses test files via AST to produce Part 1 (test plan), and optionally
runs pytest to generate Part 2 (results).

Usage:
    # Generate Part 1 (test plan) from test files
    python generate-test-docs.py plan <tests-dir> --app-name hackernews

    # Generate Part 2 (results) by running pytest and appending
    python generate-test-docs.py results <tests-dir> --app-name hackernews

    # Generate full TEST.md (both parts)
    python generate-test-docs.py full <tests-dir> --app-name hackernews
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# AST parsing — extract test classes and methods
# ---------------------------------------------------------------------------

def parse_test_file(path: Path) -> list[dict]:
    """Parse a test file and extract test classes with their methods.

    Returns:
        List of dicts: {"class": str, "methods": list[str], "layer": str}
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    results = []
    filename = path.name

    # Classify layer
    if "core" in filename or "unit" in filename:
        default_layer = "Unit (mocked)"
    elif "e2e" in filename or "live" in filename:
        default_layer = "E2E (live)"
    elif "integration" in filename:
        default_layer = "Integration"
    else:
        default_layer = "Unit"

    # Single pass: collect top-level test functions and test classes
    top_funcs = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            top_funcs.append(node.name)
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            methods = [
                n.name for n in ast.iter_child_nodes(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name.startswith("test_")
            ]
            if methods:
                layer = default_layer
                if "Subprocess" in node.name:
                    layer = "Subprocess"
                elif "Live" in node.name or "E2E" in node.name:
                    layer = "E2E (live)"
                elif "Unit" in node.name:
                    layer = "Unit (mocked)"

                results.append({
                    "class": node.name,
                    "methods": methods,
                    "layer": layer,
                })

    if top_funcs:
        # Prepend module-level functions before classes
        results.insert(0, {
            "class": f"(module-level in {filename})",
            "methods": top_funcs,
            "layer": default_layer,
        })

    return results


# ---------------------------------------------------------------------------
# Part 1: Test Plan
# ---------------------------------------------------------------------------

def generate_plan(tests_dir: Path, app_name: str) -> str:
    """Generate TEST.md Part 1 from test files."""
    lines = [
        f"# TEST.md — cli-web-{app_name} Test Plan & Results\n",
        "",
        "## Part 1: Test Plan\n",
        "",
    ]

    # Find all test files
    test_files = sorted(tests_dir.glob("test_*.py"))
    if not test_files:
        lines.append("*No test files found.*\n")
        return "\n".join(lines)

    # Parse all files
    all_classes = []
    file_summaries = []
    for tf in test_files:
        classes = parse_test_file(tf)
        total = sum(len(c["methods"]) for c in classes)
        layers = set(c["layer"] for c in classes)
        layer_str = " + ".join(sorted(layers)) if layers else "Unknown"
        file_summaries.append((tf.name, total, layer_str))
        all_classes.extend([(tf.name, c) for c in classes])

    # Inventory table
    lines.append("### Test Inventory\n")
    lines.append("| File | Tests | Layer |")
    lines.append("|------|-------|-------|")
    for name, count, layer in file_summaries:
        lines.append(f"| {name} | {count} | {layer} |")
    lines.append("")

    total_tests = sum(s[1] for s in file_summaries)
    lines.append(f"**Total: {total_tests} tests**\n")
    lines.append("")

    # Detailed breakdown by file
    current_file = ""
    for filename, cls in all_classes:
        if filename != current_file:
            current_file = filename
            lines.append(f"### {filename}\n")

        lines.append(f"**{cls['class']}** ({len(cls['methods'])} tests) — {cls['layer']}\n")
        for m in cls["methods"]:
            # Convert test_foo_bar to readable "Foo bar"
            readable = m.replace("test_", "").replace("_", " ")
            lines.append(f"- `{m}` — {readable}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Part 2: Test Results
# ---------------------------------------------------------------------------

def generate_results(tests_dir: Path, app_name: str) -> str:
    """Run pytest and generate TEST.md Part 2."""
    lines = [
        "",
        "---\n",
        "",
        "## Part 2: Test Results\n",
        "",
    ]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"**Date:** {now}\n")
    lines.append("")

    # Find the harness dir (parent of cli_web/<app>/tests/)
    harness_dir = tests_dir
    while harness_dir.name != "agent-harness" and harness_dir.parent != harness_dir:
        harness_dir = harness_dir.parent

    # Run pytest
    cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "-v", "--tb=short", "-q",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(harness_dir) if harness_dir.name == "agent-harness" else None,
        )
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        output = "TIMEOUT: pytest exceeded 300s limit"
    except FileNotFoundError:
        output = "ERROR: pytest not found. Install with: pip install pytest"

    # Parse results from pytest summary line (e.g., "3 passed, 1 failed in 0.5s")
    summary_match = re.search(r"=+\s*(.*?)\s*=+\s*$", output, re.MULTILINE)
    summary = summary_match.group(1) if summary_match else ""
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", summary)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", summary)) else 0
    errors = int(m.group(1)) if (m := re.search(r"(\d+) error", summary)) else 0
    skipped = int(m.group(1)) if (m := re.search(r"(\d+) skipped", summary)) else 0
    total = passed + failed + errors + skipped

    # Time extraction
    time_match = re.search(r"in ([\d.]+)s", output)
    elapsed = time_match.group(1) + "s" if time_match else "N/A"

    pass_rate = f"{passed}/{total} ({passed/total*100:.0f}%)" if total > 0 else "N/A"

    lines.append("### Summary\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total tests | {total} |")
    lines.append(f"| Passed | {passed} |")
    lines.append(f"| Failed | {failed} |")
    lines.append(f"| Errors | {errors} |")
    lines.append(f"| Skipped | {skipped} |")
    lines.append(f"| Pass rate | {pass_rate} |")
    lines.append(f"| Execution time | {elapsed} |")
    lines.append(f"| Date | {now} |")
    lines.append("")

    # Include raw output
    lines.append("### Raw Output\n")
    lines.append("```")
    lines.append(output.strip())
    lines.append("```\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate TEST.md for cli-web-* CLI.")
    parser.add_argument(
        "mode",
        choices=["plan", "results", "full"],
        help="What to generate: plan (Part 1), results (Part 2), or full (both)",
    )
    parser.add_argument("tests_dir", type=Path, help="Path to tests/ directory")
    parser.add_argument("--app-name", required=True, help="CLI app name")
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Output file path (default: <tests-dir>/TEST.md)",
    )

    args = parser.parse_args()

    tests_dir = args.tests_dir.resolve()
    if not tests_dir.is_dir():
        print(f"Error: {tests_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or (tests_dir / "TEST.md")

    if args.mode == "plan":
        content = generate_plan(tests_dir, args.app_name)
        output_path.write_text(content, encoding="utf-8")
        print(f"Generated Part 1 (test plan) -> {output_path}")

    elif args.mode == "results":
        # Read existing Part 1 if it exists
        existing = ""
        if output_path.exists():
            existing = output_path.read_text(encoding="utf-8")

        results = generate_results(tests_dir, args.app_name)

        if existing and "## Part 2" in existing:
            # Replace existing Part 2
            idx = existing.index("## Part 2")
            # Find the --- separator before Part 2
            sep_idx = existing.rfind("---", 0, idx)
            if sep_idx > 0:
                content = existing[:sep_idx].rstrip() + "\n" + results
            else:
                content = existing[:idx].rstrip() + "\n" + results
        elif existing:
            content = existing.rstrip() + "\n" + results
        else:
            content = results

        output_path.write_text(content, encoding="utf-8")
        print(f"Generated Part 2 (results) -> {output_path}")

    elif args.mode == "full":
        plan = generate_plan(tests_dir, args.app_name)
        results = generate_results(tests_dir, args.app_name)
        content = plan + results
        output_path.write_text(content, encoding="utf-8")
        print(f"Generated full TEST.md -> {output_path}")


if __name__ == "__main__":
    main()
