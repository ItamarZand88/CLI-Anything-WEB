#!/usr/bin/env python3
"""Grade an eval output against binary assertions.

Usage:
    python grade_output.py --output response.md --assertions assertions.json
    python grade_output.py --output response.md --assertions assertions.json --no-llm
"""

import argparse
import json
import re
import subprocess
from pathlib import Path


def grade_programmatic(text: str, pattern: str) -> bool:
    """Check if text matches a regex pattern."""
    return bool(re.search(pattern, text, re.IGNORECASE | re.DOTALL))


def grade_llm(text: str, assertion_text: str, timeout: int = 60) -> bool:
    """Use claude -p to grade a subjective assertion."""
    prompt = (
        f"You are a strict grader. Given the following output, does it satisfy "
        f"this assertion?\n\n"
        f"ASSERTION: {assertion_text}\n\n"
        f"OUTPUT (first 3000 chars):\n{text[:3000]}\n\n"
        f"Answer with EXACTLY one word: PASS or FAIL"
    )
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        answer = result.stdout.strip().upper()
        return "PASS" in answer and "FAIL" not in answer
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def grade_output(output_text: str, assertions: list[dict], use_llm: bool = True) -> dict:
    """Grade output against all assertions. Returns results dict."""
    results = []
    for a in assertions:
        assertion_id = a["id"]
        assertion_text = a["text"]
        check_type = a.get("check", "llm")
        pattern = a.get("pattern", "")

        if check_type == "programmatic" and pattern:
            passed = grade_programmatic(output_text, pattern)
        elif check_type == "llm" and use_llm:
            passed = grade_llm(output_text, assertion_text)
        else:
            passed = grade_programmatic(output_text, assertion_text)

        results.append({
            "id": assertion_id,
            "text": assertion_text,
            "passed": passed,
        })

    passed_count = sum(1 for r in results if r["passed"])
    return {
        "assertions": results,
        "passed": passed_count,
        "total": len(results),
        "pass_rate": f"{passed_count}/{len(results)}",
    }


def main():
    parser = argparse.ArgumentParser(description="Grade eval output against assertions")
    parser.add_argument("--output", required=True, help="Path to output file to grade")
    parser.add_argument("--assertions", required=True, help="Path to assertions JSON file")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM grading (programmatic only)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    output_text = Path(args.output).read_text(encoding="utf-8")
    assertions = json.loads(Path(args.assertions).read_text(encoding="utf-8"))

    results = grade_output(output_text, assertions, use_llm=not args.no_llm)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results["assertions"]:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"  [{status}] {r['id']}: {r['text']}")
        print(f"\nScore: {results['pass_rate']}")


if __name__ == "__main__":
    main()
