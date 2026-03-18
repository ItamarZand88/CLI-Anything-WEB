#!/usr/bin/env python3
"""Run the full eval suite for skill optimization.

Usage:
    python run-eval.py --evals evals/eval-suite.json
    python run-eval.py --evals evals/eval-suite.json --runs 3 --output evals/results.json
    python run-eval.py --evals evals/eval-suite.json --no-llm-grading
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from grade_output import grade_output  # type: ignore[import-not-found]  # resolved via sys.path


def load_skill_content(skill_dir: Path, skill_names: list[str]) -> str:
    """Load skill SKILL.md content for inline injection into prompts."""
    content_parts = []
    for name in skill_names:
        skill_path = skill_dir / name / "SKILL.md"
        if skill_path.exists():
            content_parts.append(f"## Skill: {name}\n\n{skill_path.read_text(encoding='utf-8')}")
        refs_dir = skill_dir / name / "references"
        if refs_dir.exists():
            for ref_file in sorted(refs_dir.glob("*.md")):
                content_parts.append(
                    f"## Reference: {ref_file.name}\n\n{ref_file.read_text(encoding='utf-8')}"
                )
    return "\n\n---\n\n".join(content_parts)


def run_single_eval(prompt: str, skill_content: str, timeout: int = 120) -> str:
    """Run a single eval by spawning claude -p with skill content prepended."""
    full_prompt = (
        f"You have access to the following skills. Read them carefully before "
        f"completing the task.\n\n{skill_content}\n\n"
        f"## Task\n\n{prompt}\n\n"
        f"Write your complete response below."
    )
    try:
        result = subprocess.run(
            ["claude", "-p", full_prompt],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT: agent did not respond within {timeout}s]"
    except FileNotFoundError:
        print("Error: 'claude' CLI not found. Install Claude Code first.", file=sys.stderr)
        sys.exit(1)


def run_eval_suite(eval_suite_path: Path, skill_dir: Path, runs: int = 3,
                   use_llm_grading: bool = True) -> dict:
    """Run all evals in the suite, grade outputs, return results."""
    suite = json.loads(eval_suite_path.read_text(encoding="utf-8"))
    runs_per = suite.get("runs_per_eval", runs)

    all_results = []

    for eval_def in suite["evals"]:
        eval_id = eval_def["id"]
        eval_name = eval_def.get("name", eval_id)
        prompt = eval_def["prompt"]
        skills = eval_def.get("skills_to_load", [])
        assertions = eval_def["assertions"]

        print(f"\n--- Eval: {eval_name} ({len(assertions)} assertions, {runs_per} runs) ---")

        skill_content = load_skill_content(skill_dir, skills)

        run_results = []
        for i in range(runs_per):
            print(f"  Run {i+1}/{runs_per}...", end=" ", flush=True)
            output = run_single_eval(prompt, skill_content)
            grading = grade_output(output, assertions, use_llm=use_llm_grading)
            run_results.append(grading)
            print(f"{grading['pass_rate']}")

        # Majority vote per assertion
        final_assertions = []
        for a_idx, assertion in enumerate(assertions):
            votes = [r["assertions"][a_idx]["passed"] for r in run_results]
            passed = sum(votes) > len(votes) / 2
            final_assertions.append({
                "id": assertion["id"],
                "text": assertion["text"],
                "passed": passed,
                "votes": f"{sum(votes)}/{len(votes)}",
            })

        passed_count = sum(1 for a in final_assertions if a["passed"])
        eval_result = {
            "eval_id": eval_id,
            "eval_name": eval_name,
            "assertions": final_assertions,
            "passed": passed_count,
            "total": len(assertions),
            "pass_rate": f"{passed_count}/{len(assertions)}",
        }
        all_results.append(eval_result)

    total_passed = sum(r["passed"] for r in all_results)
    total_assertions = sum(r["total"] for r in all_results)

    return {
        "timestamp": datetime.now().isoformat(),
        "evals": all_results,
        "total_passed": total_passed,
        "total_assertions": total_assertions,
        "overall_pass_rate": f"{total_passed}/{total_assertions}",
        "overall_percentage": round(total_passed / total_assertions * 100, 1) if total_assertions else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Run eval suite for skill optimization")
    parser.add_argument("--evals", required=True, help="Path to eval-suite.json")
    parser.add_argument("--skill-dir", default="skills/", help="Path to skills/ directory")
    parser.add_argument("--runs", type=int, default=3, help="Runs per eval (default: 3)")
    parser.add_argument("--output", "-o", help="Save results to JSON file")
    parser.add_argument("--no-llm-grading", action="store_true", help="Programmatic grading only")
    args = parser.parse_args()

    results = run_eval_suite(
        Path(args.evals),
        Path(args.skill_dir),
        runs=args.runs,
        use_llm_grading=not args.no_llm_grading,
    )

    print(f"\n{'='*50}")
    print(f"OVERALL: {results['overall_pass_rate']} ({results['overall_percentage']}%)")
    print(f"{'='*50}")
    for r in results["evals"]:
        print(f"  {r['eval_name']}: {r['pass_rate']}")
        for a in r["assertions"]:
            status = "PASS" if a["passed"] else "FAIL"
            print(f"    [{status}] {a['id']}: {a['text']} (votes: {a['votes']})")

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
