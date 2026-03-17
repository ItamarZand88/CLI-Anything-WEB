---
name: cli-anything-web:auto-optimize
description: Run autonomous skill optimization loop. Iteratively modifies skills, runs evals, keeps improvements, discards regressions. Runs until interrupted.
argument-hint: [--level 1|2|3] [--iterations N] [--target-score N]
allowed-tools: Bash(*), Read, Write, Edit
---

## Read the auto-optimize skill first

@${CLAUDE_PLUGIN_ROOT}/skills/auto-optimize/SKILL.md

# CLI-Anything-Web: Auto-Optimize Skills

## Process

Follow the auto-optimize skill's loop exactly:

1. **Setup:**
   - Create branch: `git checkout -b autoresearch/$(date +%Y%m%d)`
   - Run baseline: `cd ${CLAUDE_PLUGIN_ROOT} && python scripts/run-eval.py --evals evals/eval-suite.json --skill-dir skills/ --output evals/baseline.json`
   - Extract baseline score from output
   - Initialize `evals/results.tsv` with header + baseline row
   - Show baseline to user, confirm before starting loop

2. **Loop (repeat until interrupted):**
   - Read results.tsv — find weakest assertions
   - Propose ONE change to ONE skill file
   - `git commit -m "auto-optimize: <description>"`
   - Run eval suite: `cd ${CLAUDE_PLUGIN_ROOT} && python scripts/run-eval.py --evals evals/eval-suite.json --skill-dir skills/`
   - If score improved: KEEP commit, log as "keep"
   - If not: `git reset --hard HEAD~1`, log as "discard"
   - Append to results.tsv
   - Continue immediately — do NOT pause to ask the user

## Levels

- `--level 1` (default): Fast skill knowledge evals (~3 min/iteration)
  - Runs: `python scripts/run-eval.py --evals evals/eval-suite.json`
  - Optimizes: skill .md instructions

- `--level 2`: Full pipeline integration eval (~20-30 min/iteration)
  - Runs: `python scripts/run-integration-eval.py --suite evals/integration-suite.json`
  - Tests: does the generated CLI actually work?
  - Optimizes: HARNESS.md phases, command instructions

- `--level 3`: Level 2 + transcript analysis (~30-40 min/iteration)
  - Runs: Level 2 + `python scripts/analyze-transcript.py`
  - Analyzes: time per phase, errors, dead ends, patterns
  - Generates: specific HARNESS.md improvement proposals
  - Optimizes: the pipeline itself

**Recommended flow:**
1. Run `--level 1` until 100% pass rate
2. Run `--level 2` to verify CLIs actually work
3. Run `--level 3` to find process improvements
4. Apply Level 3 proposals, re-run `--level 1` to verify

3. **Stopping conditions:**
   - User interrupts (Ctrl+C)
   - `--iterations N` reached (if specified)
   - `--target-score N` reached (if specified)
   - All assertions pass consistently (100% across 3 runs)
