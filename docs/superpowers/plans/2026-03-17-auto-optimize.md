# Auto-Optimize System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an autonomous skill optimization loop that iteratively improves plugin skills by running evals, grading outputs, and keeping only improvements.

**Architecture:** Three layers — `scripts/grade_output.py` (grades one output), `scripts/run-eval.py` (orchestrates eval suite), `skills/auto-optimize/SKILL.md` (teaches the agent the loop). Eval definitions in `evals/eval-suite.json`. Results logged to `evals/results.tsv`.

**Tech Stack:** Python 3.10+ (subprocess, json, re, argparse), `claude -p` CLI for agent spawning

**Spec:** `docs/superpowers/specs/2026-03-17-auto-optimize-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/grade_output.py` | **CREATE** | Grade one output against binary assertions |
| `scripts/run-eval.py` | **CREATE** | Orchestrate full eval suite |
| `evals/eval-suite.json` | **CREATE** | 4 evals, 34 binary assertions |
| `skills/auto-optimize/SKILL.md` | **CREATE** | Optimization loop methodology |
| `commands/auto-optimize.md` | **CREATE** | Command entry point |
| `verify-plugin.sh` | **UPDATE** | Add auto-optimize skill check |
| `.gitignore` | **UPDATE** | Add evals/results.tsv |
| `skills/cli-anything-web-methodology/SKILL.md` | **UPDATE** | Add companion skill |

---

## Chunk 1: Scripts (grade_output.py + run-eval.py)

### Task 1: Create scripts/grade_output.py

**Files:**
- Create: `cli-anything-web-plugin/scripts/grade_output.py`

- [ ] **Step 1: Write grade_output.py**

This script grades a single output file against a list of binary assertions.
Two modes: programmatic (regex match) and LLM (spawn `claude -p` grader).

```python
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
import sys
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
            # Fallback: programmatic with assertion text as pattern
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
```

- [ ] **Step 2: Verify it runs**

```bash
cd cli-anything-web-plugin && python scripts/grade_output.py --help
```
Expected: help text prints.

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/scripts/grade_output.py
git commit -m "feat: add grade_output.py for binary assertion grading"
```

---

### Task 2: Create scripts/run-eval.py

**Files:**
- Create: `cli-anything-web-plugin/scripts/run-eval.py`

- [ ] **Step 1: Write run-eval.py**

Orchestrates the full eval suite: reads eval-suite.json, spawns agents, grades outputs, produces scores.

```python
#!/usr/bin/env python3
"""Run the full eval suite for skill optimization.

Usage:
    python run-eval.py --evals evals/eval-suite.json
    python run-eval.py --evals evals/eval-suite.json --runs 3 --output evals/results.json
    python run-eval.py --evals evals/eval-suite.json --no-llm-grading
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add scripts dir to path for grade_output import
sys.path.insert(0, str(Path(__file__).parent))
from grade_output import grade_output


def load_skill_content(skill_dir: Path, skill_names: list[str]) -> str:
    """Load skill SKILL.md content for inline injection into prompts."""
    content_parts = []
    for name in skill_names:
        skill_path = skill_dir / name / "SKILL.md"
        if skill_path.exists():
            content_parts.append(f"## Skill: {name}\n\n{skill_path.read_text(encoding='utf-8')}")
        # Also load references
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
        return "[TIMEOUT: agent did not respond within {timeout}s]"
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

        # Load skill content
        skill_content = load_skill_content(skill_dir, skills)

        # Run N times
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
            passed = sum(votes) > len(votes) / 2  # majority
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

    # Aggregate
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

    # Print summary
    print(f"\n{'='*50}")
    print(f"OVERALL: {results['overall_pass_rate']} ({results['overall_percentage']}%)")
    print(f"{'='*50}")
    for r in results["evals"]:
        print(f"  {r['eval_name']}: {r['pass_rate']}")
        for a in r["assertions"]:
            status = "PASS" if a["passed"] else "FAIL"
            print(f"    [{status}] {a['id']}: {a['text']} (votes: {a['votes']})")

    # Save results
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it runs**

```bash
cd cli-anything-web-plugin && python scripts/run-eval.py --help
```
Expected: help text prints.

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/scripts/run-eval.py
git commit -m "feat: add run-eval.py for automated eval suite execution"
```

---

## Chunk 2: Eval Suite + Skill + Integration

### Task 3: Create evals/eval-suite.json

**Files:**
- Create: `cli-anything-web-plugin/evals/eval-suite.json`

- [ ] **Step 1: Write eval-suite.json**

Use the exact JSON from the spec (4 evals, 34 assertions). Copy it verbatim from `docs/superpowers/specs/2026-03-17-auto-optimize-design.md` lines 118-228.

- [ ] **Step 2: Verify valid JSON**

```bash
cd cli-anything-web-plugin && python -c "import json; d=json.load(open('evals/eval-suite.json')); print(f'{len(d[\"evals\"])} evals, {sum(len(e[\"assertions\"]) for e in d[\"evals\"])} assertions')"
```
Expected: `4 evals, 34 assertions`

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/evals/eval-suite.json
git commit -m "feat: add eval-suite.json with 4 evals and 34 binary assertions"
```

---

### Task 4: Create skills/auto-optimize/SKILL.md

**Files:**
- Create: `cli-anything-web-plugin/skills/auto-optimize/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

The methodology skill teaching the agent the optimization loop. Must include:

- YAML frontmatter with name `auto-optimize`, description with trigger phrases
- The complete loop (setup → loop forever → keep/discard)
- How to identify weak assertions (parse results, find most-failed)
- Mutation strategies (6 types): clarify, add examples, simplify, add constraints, remove content, reorder
- Decision rule: `new_pass_rate > baseline -> KEEP, else DISCARD`
- How to run evals: `python scripts/run-eval.py --evals evals/eval-suite.json --skill-dir skills/`
- How to log: append to `evals/results.tsv`
- Simplicity criterion
- When to try radical changes (3+ consecutive discards)
- The `results.tsv` format

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/skills/auto-optimize/SKILL.md
git commit -m "feat: add auto-optimize skill with optimization loop methodology"
```

---

### Task 5: Create commands/auto-optimize.md

**Files:**
- Create: `cli-anything-web-plugin/commands/auto-optimize.md`

- [ ] **Step 1: Write the command**

```markdown
---
name: cli-anything-web:auto-optimize
description: Run autonomous skill optimization loop. Iteratively modifies skills, runs evals, keeps improvements, discards regressions. Runs until interrupted.
argument-hint: [--iterations N] [--target-score N]
allowed-tools: Bash(*), Read, Write, Edit
---

## CRITICAL: Read the auto-optimize skill first

@${CLAUDE_PLUGIN_ROOT}/skills/auto-optimize/SKILL.md

# CLI-Anything-Web: Auto-Optimize Skills

## Process

Follow the auto-optimize skill's loop exactly:

1. **Setup:**
   - Create branch: `git checkout -b autoresearch/$(date +%Y%m%d)`
   - Run baseline: `python ${CLAUDE_PLUGIN_ROOT}/scripts/run-eval.py --evals ${CLAUDE_PLUGIN_ROOT}/evals/eval-suite.json --skill-dir ${CLAUDE_PLUGIN_ROOT}/skills/ --output baseline.json`
   - Initialize `evals/results.tsv` with baseline score
   - Confirm baseline with user

2. **Loop (repeat until interrupted):**
   - Read results.tsv — find weakest assertions
   - Propose ONE change to ONE skill file
   - `git commit`
   - Run eval suite
   - If score improved: KEEP commit
   - If not: `git reset --hard HEAD~1`
   - Log to results.tsv
   - Continue

3. **Stopping conditions (optional):**
   - `--iterations N` — stop after N iterations
   - `--target-score N` — stop when score reaches N
   - Manual interrupt (Ctrl+C) — always available

## Output

- Optimized skill files on the branch
- `evals/results.tsv` — full experiment log
- Git history showing kept improvements
```

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/commands/auto-optimize.md
git commit -m "feat: add auto-optimize command for skill optimization loop"
```

---

### Task 6: Update existing files (verify-plugin.sh, .gitignore, methodology)

**Files:**
- Modify: `cli-anything-web-plugin/verify-plugin.sh`
- Modify: `cli-anything-web-plugin/.gitignore` (create if missing inside plugin)
- Modify: `cli-anything-web-plugin/skills/cli-anything-web-methodology/SKILL.md`

- [ ] **Step 1: Update verify-plugin.sh skills loop**

Add `auto-optimize` to the skills check loop.

- [ ] **Step 2: Update .gitignore**

Add to root `.gitignore`:
```
evals/results.tsv
```

- [ ] **Step 3: Update methodology SKILL.md**

Add to companion skills table:
```
| **auto-optimize** | Autonomous skill optimization — run evals, improve instructions, keep winners |
```

- [ ] **Step 4: Run verify-plugin.sh**

```bash
cd cli-anything-web-plugin && bash verify-plugin.sh
```
Expected: 19/19 checks pass (was 18, +1 for auto-optimize skill).

- [ ] **Step 5: Commit**

```bash
git add cli-anything-web-plugin/verify-plugin.sh cli-anything-web-plugin/skills/cli-anything-web-methodology/SKILL.md .gitignore
git commit -m "feat: integrate auto-optimize into plugin verification and methodology"
```

---

### Task 7: Final verification

- [ ] **Step 1: Verify all new files exist**

```bash
ls cli-anything-web-plugin/scripts/grade_output.py \
   cli-anything-web-plugin/scripts/run-eval.py \
   cli-anything-web-plugin/evals/eval-suite.json \
   cli-anything-web-plugin/skills/auto-optimize/SKILL.md \
   cli-anything-web-plugin/commands/auto-optimize.md
```

- [ ] **Step 2: Verify scripts run**

```bash
cd cli-anything-web-plugin && python scripts/grade_output.py --help && python scripts/run-eval.py --help
```

- [ ] **Step 3: Verify eval-suite.json is valid**

```bash
cd cli-anything-web-plugin && python -c "import json; d=json.load(open('evals/eval-suite.json')); print(f'{len(d[\"evals\"])} evals, {sum(len(e[\"assertions\"]) for e in d[\"evals\"])} assertions')"
```
Expected: `4 evals, 34 assertions`

- [ ] **Step 4: Run verify-plugin.sh**

```bash
cd cli-anything-web-plugin && bash verify-plugin.sh
```
Expected: 19/19 checks pass.
