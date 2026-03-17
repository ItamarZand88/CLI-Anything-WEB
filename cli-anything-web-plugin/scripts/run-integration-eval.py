#!/usr/bin/env python3
"""Run a full integration eval: execute /cli-anything-web pipeline + post-checks.

Usage:
    python run-integration-eval.py --target https://suno.com --plugin-dir cli-anything-web-plugin/
    python run-integration-eval.py --target https://suno.com --plugin-dir . --output evals/integration/suno/
    python run-integration-eval.py --suite evals/integration-suite.json --plugin-dir .
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def extract_app_name(url: str) -> str:
    """Extract app name from URL (e.g., https://suno.com -> suno)."""
    from urllib.parse import urlparse
    hostname = urlparse(url).hostname or url
    # Remove www. and TLD
    parts = hostname.replace("www.", "").split(".")
    return parts[0]


def run_pipeline(target_url: str, plugin_dir: str, timeout_minutes: int = 30) -> dict:
    """Run /cli-anything-web <url> and capture the full transcript."""
    app_name = extract_app_name(target_url)
    prompt = f"/cli-anything-web {target_url}"

    print(f"\n{'='*60}")
    print(f"INTEGRATION EVAL: {target_url}")
    print(f"App name: {app_name}")
    print(f"Timeout: {timeout_minutes} minutes")
    print(f"{'='*60}\n")

    start_time = time.time()

    try:
        result = subprocess.run(
            ["claude", "--plugin-dir", plugin_dir, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout_minutes * 60,
        )
        transcript = result.stdout + "\n" + result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        transcript = f"[TIMEOUT after {timeout_minutes} minutes]"
        exit_code = -1
    except FileNotFoundError:
        print("Error: 'claude' CLI not found.", file=sys.stderr)
        sys.exit(1)

    duration = time.time() - start_time

    return {
        "target_url": target_url,
        "app_name": app_name,
        "transcript": transcript,
        "exit_code": exit_code,
        "duration_seconds": round(duration, 1),
        "timestamp": datetime.now().isoformat(),
    }


def run_post_check(check: dict, timeout: int = 60) -> dict:
    """Run a single post-check command and evaluate the result."""
    cmd = check["cmd"]
    expect = check["expect"]
    check_timeout = check.get("timeout", timeout)

    try:
        result = subprocess.run(
            cmd, shell=True,
            capture_output=True, text=True,
            timeout=check_timeout,
        )

        passed = False
        output = result.stdout.strip()

        if expect == "exit_code_0":
            passed = result.returncode == 0
        elif expect.startswith("contains:"):
            keyword = expect.split(":", 1)[1]
            passed = keyword.lower() in (output + result.stderr).lower()
        elif expect == "valid_json":
            try:
                json.loads(output)
                passed = True
            except json.JSONDecodeError:
                passed = False
        elif expect.startswith("valid_json_with_field:"):
            field = expect.split(":", 1)[1]
            try:
                data = json.loads(output)
                if isinstance(data, list):
                    passed = any(field in item for item in data if isinstance(item, dict))
                elif isinstance(data, dict):
                    passed = field in data
            except json.JSONDecodeError:
                passed = False

        return {
            "id": check["id"],
            "name": check["name"],
            "cmd": cmd,
            "passed": passed,
            "exit_code": result.returncode,
            "output_preview": output[:500],
        }

    except subprocess.TimeoutExpired:
        return {
            "id": check["id"],
            "name": check["name"],
            "cmd": cmd,
            "passed": False,
            "exit_code": -1,
            "output_preview": f"[TIMEOUT after {check_timeout}s]",
        }


def run_integration_eval(target_url: str, plugin_dir: str, post_checks: list[dict],
                         output_dir: Path, timeout_minutes: int = 30) -> dict:
    """Run full integration eval: pipeline + post-checks."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run the pipeline
    pipeline_result = run_pipeline(target_url, plugin_dir, timeout_minutes)

    # Save transcript
    transcript_path = output_dir / "transcript.log"
    transcript_path.write_text(pipeline_result["transcript"], encoding="utf-8")
    print(f"Transcript saved to {transcript_path} ({len(pipeline_result['transcript'])} chars)")

    # Run post-checks
    print(f"\nRunning {len(post_checks)} post-checks...")
    check_results = []
    for check in post_checks:
        if check.get("interactive"):
            print(f"  [SKIP] {check['name']} (interactive — requires manual auth)")
            check_results.append({
                "id": check["id"],
                "name": check["name"],
                "passed": None,
                "output_preview": "Skipped (interactive)",
            })
            continue

        print(f"  Running: {check['name']}...", end=" ", flush=True)
        result = run_post_check(check)
        status = "PASS" if result["passed"] else "FAIL"
        print(status)
        check_results.append(result)

    # Calculate score
    graded = [r for r in check_results if r["passed"] is not None]
    passed = sum(1 for r in graded if r["passed"])

    results = {
        "target_url": target_url,
        "app_name": pipeline_result["app_name"],
        "pipeline_duration_seconds": pipeline_result["duration_seconds"],
        "pipeline_exit_code": pipeline_result["exit_code"],
        "post_checks": check_results,
        "passed": passed,
        "total": len(graded),
        "pass_rate": f"{passed}/{len(graded)}",
        "timestamp": pipeline_result["timestamp"],
    }

    # Save results
    results_path = output_dir / "integration-results.json"
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Print summary
    print(f"\n{'='*40}")
    print(f"RESULT: {results['pass_rate']} post-checks passed")
    print(f"Pipeline duration: {pipeline_result['duration_seconds']}s")
    print(f"{'='*40}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Run integration eval (full pipeline + post-checks)")
    parser.add_argument("--target", help="Target URL (e.g., https://suno.com)")
    parser.add_argument("--suite", help="Path to integration-suite.json (runs all evals)")
    parser.add_argument("--plugin-dir", default=".", help="Path to plugin directory")
    parser.add_argument("--output", "-o", default="evals/integration/", help="Output directory")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in minutes (default: 30)")
    args = parser.parse_args()

    if args.suite:
        suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
        for eval_def in suite["evals"]:
            app = extract_app_name(eval_def["target_url"])
            output_dir = Path(args.output) / app
            run_integration_eval(
                eval_def["target_url"],
                args.plugin_dir,
                eval_def["post_checks"],
                output_dir,
                eval_def.get("timeout_minutes", args.timeout),
            )
    elif args.target:
        app = extract_app_name(args.target)
        output_dir = Path(args.output) / app
        # Default post-checks for unknown target
        default_checks = [
            {"id": "P1", "name": "CLI installed", "cmd": f"which cli-web-{app}", "expect": "exit_code_0"},
            {"id": "P2", "name": "Help works", "cmd": f"cli-web-{app} --help", "expect": "exit_code_0"},
            {"id": "P3", "name": "Package importable", "cmd": f"python -c \"import cli_web.{app}\"", "expect": "exit_code_0"},
        ]
        run_integration_eval(args.target, args.plugin_dir, default_checks, output_dir, args.timeout)
    else:
        parser.error("Either --target or --suite is required")


if __name__ == "__main__":
    main()
