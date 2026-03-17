---
name: cli-anything-web:auto-optimize
description: Run autonomous skill optimization loop. Iteratively modifies skills, runs evals, keeps improvements, discards regressions. Runs until interrupted.
argument-hint: [--iterations N] [--target-score N]
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

3. **Stopping conditions:**
   - User interrupts (Ctrl+C)
   - `--iterations N` reached (if specified)
   - `--target-score N` reached (if specified)
   - All assertions pass consistently (100% across 3 runs)
