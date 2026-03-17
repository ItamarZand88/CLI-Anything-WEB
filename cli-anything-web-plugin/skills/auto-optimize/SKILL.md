---
name: auto-optimize
description: >
  Autonomous skill optimization loop inspired by autoresearch. Iteratively modifies
  skill instruction files, runs eval suite, keeps improvements, discards regressions.
  Trigger phrases: "optimize skills", "improve pass rate", "auto-research", "autoloop",
  "run optimization", "make skills better", "self-improve".
version: 0.1.0
---

# Auto-Optimize Skill

## Overview

Auto-optimize is an autonomous skill optimization loop inspired by Andrej Karpathy's
autoresearch methodology. It iteratively modifies skill instruction files (.md), runs
the eval suite to measure binary assertion pass rate, keeps changes that improve the
score, and discards changes that regress. The loop runs indefinitely until interrupted,
producing a continuously improving set of skill instructions backed by objective metrics.

## The Three Ingredients

Every optimization loop needs exactly three things:

1. **Objective metric** — Binary assertion pass rate (X/Y assertions passed). No scales,
   no subjective scores. Each assertion is PASS or FAIL.
2. **Measurement tool** — `scripts/run-eval.py` spawns Claude agents via `claude -p`,
   runs them against test prompts, and grades outputs against binary assertions. Runs
   each eval 3 times and uses majority vote to smooth AI noise.
3. **Something to change** — Skill instruction files (.md) under `skills/` and
   reference documents under `references/`. These are the "knobs" the optimizer turns.

## Setup Phase

Before starting the optimization loop:

1. **Create a branch** — `git checkout -b autoresearch/$(date +%Y%m%d)` to isolate
   optimization work from the main branch.
2. **Run baseline evals** — Execute the full eval suite to establish the starting score:
   ```
   python scripts/run-eval.py --evals evals/eval-suite.json --skill-dir skills/ --output evals/baseline.json
   ```
3. **Initialize results.tsv** — Create `evals/results.tsv` with the header row and
   baseline entry:
   ```
   commit	score	max_score	pass_rate	status	description	timestamp
   <hash>	<score>	34	<rate>	baseline	initial state	<timestamp>
   ```

## The Loop

```
LOOP FOREVER:
  1. Read results.tsv — identify weakest assertions (most failed)
  2. Read the skill file responsible for that assertion
  3. Propose ONE targeted change (clarify, add example, simplify, etc.)
  4. git commit the change
  5. Run: python scripts/run-eval.py --evals evals/eval-suite.json --skill-dir skills/
  6. Extract score from output
  7. If score > baseline: KEEP commit, update baseline
  8. If score <= baseline: git reset --hard HEAD~1, DISCARD
  9. Append to evals/results.tsv
  10. NEVER stop — loop until interrupted
```

Key rules:
- **ONE change per iteration** — isolate what works from what doesn't
- **Run 3x per eval** — AI is noisy, majority vote smooths variance
- **Never pause to ask the human** — run autonomously until interrupted
- **Log everything** — results.tsv is the research artifact

## Mutation Strategies

Six types of changes to try, in rough order of frequency:

1. **Clarify wording** — Make ambiguous instructions precise. Replace vague terms with
   specific ones. Add "always" or "never" qualifiers where appropriate.
2. **Add concrete examples** — Show exactly what good output looks like. Include command
   snippets, expected file structures, or output samples.
3. **Simplify (remove unnecessary words)** — Delete filler, hedge words, redundant
   explanations. Shorter instructions that score the same are better.
4. **Add constraints** — Add explicit rules ("MUST include X", "NEVER do Y") that
   address specific assertion failures.
5. **Remove redundant content** — If two sections say the same thing, remove one.
   Deduplication improves clarity without losing information.
6. **Reorder sections for emphasis** — Move critical instructions earlier. Put the most
   important rules first where the agent is most likely to follow them.

## Decision Rule

Simple and binary:

```
new_pass_rate > baseline → KEEP the commit, update baseline
new_pass_rate <= baseline → DISCARD the commit (git reset --hard HEAD~1)
```

No exceptions. No "close enough". The metric decides.

## Simplicity Criterion

Equal score with simpler instructions = WIN. Specifically:

- Removing text and keeping the same score is a WIN (simplification)
- Shorter skill files that maintain pass rate are preferred
- Fewer files that maintain pass rate are preferred
- If you can delete a paragraph and the score doesn't drop, delete it

The goal is the simplest possible instructions that maximize the pass rate.

## Radical Changes

After **3 or more consecutive discards**, the incremental approach is stuck. Try
something radical:

- Restructure a whole section (rewrite from scratch with a different angle)
- Combine two related sections into one
- Split a dense section into multiple focused sections
- Completely rewrite a paragraph using a different explanation strategy
- Move content between skill files (e.g., from methodology to standards)
- Add a completely new section that addresses the failing assertions differently

Radical changes have lower success probability but can break through plateaus.

## results.tsv Format

Append-only log file tracking every optimization iteration:

```
commit	score	max_score	pass_rate	status	description	timestamp
```

Fields:
- `commit` — short git hash of the change
- `score` — number of assertions passed (e.g., 32)
- `max_score` — total assertions (e.g., 34)
- `pass_rate` — percentage (e.g., 94.1%)
- `status` — one of: `baseline`, `keep`, `discard`
- `description` — brief description of the change attempted
- `timestamp` — ISO 8601 timestamp

This file is NOT committed to git (listed in .gitignore). It is the raw research log.

## What You Can Change

- Any `.md` file under `skills/` — skill instruction files
- Any `.md` file under `references/` — reference documents

These are the optimization targets. Every iteration modifies exactly one of these files.

## What You Cannot Change

- `evals/eval-suite.json` — the eval definitions are fixed, like autoresearch's
  `prepare.py`. Changing the test while optimizing the code is cheating.
- `scripts/*.py` — the measurement tools must remain constant for results to be
  comparable across iterations.

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
pipeline, then checks: CLI installs, auth works, READ returns data, WRITE succeeds,
tests pass.

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
