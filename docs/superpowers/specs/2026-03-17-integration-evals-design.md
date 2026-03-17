# Integration Evals + Process Analysis Design

**Date:** 2026-03-17
**Status:** Approved
**Branch:** `playwright-migration`

---

## Goal

Add two evaluation levels on top of the existing skill knowledge evals:

- **Level 2 (Integration):** Run the full `/cli-anything-web` pipeline on a real
  site, then verify the generated CLI actually works (auth, list, create/generate).
- **Level 3 (Process Analysis):** Read the agent's full transcript, analyze time
  per phase, errors, dead ends, retries — then propose improvements to HARNESS.md
  and the pipeline itself.

---

## The Three Levels

| Level | What it tests | Time | Optimizes |
|-------|--------------|------|-----------|
| 1. Skill Knowledge | Does the agent know the methodology? | ~3 min | Skill .md instructions |
| 2. Integration | Does the generated CLI actually work? | ~20-30 min | Generated CLI quality |
| 3. Process Analysis | How did the agent build it? What went wrong? | Post-run | HARNESS.md phases, the pipeline itself |

---

## Level 2: Integration Evals

### How it works

```bash
python scripts/run-integration-eval.py \
  --target https://suno.com \
  --plugin-dir cli-anything-web-plugin/ \
  --output evals/integration/suno/ \
  --timeout 30
```

Flow:
1. Start a `claude` subprocess with `--plugin-dir` loaded
2. Send `/cli-anything-web <url>` as the prompt
3. Pipe ALL output to a transcript file (`transcript.log`)
4. Wait for completion (timeout configurable, default 30 min)
5. After completion, run post-checks against the generated CLI
6. Grade each post-check as PASS/FAIL
7. Save results to `integration-results.json`

### Post-Checks (binary assertions on the generated CLI)

```json
{
  "id": "e2e-suno",
  "type": "integration",
  "target_url": "https://suno.com",
  "app_name": "suno",
  "timeout_minutes": 30,
  "post_checks": [
    {
      "id": "P1",
      "name": "CLI installed",
      "cmd": "which cli-web-suno",
      "expect": "exit_code_0"
    },
    {
      "id": "P2",
      "name": "Help works",
      "cmd": "cli-web-suno --help",
      "expect": "exit_code_0"
    },
    {
      "id": "P3",
      "name": "Auth login works",
      "cmd": "cli-web-suno auth login",
      "expect": "exit_code_0",
      "interactive": true,
      "note": "Requires user to log in via browser"
    },
    {
      "id": "P4",
      "name": "Auth status valid",
      "cmd": "cli-web-suno auth status",
      "expect": "contains:authenticated"
    },
    {
      "id": "P5",
      "name": "READ operation returns real data",
      "cmd": "cli-web-suno --json songs list --limit 1",
      "expect": "valid_json"
    },
    {
      "id": "P6",
      "name": "WRITE operation succeeds",
      "cmd": "cli-web-suno --json songs generate --prompt 'test jazz piano' --wait",
      "expect": "valid_json_with_field:status",
      "timeout": 120,
      "note": "This is the most critical check — proves the CLI can actually DO things"
    },
    {
      "id": "P7",
      "name": "REPL mode works",
      "cmd": "echo 'help' | cli-web-suno",
      "expect": "contains:commands"
    },
    {
      "id": "P8",
      "name": "Package structure valid",
      "cmd": "python -c \"import cli_web.suno\"",
      "expect": "exit_code_0"
    },
    {
      "id": "P9",
      "name": "Tests pass",
      "cmd": "cd suno/agent-harness && python -m pytest cli_web/suno/tests/ -v --tb=short",
      "expect": "contains:passed",
      "timeout": 120
    }
  ]
}
```

### Output Structure

```
evals/integration/suno/
├── transcript.log          # Full agent output (every line of the session)
├── integration-results.json # Post-check results (PASS/FAIL per check)
├── timing.json             # Phase timing extracted from transcript
└── errors.json             # Errors encountered during the run
```

---

## Level 3: Process Analysis

### How it works

After a Level 2 run completes, analyze the transcript:

```bash
python scripts/analyze-transcript.py \
  --transcript evals/integration/suno/transcript.log \
  --output evals/integration/suno/analysis.json
```

### What it extracts from the transcript

#### 3a. Phase Timing

Parse the agent's progress table and timestamps to extract time per phase:

```json
{
  "phases": [
    {"phase": "1a", "name": "Reconnaissance", "start": "10:00:00", "end": "10:03:22", "duration_seconds": 202, "status": "completed"},
    {"phase": "1", "name": "Record", "start": "10:03:22", "end": "10:12:45", "duration_seconds": 563, "status": "completed"},
    {"phase": "2", "name": "Analyze", "start": "10:12:45", "end": "10:15:30", "duration_seconds": 165, "status": "completed"},
    {"phase": "3", "name": "Design", "start": "10:15:30", "end": "10:18:12", "duration_seconds": 162, "status": "completed"},
    {"phase": "4", "name": "Implement", "start": "10:18:12", "end": "10:28:55", "duration_seconds": 643, "status": "completed"},
    {"phase": "5", "name": "Plan Tests", "start": "10:28:55", "end": "10:30:20", "duration_seconds": 85, "status": "completed"},
    {"phase": "6", "name": "Test", "start": "10:30:20", "end": "10:35:10", "duration_seconds": 290, "status": "completed"},
    {"phase": "7", "name": "Document", "start": "10:35:10", "end": "10:36:45", "duration_seconds": 95, "status": "completed"},
    {"phase": "8", "name": "Publish", "start": "10:36:45", "end": "10:40:00", "duration_seconds": 195, "status": "completed"}
  ],
  "total_duration_seconds": 2400,
  "bottleneck_phase": "4 (Implement)",
  "fastest_phase": "5 (Plan Tests)"
}
```

#### 3b. Error Analysis

Parse the transcript for errors, retries, and dead ends:

```json
{
  "errors": [
    {
      "phase": "1",
      "timestamp": "10:05:33",
      "type": "command_error",
      "message": "playwright-cli: Unknown command: navigate",
      "resolution": "Agent corrected to 'goto'",
      "time_wasted_seconds": 15
    },
    {
      "phase": "4",
      "timestamp": "10:22:10",
      "type": "implementation_error",
      "message": "ModuleNotFoundError: No module named 'cli_web.suno.core.rpc'",
      "resolution": "Agent added missing __init__.py",
      "time_wasted_seconds": 45
    },
    {
      "phase": "6",
      "timestamp": "10:32:00",
      "type": "test_failure",
      "message": "test_auth_status FAILED: auth not configured",
      "resolution": "Agent ran auth login first, then re-ran tests",
      "time_wasted_seconds": 120
    }
  ],
  "total_errors": 3,
  "total_time_wasted_seconds": 180,
  "error_rate_by_phase": {
    "1": 1, "2": 0, "3": 0, "4": 1, "5": 0, "6": 1, "7": 0, "8": 0
  }
}
```

#### 3c. Dead End Detection

Identify times the agent went down unproductive paths:

```json
{
  "dead_ends": [
    {
      "phase": "1",
      "description": "Agent spent 8 minutes grepping JavaScript bundles instead of using the Create button",
      "time_wasted_seconds": 480,
      "should_have_done": "Take screenshot, click Create, capture the API call",
      "harness_fix": "Already added 'use the feature' guidance — verify it was followed"
    },
    {
      "phase": "4",
      "description": "Agent wrote all command files sequentially instead of dispatching parallel subagents",
      "time_wasted_seconds": 300,
      "should_have_done": "Dispatch 4 parallel agents for 4 command modules",
      "harness_fix": "Make parallel dispatch more prominent in Phase 4 instructions"
    }
  ]
}
```

#### 3d. Pattern Detection

Identify recurring patterns across multiple runs:

```json
{
  "patterns": [
    {
      "pattern": "auth_always_fails_first_time",
      "frequency": "3/3 runs",
      "description": "Agent always runs tests before configuring auth, gets failures, then goes back",
      "suggestion": "Move auth configuration to BEFORE test writing in Phase 6"
    },
    {
      "pattern": "recon_skipped",
      "frequency": "2/3 runs",
      "description": "Agent skips Phase 1a reconnaissance even for unfamiliar sites",
      "suggestion": "Make recon mandatory for first run, or auto-detect if site is unfamiliar"
    },
    {
      "pattern": "parallel_not_used",
      "frequency": "3/3 runs",
      "description": "Agent never dispatches parallel subagents for Phase 4 despite HARNESS guidance",
      "suggestion": "Add explicit 'dispatch N agents NOW' instruction, not just 'you can parallelize'"
    }
  ]
}
```

#### 3e. Improvement Proposals

Based on all analysis, generate specific HARNESS.md improvement proposals:

```json
{
  "proposals": [
    {
      "target_file": "HARNESS.md",
      "section": "Phase 4 — Implement",
      "current_text": "Then (parallel subagents): Dispatch one agent per command module",
      "proposed_text": "MANDATORY: Dispatch parallel subagents NOW for each command module. Do NOT implement sequentially.",
      "rationale": "Agent never parallelizes because the instruction is permissive ('you can') not imperative ('you must')",
      "expected_impact": "Save ~5 minutes per run (Phase 4: 10min → 5min)"
    },
    {
      "target_file": "HARNESS.md",
      "section": "Phase 6 — Test",
      "current_text": "Before writing or running any live test, you MUST ensure authentication is working",
      "proposed_text": "STEP 0 (before writing ANY test code): Run auth login and verify auth status. Do NOT proceed to test code until auth shows valid.",
      "rationale": "Agent writes tests first, runs them, sees auth failures, THEN configures auth — wasting 2 minutes every time",
      "expected_impact": "Eliminate 2-minute auth-retry cycle in Phase 6"
    }
  ]
}
```

---

## New Files

| File | Purpose |
|------|---------|
| `scripts/run-integration-eval.py` | Run full pipeline + post-checks |
| `scripts/analyze-transcript.py` | Parse transcript → timing, errors, dead ends, proposals |
| `evals/integration-suite.json` | Integration eval definitions (target URLs + post-checks) |

## Updated Files

| File | Change |
|------|--------|
| `evals/eval-suite.json` | Add `"type": "knowledge"` to existing evals for clarity |
| `skills/auto-optimize/SKILL.md` | Add Level 2 + Level 3 sections |
| `commands/auto-optimize.md` | Add `--level 2` and `--level 3` flags |

---

## The Auto-Optimize Loop with All 3 Levels

```
/cli-anything-web:auto-optimize --level 1
  → Fast skill knowledge evals (current behavior)
  → Optimizes: skill .md instructions
  → 3 min per iteration

/cli-anything-web:auto-optimize --level 2
  → Full pipeline integration eval
  → Runs /cli-anything-web on a real site
  → Post-checks on generated CLI
  → 20-30 min per iteration
  → Optimizes: HARNESS.md phases, command instructions

/cli-anything-web:auto-optimize --level 3
  → Level 2 + transcript analysis
  → Reads the full agent transcript
  → Extracts: timing, errors, dead ends, patterns
  → Generates specific HARNESS.md improvement proposals
  → 30-40 min per iteration (includes analysis time)
  → Optimizes: the pipeline itself
```

---

## What Does NOT Change

- Level 1 eval system (already built)
- grade_output.py, run-eval.py (already built)
- eval-suite.json format (34 knowledge assertions stay)
- 5 skills, 8 commands, 8 references (structure)
- HARNESS.md (structure — content gets optimized by the system)

---

## Out of Scope

- Automated browser login during integration evals (user must log in manually)
- Running integration evals in CI/CD (requires interactive browser)
- Multi-site parallel integration evals (one site at a time)
