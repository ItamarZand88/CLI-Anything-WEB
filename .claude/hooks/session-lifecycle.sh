#!/bin/bash
# Hook: SessionStart / SessionEnd — Log session boundaries with context
#
# On SessionStart: logs session metadata, git state, environment
# On SessionEnd:   logs session summary with duration, operation counts, files touched
#
# Called with $1 = "start" or "end" (set via hook command args)

set -e

INPUT=$(cat)
ACTION="${1:-start}"

# --- Configuration ---
LOG_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/logs"
PROJECT_NAME=$(basename "${CLAUDE_PROJECT_DIR:-$(pwd)}")
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // ""')
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/session-${DATE}.jsonl"
SESSIONS_INDEX="$LOG_DIR/sessions.jsonl"

mkdir -p "$LOG_DIR"

if [[ "$ACTION" == "start" ]]; then
    # --- Collect environment context ---
    GIT_BRANCH=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git branch --show-current 2>/dev/null || echo "unknown")
    GIT_DIRTY=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git diff --stat --quiet 2>/dev/null && echo "clean" || echo "dirty")
    GIT_LAST_COMMIT=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git log -1 --format="%h %s" 2>/dev/null || echo "unknown")
    GIT_UNCOMMITTED=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
    GIT_UNTRACKED=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')

    PERMISSION_MODE=$(echo "$INPUT" | jq -r '.permission_mode // "unknown"')
    CWD=$(echo "$INPUT" | jq -r '.cwd // ""')

    # Count existing files for context
    TOTAL_FILES=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git ls-files 2>/dev/null | wc -l | tr -d ' ')

    # Cache git context for session-logger.sh to reuse
    GIT_CACHE_FILE="$LOG_DIR/.git-context-${SESSION_ID}"
    echo "$GIT_BRANCH" > "$GIT_CACHE_FILE"
    echo "$GIT_DIRTY" >> "$GIT_CACHE_FILE"

    # Save session start timestamp for duration calculation
    echo "$TIMESTAMP" > "$LOG_DIR/.session-start-${SESSION_ID}"

    # --- Log session start ---
    LOG_ENTRY=$(jq -n \
        --arg timestamp "$TIMESTAMP" \
        --arg session_id "$SESSION_ID" \
        --arg project "$PROJECT_NAME" \
        --arg event "session_start" \
        --arg git_branch "$GIT_BRANCH" \
        --arg git_dirty "$GIT_DIRTY" \
        --arg git_last_commit "$GIT_LAST_COMMIT" \
        --argjson git_uncommitted "$GIT_UNCOMMITTED" \
        --argjson git_untracked "$GIT_UNTRACKED" \
        --arg permission_mode "$PERMISSION_MODE" \
        --arg cwd "$CWD" \
        --argjson total_files "$TOTAL_FILES" \
        '{
            timestamp: $timestamp,
            session_id: $session_id,
            project: $project,
            event: $event,
            environment: {
                permission_mode: $permission_mode,
                cwd: $cwd,
                total_tracked_files: $total_files
            },
            git: {
                branch: $git_branch,
                dirty: $git_dirty,
                last_commit: $git_last_commit,
                uncommitted_files: $git_uncommitted,
                untracked_files: $git_untracked
            }
        }'
    )

    echo "$LOG_ENTRY" >> "$LOG_FILE"
    echo "$LOG_ENTRY" >> "$SESSIONS_INDEX"

elif [[ "$ACTION" == "end" ]]; then
    # --- Compute session summary ---
    START_FILE="$LOG_DIR/.session-start-${SESSION_ID}"
    START_TIME=""
    DURATION_SEC=0

    if [[ -f "$START_FILE" ]]; then
        START_TIME=$(cat "$START_FILE")
        START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || date -jf "%Y-%m-%dT%H:%M:%SZ" "$START_TIME" +%s 2>/dev/null || echo 0)
        NOW_EPOCH=$(date +%s)
        if [[ "$START_EPOCH" -gt 0 ]]; then
            DURATION_SEC=$((NOW_EPOCH - START_EPOCH))
        fi
    fi

    # Format duration as human-readable
    DURATION_MIN=$((DURATION_SEC / 60))
    DURATION_REMAINDER=$((DURATION_SEC % 60))
    DURATION_HUMAN="${DURATION_MIN}m ${DURATION_REMAINDER}s"

    # Count operations from today's log for this session
    if [[ -f "$LOG_FILE" ]]; then
        TOTAL_OPS=$(grep -c "\"session_id\":\"${SESSION_ID}\"" "$LOG_FILE" 2>/dev/null || echo 0)

        # Operations by type
        OP_BREAKDOWN=$(grep "\"session_id\":\"${SESSION_ID}\"" "$LOG_FILE" 2>/dev/null | \
            jq -s 'group_by(.op_type) | map({type: .[0].op_type, count: length}) | sort_by(-.count)' 2>/dev/null || echo "[]")

        # Tools used
        TOOLS_USED=$(grep "\"session_id\":\"${SESSION_ID}\"" "$LOG_FILE" 2>/dev/null | \
            jq -s 'group_by(.tool) | map({tool: .[0].tool, count: length}) | sort_by(-.count)' 2>/dev/null || echo "[]")

        # Unique files touched
        FILES_TOUCHED=$(grep "\"session_id\":\"${SESSION_ID}\"" "$LOG_FILE" 2>/dev/null | \
            jq -s '[.[].details.file // empty] | unique | length' 2>/dev/null || echo 0)

        FILES_LIST=$(grep "\"session_id\":\"${SESSION_ID}\"" "$LOG_FILE" 2>/dev/null | \
            jq -s '[.[].details.file // empty] | unique' 2>/dev/null || echo "[]")

        # Total tokens
        TOTAL_TOKENS=$(grep "\"session_id\":\"${SESSION_ID}\"" "$LOG_FILE" 2>/dev/null | \
            jq -s '{input: ([.[].tokens.input] | add), output: ([.[].tokens.output] | add), total: ([.[].tokens.total] | add)}' 2>/dev/null || echo '{}')

        # Errors encountered
        ERRORS=$(grep "\"session_id\":\"${SESSION_ID}\"" "$LOG_FILE" 2>/dev/null | \
            jq -s '[.[] | select(.output.error.detected == true) | {tool: .tool, file: .details.file, error: .output.error.message}]' 2>/dev/null || echo "[]")
        ERROR_COUNT=$(echo "$ERRORS" | jq 'length' 2>/dev/null || echo 0)

        # Commands executed
        COMMANDS_RUN=$(grep "\"session_id\":\"${SESSION_ID}\"" "$LOG_FILE" 2>/dev/null | \
            jq -s '[.[] | select(.tool == "Bash") | .details.command] | length' 2>/dev/null || echo 0)

        # Agents spawned
        AGENTS_SPAWNED=$(grep "\"session_id\":\"${SESSION_ID}\"" "$LOG_FILE" 2>/dev/null | \
            jq -s '[.[] | select(.tool == "Agent")] | length' 2>/dev/null || echo 0)
    else
        TOTAL_OPS=0
        OP_BREAKDOWN="[]"
        TOOLS_USED="[]"
        FILES_TOUCHED=0
        FILES_LIST="[]"
        TOTAL_TOKENS='{}'
        ERRORS="[]"
        ERROR_COUNT=0
        COMMANDS_RUN=0
        AGENTS_SPAWNED=0
    fi

    # Git end state
    GIT_BRANCH=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git branch --show-current 2>/dev/null || echo "unknown")
    GIT_DIRTY=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git diff --stat --quiet 2>/dev/null && echo "clean" || echo "dirty")
    GIT_NEW_COMMITS=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git log --oneline --since="$START_TIME" 2>/dev/null | wc -l | tr -d ' ' || echo 0)
    GIT_DIFF_STAT=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git diff --shortstat 2>/dev/null || echo "")

    # --- Log session end ---
    LOG_ENTRY=$(jq -n \
        --arg timestamp "$TIMESTAMP" \
        --arg session_id "$SESSION_ID" \
        --arg project "$PROJECT_NAME" \
        --arg event "session_end" \
        --arg start_time "$START_TIME" \
        --argjson duration_sec "$DURATION_SEC" \
        --arg duration_human "$DURATION_HUMAN" \
        --argjson total_ops "$TOTAL_OPS" \
        --argjson op_breakdown "$OP_BREAKDOWN" \
        --argjson tools_used "$TOOLS_USED" \
        --argjson files_touched "$FILES_TOUCHED" \
        --argjson files_list "$FILES_LIST" \
        --argjson tokens "$TOTAL_TOKENS" \
        --argjson error_count "$ERROR_COUNT" \
        --argjson errors "$ERRORS" \
        --argjson commands_run "$COMMANDS_RUN" \
        --argjson agents_spawned "$AGENTS_SPAWNED" \
        --arg git_branch "$GIT_BRANCH" \
        --arg git_dirty "$GIT_DIRTY" \
        --argjson git_new_commits "$GIT_NEW_COMMITS" \
        --arg git_diff_stat "$GIT_DIFF_STAT" \
        '{
            timestamp: $timestamp,
            session_id: $session_id,
            project: $project,
            event: $event,
            duration: {
                seconds: $duration_sec,
                human: $duration_human,
                start: $start_time
            },
            summary: {
                total_operations: $total_ops,
                operations_by_type: $op_breakdown,
                tools_used: $tools_used,
                files_touched: $files_touched,
                files_list: $files_list,
                commands_run: $commands_run,
                agents_spawned: $agents_spawned,
                errors: {
                    count: $error_count,
                    details: $errors
                }
            },
            tokens: $tokens,
            git_end_state: {
                branch: $git_branch,
                dirty: $git_dirty,
                new_commits: $git_new_commits,
                diff_stat: $git_diff_stat
            }
        }'
    )

    echo "$LOG_ENTRY" >> "$LOG_FILE"

    # Update sessions index with end data
    echo "$LOG_ENTRY" >> "$SESSIONS_INDEX"

    # Cleanup temp files
    rm -f "$START_FILE" "$LOG_DIR/.git-context-${SESSION_ID}" 2>/dev/null
fi

exit 0
