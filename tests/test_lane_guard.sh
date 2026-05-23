#!/usr/bin/env bash
# Test harness for .claude/hooks/lane-guard.sh.
# The hook receives a JSON tool-call payload on stdin, reads $LANE from env,
# reads .agent-state/ownership.json, and prints JSON to stdout when a
# cross-lane edit is detected (warn mode). Always exits 0.

set -u

HOOK="${PWD}/.claude/hooks/lane-guard.sh"
FAILED=0

run_case() {
    local name="$1"
    local lane="$2"
    local file_path="$3"
    local expect_warning="$4"  # "yes" or "no"

    local stdin_json
    stdin_json=$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$file_path")

    local stdout
    stdout=$(printf '%s' "$stdin_json" | LANE="$lane" bash "$HOOK" 2>/dev/null)
    local rc=$?

    if [ "$rc" -ne 0 ]; then
        echo "FAIL [$name]: hook exited $rc (expected 0)"
        FAILED=1
        return
    fi

    local has_warning="no"
    if echo "$stdout" | grep -q "additionalContext"; then
        has_warning="yes"
    fi

    if [ "$has_warning" != "$expect_warning" ]; then
        echo "FAIL [$name]: expected warning=$expect_warning, got warning=$has_warning"
        echo "       stdout: $stdout"
        FAILED=1
    else
        echo "PASS [$name]"
    fi
}

# In-lane edit: backend editing app/main.py → no warning
run_case "in-lane backend" "backend" "$(pwd)/app/main.py" "no"

# Cross-lane edit: backend editing app/dashboard.py → warning
run_case "cross-lane backend→dashboard" "backend" "$(pwd)/app/dashboard.py" "yes"

# Cross-lane edit: docs editing app/main.py → warning
run_case "cross-lane docs→backend" "docs" "$(pwd)/app/main.py" "yes"

# In-lane edit: docs editing README.md → no warning
run_case "in-lane docs README" "docs" "$(pwd)/README.md" "no"

# In-lane edit: demo-data editing scripts/seed-archetype-mrs-v2.sh → no warning
run_case "in-lane demo-data seed" "demo-data" "$(pwd)/scripts/seed-archetype-mrs-v2.sh" "no"

# LANE empty (treated identically to unset by the hook's -z check) → no warning
run_case "LANE empty" "" "$(pwd)/app/main.py" "no"

# Cross-lane edit but lock exists → no warning
# Locks live under .git/agent-state-locks/ (truly shared across worktrees).
LOCK_DIR=$(cd "$(git rev-parse --git-common-dir)" && pwd)/agent-state-locks
mkdir -p "$LOCK_DIR"
echo "backend" > "$LOCK_DIR/dashboard.lock"
run_case "cross-lane with lock" "backend" "$(pwd)/app/dashboard.py" "no"
rm -f "$LOCK_DIR/dashboard.lock"

# Unowned file: editing pyproject.toml from backend → warning
run_case "unowned file" "backend" "$(pwd)/pyproject.toml" "yes"

if [ "$FAILED" -eq 0 ]; then
    echo "All tests passed."
    exit 0
else
    echo "Some tests failed."
    exit 1
fi
