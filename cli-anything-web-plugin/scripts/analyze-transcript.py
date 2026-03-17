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
