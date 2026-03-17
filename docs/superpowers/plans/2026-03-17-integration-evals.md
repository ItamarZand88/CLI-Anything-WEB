# Integration Evals + Process Analysis Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Level 2 (integration evals — run full pipeline, test generated CLI) and Level 3 (process analysis — parse transcript, extract timing/errors/dead ends, propose HARNESS improvements).

**Architecture:** `run-integration-eval.py` spawns `claude` with plugin loaded, captures transcript, runs post-checks. `analyze-transcript.py` parses the transcript for timing, errors, dead ends, and generates improvement proposals. Both feed into the auto-optimize loop via `--level 2` and `--level 3` flags.

**Tech Stack:** Python 3.10+ (subprocess, json, re, datetime), `claude` CLI

**Spec:** `docs/superpowers/specs/2026-03-17-integration-evals-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/run-integration-eval.py` | **CREATE** | Run full pipeline + post-checks |
| `scripts/analyze-transcript.py` | **CREATE** | Parse transcript → timing, errors, dead ends, proposals |
| `evals/integration-suite.json` | **CREATE** | Integration eval definitions (target URLs + post-checks) |
| `skills/auto-optimize/SKILL.md` | **UPDATE** | Add Level 2 + Level 3 sections |
| `commands/auto-optimize.md` | **UPDATE** | Add `--level` flag documentation |

---

## Chunk 1: Scripts

### Task 1: Create scripts/run-integration-eval.py

**Files:**
- Create: `cli-anything-web-plugin/scripts/run-integration-eval.py`

- [ ] **Step 1: Write run-integration-eval.py**

```python
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
```

- [ ] **Step 2: Verify**

```bash
cd cli-anything-web-plugin && python scripts/run-integration-eval.py --help
```

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/scripts/run-integration-eval.py
git commit -m "feat: add run-integration-eval.py for Level 2 pipeline testing"
```

---

### Task 2: Create scripts/analyze-transcript.py

**Files:**
- Create: `cli-anything-web-plugin/scripts/analyze-transcript.py`

- [ ] **Step 1: Write analyze-transcript.py**

```python
#!/usr/bin/env python3
"""Analyze an agent transcript from an integration eval run.

Extracts: phase timing, errors, dead ends, patterns, and improvement proposals.

Usage:
    python analyze-transcript.py --transcript evals/integration/suno/transcript.log
    python analyze-transcript.py --transcript transcript.log --output analysis.json
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def extract_phase_timing(transcript: str) -> list[dict]:
    """Extract phase start/end times and durations from transcript."""
    phases = []
    # Look for phase progress markers like "Phase 1 │ DONE" or "Phase 1 │ ▶ START"
    # Also look for "### Phase N" markers
    phase_pattern = re.compile(
        r'Phase\s+(\d+[a-z]?)\s*[│|]\s*(DONE|START|▶|\.\.\.)\s*[│|]\s*(.+?)(?:\s*[│|]|\s*$)',
        re.MULTILINE
    )

    # Simpler: look for phase-related log lines with timestamps
    # The agent typically outputs "Phase X — Name" when starting each phase
    phase_start_pattern = re.compile(
        r'(?:Phase|###\s*Phase)\s+(\d+[a-z]?)\s*[—\-:]+\s*(.+)',
        re.MULTILINE
    )

    found = phase_start_pattern.findall(transcript)
    for phase_num, phase_name in found:
        phases.append({
            "phase": phase_num.strip(),
            "name": phase_name.strip()[:50],
            "status": "detected",
        })

    return phases


def extract_errors(transcript: str) -> list[dict]:
    """Extract errors, failures, and retries from transcript."""
    errors = []

    # Error patterns to look for
    patterns = [
        (r'Error:?\s*(.+)', "error"),
        (r'FAIL(?:ED)?:?\s*(.+)', "failure"),
        (r'Traceback.*?(?=\n\S)', "traceback"),
        (r'(?:Exit code|exit_code)\s*(?:1|[2-9]\d*)', "exit_error"),
        (r'TimeoutError:?\s*(.+)', "timeout"),
        (r'(?:Unknown command|command not found):?\s*(.+)', "command_error"),
        (r'ModuleNotFoundError:?\s*(.+)', "import_error"),
        (r'auth not configured', "auth_error"),
        (r'401|403|429', "http_error"),
    ]

    for pattern, error_type in patterns:
        for match in re.finditer(pattern, transcript, re.IGNORECASE):
            # Get surrounding context (50 chars before and after)
            start = max(0, match.start() - 100)
            end = min(len(transcript), match.end() + 100)
            context = transcript[start:end].strip()

            errors.append({
                "type": error_type,
                "message": match.group(0)[:200],
                "context": context[:300],
                "position": match.start(),
            })

    # Deduplicate by message
    seen = set()
    unique = []
    for e in errors:
        key = e["message"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


def extract_dead_ends(transcript: str) -> list[dict]:
    """Detect unproductive paths the agent went down."""
    dead_ends = []

    # Pattern: agent tries something, it fails, agent tries something else
    # Look for: grep/search through JS bundles (the anti-pattern we documented)
    js_grep_pattern = re.compile(
        r'(?:grep|search|find).*?(?:\.js|webpack|bundle|chunk|manifest)',
        re.IGNORECASE
    )
    if js_grep_pattern.search(transcript):
        dead_ends.append({
            "description": "Agent searched through JavaScript bundles instead of using the feature in the browser",
            "harness_fix": "HARNESS.md already has 'use the feature' guidance — check if agent followed it",
        })

    # Pattern: agent runs tests before configuring auth
    auth_after_test = re.compile(
        r'pytest.*?(?:FAIL|fail).*?auth.*?(?:not configured|missing|expired)',
        re.IGNORECASE | re.DOTALL
    )
    if auth_after_test.search(transcript):
        dead_ends.append({
            "description": "Agent ran tests before configuring auth — got auth failures, then went back to configure",
            "harness_fix": "Make auth configuration step more prominent before test writing in Phase 6",
        })

    # Pattern: sequential implementation when parallel was possible
    sequential = re.compile(
        r'(?:Implement(?:ing)?\s+commands/\w+\.py.*?){3,}',
        re.IGNORECASE | re.DOTALL
    )
    if sequential.search(transcript) and "parallel" not in transcript[:5000].lower():
        dead_ends.append({
            "description": "Agent implemented command files sequentially instead of dispatching parallel subagents",
            "harness_fix": "Make parallel dispatch MANDATORY in Phase 4, not optional",
        })

    # Pattern: agent uses navigate instead of goto
    if "Unknown command: navigate" in transcript:
        dead_ends.append({
            "description": "Agent used 'navigate' instead of 'goto' for playwright-cli",
            "harness_fix": "Add 'goto (NOT navigate)' note to Phase 1 commands",
        })

    return dead_ends


def generate_proposals(phases: list, errors: list, dead_ends: list, transcript: str) -> list[dict]:
    """Generate improvement proposals based on analysis. Uses claude -p if available."""
    proposals = []

    # Rule-based proposals from dead ends
    for de in dead_ends:
        proposals.append({
            "target_file": "HARNESS.md",
            "rationale": de["description"],
            "proposed_fix": de["harness_fix"],
            "source": "dead_end_detection",
        })

    # Rule-based proposals from error patterns
    error_types = [e["type"] for e in errors]
    if error_types.count("auth_error") >= 2:
        proposals.append({
            "target_file": "HARNESS.md",
            "section": "Phase 6 — Test",
            "rationale": f"Auth errors appeared {error_types.count('auth_error')} times — agent keeps forgetting to configure auth before testing",
            "proposed_fix": "Add bold 'CONFIGURE AUTH FIRST' step at the very top of Phase 6, before any test code",
            "source": "error_frequency",
        })

    if error_types.count("command_error") >= 2:
        proposals.append({
            "target_file": "commands/cli-anything-web.md",
            "rationale": f"Command errors appeared {error_types.count('command_error')} times — agent uses wrong playwright-cli commands",
            "proposed_fix": "Add a quick-reference table of correct playwright-cli commands at the top of Phase 1",
            "source": "error_frequency",
        })

    # Try LLM analysis if claude is available
    try:
        # Truncate transcript to fit in prompt
        truncated = transcript[:8000] + "\n...[truncated]...\n" + transcript[-2000:]
        prompt = (
            "You are analyzing an AI agent's transcript from building a CLI for a web app. "
            "Based on this transcript, identify the top 3 improvements to make to the methodology "
            "(HARNESS.md) to make future runs faster and more reliable.\n\n"
            "For each improvement, provide:\n"
            "- target_file: which file to change\n"
            "- rationale: what went wrong\n"
            "- proposed_fix: specific text change\n"
            "- expected_impact: time or quality improvement\n\n"
            "Return ONLY a JSON array of objects. No markdown, no explanation.\n\n"
            f"TRANSCRIPT:\n{truncated}"
        )
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=120,
        )
        try:
            llm_proposals = json.loads(result.stdout.strip())
            if isinstance(llm_proposals, list):
                for p in llm_proposals:
                    p["source"] = "llm_analysis"
                    proposals.append(p)
        except json.JSONDecodeError:
            pass  # LLM didn't return valid JSON — skip
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # claude not available — use rule-based only

    return proposals


def analyze_transcript(transcript_path: Path) -> dict:
    """Full transcript analysis: timing, errors, dead ends, proposals."""
    transcript = transcript_path.read_text(encoding="utf-8")

    phases = extract_phase_timing(transcript)
    errors = extract_errors(transcript)
    dead_ends = extract_dead_ends(transcript)
    proposals = generate_proposals(phases, errors, dead_ends, transcript)

    return {
        "transcript_path": str(transcript_path),
        "transcript_length": len(transcript),
        "timestamp": datetime.now().isoformat(),
        "phases": phases,
        "errors": {
            "total": len(errors),
            "items": errors,
        },
        "dead_ends": {
            "total": len(dead_ends),
            "items": dead_ends,
        },
        "proposals": {
            "total": len(proposals),
            "items": proposals,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze agent transcript from integration eval")
    parser.add_argument("--transcript", required=True, help="Path to transcript.log")
    parser.add_argument("--output", "-o", help="Save analysis to JSON file")
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"Error: transcript not found: {transcript_path}", file=sys.stderr)
        sys.exit(1)

    analysis = analyze_transcript(transcript_path)

    # Print summary
    print(f"\n{'='*50}")
    print(f"TRANSCRIPT ANALYSIS")
    print(f"{'='*50}")
    print(f"Length: {analysis['transcript_length']} chars")
    print(f"Phases detected: {len(analysis['phases'])}")
    print(f"Errors found: {analysis['errors']['total']}")
    print(f"Dead ends found: {analysis['dead_ends']['total']}")
    print(f"Improvement proposals: {analysis['proposals']['total']}")

    if analysis["errors"]["items"]:
        print(f"\nErrors:")
        for e in analysis["errors"]["items"][:10]:
            print(f"  [{e['type']}] {e['message'][:80]}")

    if analysis["dead_ends"]["items"]:
        print(f"\nDead Ends:")
        for de in analysis["dead_ends"]["items"]:
            print(f"  - {de['description'][:80]}")

    if analysis["proposals"]["items"]:
        print(f"\nImprovement Proposals:")
        for p in analysis["proposals"]["items"]:
            print(f"  [{p.get('target_file', '?')}] {p.get('rationale', '')[:80]}")

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        print(f"\nAnalysis saved to {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify**

```bash
cd cli-anything-web-plugin && python scripts/analyze-transcript.py --help
```

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/scripts/analyze-transcript.py
git commit -m "feat: add analyze-transcript.py for Level 3 process analysis"
```

---

## Chunk 2: Eval Suite + Skill Updates

### Task 3: Create evals/integration-suite.json

**Files:**
- Create: `cli-anything-web-plugin/evals/integration-suite.json`

- [ ] **Step 1: Write integration-suite.json**

Copy the post-checks from the spec (the Suno example with 9 checks). Add a simpler Futbin eval too:

```json
{
  "version": "1.0",
  "evals": [
    {
      "id": "e2e-suno",
      "target_url": "https://suno.com",
      "timeout_minutes": 30,
      "post_checks": [
        {"id": "P1", "name": "CLI installed", "cmd": "which cli-web-suno", "expect": "exit_code_0"},
        {"id": "P2", "name": "Help works", "cmd": "cli-web-suno --help", "expect": "exit_code_0"},
        {"id": "P3", "name": "Auth login works", "cmd": "cli-web-suno auth login", "expect": "exit_code_0", "interactive": true},
        {"id": "P4", "name": "Auth status valid", "cmd": "cli-web-suno auth status", "expect": "contains:authenticated"},
        {"id": "P5", "name": "READ returns data", "cmd": "cli-web-suno --json songs list --limit 1", "expect": "valid_json"},
        {"id": "P6", "name": "WRITE succeeds", "cmd": "cli-web-suno --json songs generate --prompt 'test jazz' --wait", "expect": "valid_json_with_field:status", "timeout": 120},
        {"id": "P7", "name": "REPL mode works", "cmd": "echo help | cli-web-suno", "expect": "contains:commands"},
        {"id": "P8", "name": "Package importable", "cmd": "python -c \"import cli_web.suno\"", "expect": "exit_code_0"},
        {"id": "P9", "name": "Tests pass", "cmd": "cd suno/agent-harness && python -m pytest cli_web/suno/tests/ -v --tb=short", "expect": "contains:passed", "timeout": 120}
      ]
    },
    {
      "id": "e2e-futbin",
      "target_url": "https://www.futbin.com",
      "timeout_minutes": 30,
      "post_checks": [
        {"id": "P1", "name": "CLI installed", "cmd": "which cli-web-futbin", "expect": "exit_code_0"},
        {"id": "P2", "name": "Help works", "cmd": "cli-web-futbin --help", "expect": "exit_code_0"},
        {"id": "P3", "name": "READ returns data", "cmd": "cli-web-futbin --json players search --query Messi", "expect": "valid_json"},
        {"id": "P4", "name": "Package importable", "cmd": "python -c \"import cli_web.futbin\"", "expect": "exit_code_0"},
        {"id": "P5", "name": "Tests pass", "cmd": "cd futbin/agent-harness && python -m pytest cli_web/futbin/tests/ -v --tb=short", "expect": "contains:passed", "timeout": 120}
      ]
    }
  ]
}
```

- [ ] **Step 2: Verify valid JSON**

```bash
cd cli-anything-web-plugin && python -c "import json; d=json.load(open('evals/integration-suite.json')); print(f'{len(d[\"evals\"])} integration evals')"
```

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/evals/integration-suite.json
git commit -m "feat: add integration-suite.json with Suno and Futbin post-checks"
```

---

### Task 4: Update auto-optimize skill + command

**Files:**
- Modify: `cli-anything-web-plugin/skills/auto-optimize/SKILL.md`
- Modify: `cli-anything-web-plugin/commands/auto-optimize.md`

- [ ] **Step 1: Add Level 2 + Level 3 sections to SKILL.md**

Read the current file. At the end, add:

```markdown
---

## Level 2: Integration Evals

For deeper testing, run the full `/cli-anything-web` pipeline on a real site and
verify the generated CLI works end-to-end.

```bash
python scripts/run-integration-eval.py \
  --suite evals/integration-suite.json \
  --plugin-dir . \
  --output evals/integration/
```

This spawns a real Claude session with the plugin loaded, runs the full 8-phase
pipeline, then checks:
- CLI installs and `--help` works
- Auth login succeeds
- READ operations return real data
- WRITE operations succeed (the critical check)
- Tests pass

Use Level 2 after Level 1 achieves 100% — it validates that skill quality
translates to actual working CLIs.

---

## Level 3: Process Analysis

After a Level 2 run, analyze the transcript to find process improvements:

```bash
python scripts/analyze-transcript.py \
  --transcript evals/integration/suno/transcript.log \
  --output evals/integration/suno/analysis.json
```

This extracts:
- **Phase timing** — which phases take longest?
- **Errors** — what failed and how was it recovered?
- **Dead ends** — where did the agent waste time?
- **Improvement proposals** — specific HARNESS.md changes with rationale

Level 3 proposals feed back into the Level 1 optimization loop:
1. Run Level 2 integration eval
2. Run Level 3 analysis on the transcript
3. Read the proposals
4. Apply the best ones as Level 1 skill changes
5. Re-run Level 1 to verify the changes improve knowledge evals
6. Re-run Level 2 to verify the changes improve integration
```

- [ ] **Step 2: Update commands/auto-optimize.md**

Add `--level` flag documentation. Find the argument-hint and change to:
```
argument-hint: [--level 1|2|3] [--iterations N] [--target-score N]
```

Add to the Process section:

```markdown
## Levels

- `--level 1` (default): Fast skill knowledge evals (~3 min/iteration)
- `--level 2`: Full pipeline integration eval (~20-30 min/iteration)
- `--level 3`: Level 2 + transcript analysis (~30-40 min/iteration)

**Recommended flow:**
1. Run `--level 1` until 100% pass rate
2. Run `--level 2` to verify CLIs actually work
3. Run `--level 3` to find process improvements
4. Apply Level 3 proposals, re-run `--level 1` to verify
```

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/skills/auto-optimize/SKILL.md cli-anything-web-plugin/commands/auto-optimize.md
git commit -m "feat: add Level 2+3 documentation to auto-optimize skill and command"
```

---

### Task 5: Final verification

- [ ] **Step 1: Verify all scripts**

```bash
cd cli-anything-web-plugin && python scripts/run-integration-eval.py --help && python scripts/analyze-transcript.py --help && python scripts/run-eval.py --help && python scripts/grade_output.py --help
```

- [ ] **Step 2: Verify integration-suite.json**

```bash
cd cli-anything-web-plugin && python -c "import json; d=json.load(open('evals/integration-suite.json')); print(f'{len(d[\"evals\"])} evals, {sum(len(e[\"post_checks\"]) for e in d[\"evals\"])} post-checks')"
```
Expected: `2 evals, 14 post-checks`

- [ ] **Step 3: Run verify-plugin.sh**

```bash
cd cli-anything-web-plugin && bash verify-plugin.sh
```
Expected: 19/19 checks pass.
