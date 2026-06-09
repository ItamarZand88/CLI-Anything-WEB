#!/usr/bin/env bash
# Run unit tests for every generated CLI in the repo.
# CLIs are discovered dynamically: any <dir>/agent-harness/cli_web/<pkg>/tests/test_core.py
# Usage: bash scripts/test-all.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0
FOUND=0
FAILED_CLIS=()

for test_file in "$REPO_ROOT"/*/agent-harness/cli_web/*/tests/test_core.py; do
  [ -f "$test_file" ] || continue
  FOUND=$((FOUND + 1))

  # <repo>/<dir>/agent-harness/cli_web/<pkg>/tests/test_core.py
  rel="${test_file#"$REPO_ROOT"/}"
  dir="${rel%%/*}"

  echo ""
  echo "────────────────────────────────────────"
  echo "  cli-web-$dir"
  echo "────────────────────────────────────────"

  if python -m pytest "$test_file" -v --tb=short; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    FAILED_CLIS+=("cli-web-$dir")
  fi
done

if [ "$FOUND" -eq 0 ]; then
  echo "ERROR: no test_core.py files found under */agent-harness/cli_web/*/tests/" >&2
  exit 1
fi

echo ""
echo "════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed (of $FOUND CLIs)"
if [ ${#FAILED_CLIS[@]} -gt 0 ]; then
  echo "  Failed: ${FAILED_CLIS[*]}"
fi
echo "════════════════════════════════════════"

exit $FAIL
