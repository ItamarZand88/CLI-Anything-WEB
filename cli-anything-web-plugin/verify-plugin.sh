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

# CLI-ANYTHING-WEB.md exists
check "CLI-ANYTHING-WEB.md exists" "$([ -f "$SCRIPT_DIR/CLI-ANYTHING-WEB.md" ] && echo true || echo false)"

# All 6 command files
for cmd in web-harness record refine test validate list; do
    check "commands/$cmd.md exists" "$([ -f "$SCRIPT_DIR/commands/$cmd.md" ] && echo true || echo false)"
done

# scripts/repl_skin.py
check "scripts/repl_skin.py exists" "$([ -f "$SCRIPT_DIR/scripts/repl_skin.py" ] && echo true || echo false)"

# scripts/setup-web-harness.sh executable
if [ -f "$SCRIPT_DIR/scripts/setup-web-harness.sh" ] && [ -x "$SCRIPT_DIR/scripts/setup-web-harness.sh" ]; then
    check "scripts/setup-web-harness.sh is executable" "true"
else
    check "scripts/setup-web-harness.sh is executable" "false"
fi

# .mcp.json valid JSON
if (cd "$SCRIPT_DIR" && python -c "import json; json.load(open('.mcp.json'))") 2>/dev/null; then
    check ".mcp.json is valid JSON" "true"
else
    check ".mcp.json is valid JSON" "false"
fi

# skills/web-harness-methodology/SKILL.md
check "skills/web-harness-methodology/SKILL.md exists" \
    "$([ -f "$SCRIPT_DIR/skills/web-harness-methodology/SKILL.md" ] && echo true || echo false)"

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
