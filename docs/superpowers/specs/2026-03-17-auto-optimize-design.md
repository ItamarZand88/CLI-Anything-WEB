# Auto-Optimize System Design

**Date:** 2026-03-17
**Status:** Approved
**Branch:** `playwright-migration` (building on V2)

---

## Goal

Create an autonomous skill optimization loop inspired by Andrej Karpathy's
autoresearch methodology. The system automatically improves plugin skills by:
making ONE change → running evals → measuring pass rate → keeping improvements,
discarding regressions. Runs indefinitely until interrupted.

---

## Three Core Ingredients (from autoresearch)

1. **Objective metric:** Binary assertion pass rate (X/Y assertions passed)
2. **Measurement tool:** `scripts/run-eval.py` using `claude -p` subprocess
3. **Something to change:** Skill instruction files (.md)

---

## Architecture

### The Loop (adapted from autoresearch `program.md`)

```
SETUP:
  git checkout -b autoresearch/<tag>
  Run baseline evals → establish baseline score
  Log baseline to results.tsv

LOOP FOREVER:
  1. Read current skills + results.tsv history
  2. Identify weakest assertion(s) — which ones fail most?
  3. Propose ONE targeted change to ONE skill file
  4. git commit the change
  5. Run eval suite: scripts/run-eval.py
     → Spawns 3 agents per test case (noise handling)
     → Grades each output against binary assertions
     → Majority vote per assertion (2/3 = pass)
  6. Calculate new pass rate
  7. Decision:
     - If pass_rate > baseline: KEEP commit, update baseline
     - If pass_rate <= baseline: git reset --hard HEAD~1, DISCARD
  8. Log to results.tsv
  9. GOTO step 1

NEVER pause to ask the human. Run until interrupted.
```

### Key Rules (from autoresearch, adapted)

- **ONE change per iteration** — isolate what works
- **Binary assertions only** — pass/fail, no scales or subjective scores
- **Run 3x per eval** — AI is noisy, majority vote smooths variance
- **Simplicity criterion** — if equal score with simpler instructions, prefer simpler.
  Removing something and keeping the score is a WIN (simplification)
- **Never give up** — if stuck, try radical changes, combine near-misses
- **Log everything** — results.tsv is the research artifact

---

## New Files

### 1. `skills/auto-optimize/SKILL.md`

The methodology skill — teaches the agent the optimization loop.

```yaml
---
name: auto-optimize
description: >
  Autonomous skill optimization loop. Trigger when: "optimize skills",
  "improve pass rate", "auto-research", "autoloop", "run optimization",
  "make skills better". Iteratively modifies skill files, runs evals,
  keeps improvements, discards regressions. Runs indefinitely.
version: 0.1.0
---
```

Body contains:
- The complete loop pseudocode (from Architecture section above)
- How to identify weak assertions (parse results.tsv, find most-failed)
- Mutation strategies: clarify instructions, add examples, simplify wording,
  add constraints, remove unnecessary content, reorder sections
- Decision rule: `new_pass_rate > baseline → KEEP, else DISCARD`
- How to run evals: `python scripts/run-eval.py --evals evals/eval-suite.json`
- How to log results: append to `evals/results.tsv`
- Simplicity criterion: prefer deletions, shorter instructions, fewer files
- When to try radical changes (3+ consecutive discards)

### 2. `scripts/run-eval.py`

Automated eval runner. Uses `claude -p` (Claude Code programmatic mode) to
spawn agents with skills loaded.

```python
"""
Auto-optimize eval runner.

Usage:
  python run-eval.py --evals evals/eval-suite.json --skill-dir skills/
  python run-eval.py --evals evals/eval-suite.json --runs 3 --output results.json
"""
```

Flow:
1. Read `eval-suite.json` — list of test prompts + binary assertions
2. For each eval:
   a. Build the prompt (include skill content inline OR use `--skill-dir`)
   b. Run `claude -p "prompt"` as subprocess, capture output
   c. Repeat N times (default 3) for noise handling
3. Grade each output:
   a. For each assertion, spawn a grader `claude -p` that returns PASS/FAIL
   b. Majority vote across N runs
4. Output:
   - `results.json` with per-assertion pass/fail and overall score
   - Print summary: `Score: 34/36 (94.4%)`

Implementation notes:
- Uses `subprocess.run(["claude", "-p", prompt], capture_output=True)`
- Grader prompt: "Given this output, does it satisfy this assertion? Answer PASS or FAIL only."
- Timeout per agent: 120 seconds
- If agent crashes or times out: count as FAIL for all assertions

### 3. `scripts/grade_output.py`

Standalone grader for a single eval output.

```python
"""
Grade a single eval output against binary assertions.

Usage:
  python grade_output.py --output response.md --assertions assertions.json
  python grade_output.py --output response.md --assertions assertions.json --grader claude
"""
```

Two grading modes:
- **Programmatic** (fast): regex/string matching for simple assertions
  (e.g., "Contains playwright-cli commands" → grep for `npx @playwright/cli`)
- **LLM grader** (thorough): spawn `claude -p` with grading prompt for
  subjective assertions (e.g., "Follows structured 5-step flow")

### 4. `evals/eval-suite.json`

Expanded eval definitions covering all 4 skills. Format:

```json
{
  "version": "1.0",
  "runs_per_eval": 3,
  "evals": [
    {
      "id": "recon-suno",
      "name": "Suno.com reconnaissance",
      "prompt": "Plan reconnaissance for https://suno.com. Include exact playwright-cli commands for all 5 recon steps, framework detection, protection assessment, and a RECON-REPORT.md with Expected/Confirmed columns.",
      "skills_to_load": ["web-reconnaissance"],
      "assertions": [
        {"id": "A1", "text": "Uses npx @playwright/cli commands (not MCP, not curl)", "check": "programmatic", "pattern": "npx @playwright/cli"},
        {"id": "A2", "text": "Follows structured 5-step recon flow", "check": "llm"},
        {"id": "A3", "text": "Produces RECON-REPORT.md with Expected/Confirmed columns", "check": "llm"},
        {"id": "A4", "text": "Has specific eval commands for framework detection", "check": "programmatic", "pattern": "eval.*__NEXT_DATA__|eval.*__NUXT__"},
        {"id": "A5", "text": "Mentions Force SPA Navigation trick by name and explains why", "check": "programmatic", "pattern": "(?i)force.*spa.*navigation"},
        {"id": "A6", "text": "Includes protection detection eval script", "check": "programmatic", "pattern": "cloudflare.*captcha|captcha.*cloudflare"},
        {"id": "A7", "text": "Checks robots.txt", "check": "programmatic", "pattern": "robots\\.txt"},
        {"id": "A8", "text": "Recommends specific capture strategy with rationale", "check": "llm"},
        {"id": "A9", "text": "Identifies specific API endpoints", "check": "llm"},
        {"id": "A10", "text": "Maps strategy to CLI generation impact", "check": "llm"},
        {"id": "A11", "text": "Flags warnings or risks", "check": "llm"},
        {"id": "A12", "text": "Uses API-first priority chain", "check": "llm"}
      ]
    },
    {
      "id": "recon-nextjs",
      "name": "Next.js SSR site reconnaissance",
      "prompt": "Plan reconnaissance for https://vercel.com/dashboard (a Next.js app). Include __NEXT_DATA__ extraction, Force SPA Navigation trick, and SSR+API hybrid strategy.",
      "skills_to_load": ["web-reconnaissance", "methodology"],
      "assertions": [
        {"id": "A1", "text": "Uses playwright-cli commands", "check": "programmatic", "pattern": "npx @playwright/cli"},
        {"id": "A2", "text": "Detects __NEXT_DATA__ with eval command", "check": "programmatic", "pattern": "__NEXT_DATA__"},
        {"id": "A3", "text": "Explains Force SPA Navigation trick", "check": "programmatic", "pattern": "(?i)force.*spa|spa.*navigation.*trick"},
        {"id": "A4", "text": "Recommends SSR+API hybrid strategy", "check": "programmatic", "pattern": "(?i)ssr.*api|hybrid"},
        {"id": "A5", "text": "Produces structured RECON-REPORT.md", "check": "llm"},
        {"id": "A6", "text": "Identifies /_next/data/ endpoints", "check": "programmatic", "pattern": "_next/data"}
      ]
    },
    {
      "id": "recon-protected",
      "name": "Protected site reconnaissance (Futbin)",
      "prompt": "Plan reconnaissance for https://www.futbin.com. Check for Cloudflare, rate limits, and recommend a capture strategy considering protections.",
      "skills_to_load": ["web-reconnaissance"],
      "assertions": [
        {"id": "A1", "text": "Uses playwright-cli commands", "check": "programmatic", "pattern": "npx @playwright/cli"},
        {"id": "A2", "text": "Includes protection detection eval script", "check": "programmatic", "pattern": "cloudflare|captcha|perimeterx"},
        {"id": "A3", "text": "Checks robots.txt", "check": "programmatic", "pattern": "robots\\.txt"},
        {"id": "A4", "text": "Identifies rate limiting signals", "check": "programmatic", "pattern": "(?i)rate.limit|429|retry-after"},
        {"id": "A5", "text": "Recommends Protected-manual or SSR+API strategy", "check": "llm"},
        {"id": "A6", "text": "Flags protection risks and mitigations", "check": "llm"}
      ]
    },
    {
      "id": "pipeline-suno",
      "name": "Full pipeline planning for Suno",
      "prompt": "Plan the complete implementation of cli-web-suno for https://suno.com. Cover all 8 phases including reconnaissance, traffic capture, CLI design, parallel implementation, test planning, and end-user smoke test.",
      "skills_to_load": ["methodology", "testing", "standards"],
      "assertions": [
        {"id": "A1", "text": "References 8-phase pipeline", "check": "programmatic", "pattern": "(?i)8.phase|phase.*[1-8]"},
        {"id": "A2", "text": "Uses playwright-cli for capture", "check": "programmatic", "pattern": "npx @playwright/cli|playwright-cli"},
        {"id": "A3", "text": "Identifies auth mechanism", "check": "llm"},
        {"id": "A4", "text": "Proposes parallel subagent dispatch for Phase 4", "check": "programmatic", "pattern": "(?i)parallel|subagent|concurrent"},
        {"id": "A5", "text": "Includes TEST.md two-part structure", "check": "programmatic", "pattern": "(?i)test.*md.*part|part.*1.*part.*2"},
        {"id": "A6", "text": "Tests FAIL without auth (not skip)", "check": "programmatic", "pattern": "(?i)fail.*not.*skip|pytest\\.fail"},
        {"id": "A7", "text": "Has end-user smoke test with WRITE operation", "check": "programmatic", "pattern": "(?i)smoke.*test|generate.*--wait|create.*smoke"},
        {"id": "A8", "text": "Mentions content generation download lifecycle", "check": "programmatic", "pattern": "(?i)poll|download|--output|--wait"},
        {"id": "A9", "text": "Mentions CAPTCHA handling", "check": "programmatic", "pattern": "(?i)captcha|pause.*prompt"},
        {"id": "A10", "text": "Maps strategy to CLI generation impact", "check": "llm"}
      ]
    }
  ]
}
```

Total: 4 evals, 34 assertions. Max score: 34/34.

### 5. `evals/results.tsv`

Append-only log (not committed to git):

```
commit	score	max_score	pass_rate	status	description	timestamp
a1b2c3d	34	34	100.0%	baseline	initial state	2026-03-17T10:00:00
b2c3d4e	32	34	94.1%	discard	simplified recon step 1.3	2026-03-17T10:15:00
c3d4e5f	34	34	100.0%	keep	added prediction emphasis	2026-03-17T10:30:00
```

---

## Updated Files

### `verify-plugin.sh`

Add `auto-optimize` to the skills loop:
```bash
for skill in methodology testing standards web-reconnaissance auto-optimize; do
```

### `.gitignore`

Add:
```
evals/results.tsv
```

### `skills/methodology/SKILL.md`

Add to companion skills table:
```
| **auto-optimize** | Autonomous skill optimization — run evals, improve instructions, keep winners |
```

---

## Command: `/cli-anything-web:auto-optimize`

Optionally, add a command file `commands/auto-optimize.md` that invokes the skill:

```yaml
---
name: cli-anything-web:auto-optimize
description: Run autonomous skill optimization loop. Modifies skills, runs evals, keeps improvements.
argument-hint: [--iterations N] [--target-score N]
allowed-tools: Bash(*), Read, Write, Edit
---
```

This gives users `/cli-anything-web:auto-optimize` to start the loop.

---

## What Does NOT Change

- 8-phase pipeline structure
- All existing skills (content — only their instructions get optimized)
- Generated CLI structure
- All reference docs (structure — content may be refined by the optimizer)
- parse-trace.py, repl_skin.py, verify-plugin.sh (beyond adding the new skill check)

---

## Out of Scope

- Optimizing generated CLI code (only skill instructions are optimized)
- Changing eval definitions during the loop (evals are fixed like autoresearch's `prepare.py`)
- Multi-variable optimization (ONE change per iteration)
