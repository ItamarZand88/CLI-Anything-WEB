#!/usr/bin/env bash
# verify-plugin.sh — Validate cli-anything-web-plugin structure
#
# Reports ALL checks (no fail-fast). Prints [PASS] or [FAIL] per check.
# Exits 0 if all pass, 1 if any fail.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASS=0
FAIL=0

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" = "true" ]; then
        echo "[PASS] $desc"
        ((PASS++))
    else
        echo "[FAIL] $desc"
        ((FAIL++))
    fi
}

# plugin.json valid JSON
if (cd "$SCRIPT_DIR" && python -c "import json; json.load(open('.claude-plugin/plugin.json'))") 2>/dev/null; then
    check ".claude-plugin/plugin.json is valid JSON" "true"
else
    check ".claude-plugin/plugin.json is valid JSON" "false"
fi

# HARNESS.md exists
check "HARNESS.md exists" "$([ -f "$SCRIPT_DIR/HARNESS.md" ] && echo true || echo false)"

# All 6 command files
for cmd in cli-anything-web record refine test validate list; do
    check "commands/$cmd.md exists" "$([ -f "$SCRIPT_DIR/commands/$cmd.md" ] && echo true || echo false)"
done

# scripts/repl_skin.py
check "scripts/repl_skin.py exists" "$([ -f "$SCRIPT_DIR/scripts/repl_skin.py" ] && echo true || echo false)"

# scripts/parse-trace.py
check "scripts/parse-trace.py exists" "$([ -f "$SCRIPT_DIR/scripts/parse-trace.py" ] && echo true || echo false)"

# Pipeline automation scripts
for script in scaffold-cli.py validate-checklist.py generate-test-docs.py smoke-test.py run-pipeline.py; do
    check "scripts/$script exists" "$([ -f "$SCRIPT_DIR/scripts/$script" ] && echo true || echo false)"
done

# Shared script utility modules
for mod in plugin_paths.py traffic_utils.py state_utils.py; do
    check "scripts/$mod exists" "$([ -f "$SCRIPT_DIR/scripts/$mod" ] && echo true || echo false)"
done

# Script tests
check "scripts/tests/ exists" "$([ -d "$SCRIPT_DIR/scripts/tests" ] && echo true || echo false)"

# scripts/setup.sh executable
if [ -f "$SCRIPT_DIR/scripts/setup.sh" ] && [ -x "$SCRIPT_DIR/scripts/setup.sh" ]; then
    check "scripts/setup.sh is executable" "true"
else
    check "scripts/setup.sh is executable" "false"
fi

# .mcp.json valid JSON
if (cd "$SCRIPT_DIR" && python -c "import json; json.load(open('.mcp.json'))") 2>/dev/null; then
    check ".mcp.json is valid JSON" "true"
else
    check ".mcp.json is valid JSON" "false"
fi

# All 4 skills
for skill in methodology capture testing standards; do
    check "skills/$skill/SKILL.md exists" \
        "$([ -f "$SCRIPT_DIR/skills/$skill/SKILL.md" ] && echo true || echo false)"
done

# PUBLISHING.md
check "PUBLISHING.md exists" "$([ -f "$SCRIPT_DIR/PUBLISHING.md" ] && echo true || echo false)"

# README.md
check "README.md exists" "$([ -f "$SCRIPT_DIR/README.md" ] && echo true || echo false)"

# Summary
TOTAL=$((PASS + FAIL))
echo ""
echo "$PASS/$TOTAL checks passed"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
