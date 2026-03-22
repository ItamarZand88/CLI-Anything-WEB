#!/bin/bash
# Hook: PostToolUse — Detailed session activity logger
#
# Logs every tool operation to JSONL with rich metadata:
#   - Full tool input/output (truncated to keep logs manageable)
#   - File paths, bash commands, search patterns
#   - Token estimation
#   - Git context (branch, dirty state)
#   - Operation classification (read/write/search/execute/navigate)
#   - Duration tracking via timestamps
#   - Error detection from tool output
#
# Logs stored at: .claude/logs/session-YYYY-MM-DD.jsonl
# Session index:  .claude/logs/sessions.jsonl (one line per session start)
#
# Companion: session-stats can analyze these logs

set -e

INPUT=$(cat)

# --- Configuration ---
LOG_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/logs"
PROJECT_NAME=$(basename "${CLAUDE_PROJECT_DIR:-$(pwd)}")
SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%s)-$$}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/session-${DATE}.jsonl"

mkdir -p "$LOG_DIR"

# --- Extract core fields ---
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // "unknown"')
TOOL_INPUT=$(echo "$INPUT" | jq -c '.tool_input // {}')
TOOL_OUTPUT=$(echo "$INPUT" | jq -r '.tool_output // ""')
SESSION_ID_FROM_INPUT=$(echo "$INPUT" | jq -r '.session_id // ""')
HOOK_EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // "PostToolUse"')

# Use session_id from hook input if available
if [[ -n "$SESSION_ID_FROM_INPUT" ]]; then
    SESSION_ID="$SESSION_ID_FROM_INPUT"
fi

# --- Classify operation ---
OP_TYPE="unknown"
case "$TOOL_NAME" in
    Read)           OP_TYPE="read" ;;
    Write)          OP_TYPE="write" ;;
    Edit)           OP_TYPE="edit" ;;
    Bash)           OP_TYPE="execute" ;;
    Grep)           OP_TYPE="search" ;;
    Glob)           OP_TYPE="search" ;;
    LSP)            OP_TYPE="navigate" ;;
    Agent)          OP_TYPE="delegate" ;;
    WebFetch)       OP_TYPE="network" ;;
    WebSearch)      OP_TYPE="network" ;;
    Skill)          OP_TYPE="skill" ;;
    mcp__*)         OP_TYPE="mcp" ;;
    TodoWrite|TodoRead) OP_TYPE="planning" ;;
    *)              OP_TYPE="other" ;;
esac

# --- Extract tool-specific details ---
FILE_PATH=""
COMMAND=""
SEARCH_PATTERN=""
SEARCH_GLOB=""
LINES_READ=""
EDIT_SIZE=""
AGENT_TYPE=""
SKILL_NAME=""
MCP_SERVER=""

case "$TOOL_NAME" in
    Read)
        FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // ""')
        LINES_READ=$(echo "$TOOL_INPUT" | jq -r '
            if .limit then "\(.offset // 0)-\((.offset // 0) + .limit)"
            elif .pages then "pages:\(.pages)"
            else "full"
            end
        ')
        ;;
    Write)
        FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // ""')
        CONTENT_LEN=$(echo "$TOOL_INPUT" | jq -r '.content // "" | length')
        EDIT_SIZE="$CONTENT_LEN chars written"
        ;;
    Edit)
        FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // ""')
        OLD_LEN=$(echo "$TOOL_INPUT" | jq -r '.old_string // "" | length')
        NEW_LEN=$(echo "$TOOL_INPUT" | jq -r '.new_string // "" | length')
        REPLACE_ALL=$(echo "$TOOL_INPUT" | jq -r '.replace_all // false')
        EDIT_SIZE="old:${OLD_LEN}→new:${NEW_LEN} chars (replace_all:${REPLACE_ALL})"
        ;;
    Bash)
        COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // ""' | head -c 500)
        ;;
    Grep)
        SEARCH_PATTERN=$(echo "$TOOL_INPUT" | jq -r '.pattern // ""')
        SEARCH_GLOB=$(echo "$TOOL_INPUT" | jq -r '.glob // .type // ""')
        FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.path // ""')
        ;;
    Glob)
        SEARCH_PATTERN=$(echo "$TOOL_INPUT" | jq -r '.pattern // ""')
        FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.path // ""')
        ;;
    Agent)
        AGENT_TYPE=$(echo "$TOOL_INPUT" | jq -r '.subagent_type // "general-purpose"')
        COMMAND=$(echo "$TOOL_INPUT" | jq -r '.description // ""')
        ;;
    Skill)
        SKILL_NAME=$(echo "$TOOL_INPUT" | jq -r '.skill // ""')
        ;;
    mcp__*)
        MCP_SERVER=$(echo "$TOOL_NAME" | sed 's/mcp__\([^_]*\)__.*/\1/')
        ;;
esac

# --- Analyze tool output ---
OUTPUT_LEN=${#TOOL_OUTPUT}
OUTPUT_PREVIEW=$(echo "$TOOL_OUTPUT" | head -c 300 | tr '\n' ' ' | sed 's/"/\\"/g')

# Detect errors in output
HAS_ERROR="false"
ERROR_MSG=""
if echo "$TOOL_OUTPUT" | grep -qiE '(error|Error|ERROR|FAIL|fatal|exception|denied|refused|not found)' 2>/dev/null; then
    HAS_ERROR="true"
    ERROR_MSG=$(echo "$TOOL_OUTPUT" | grep -iE '(error|Error|ERROR|FAIL|fatal|exception|denied|refused|not found)' | head -1 | head -c 200 | sed 's/"/\\"/g')
fi

# Detect if output was truncated by Claude
OUTPUT_TRUNCATED="false"
if echo "$TOOL_OUTPUT" | grep -q 'truncated\|content_truncated\|...output truncated' 2>/dev/null; then
    OUTPUT_TRUNCATED="true"
fi

# --- Token estimation (rough: ~4 chars per token) ---
INPUT_LEN=${#TOOL_INPUT}
TOKENS_IN=$((INPUT_LEN / 4))
TOKENS_OUT=$((OUTPUT_LEN / 4))
TOKENS_TOTAL=$((TOKENS_IN + TOKENS_OUT))

# --- Git context (cached per session to avoid overhead) ---
GIT_CACHE_FILE="$LOG_DIR/.git-context-${SESSION_ID}"
if [[ -f "$GIT_CACHE_FILE" ]]; then
    GIT_BRANCH=$(head -1 "$GIT_CACHE_FILE")
    GIT_DIRTY=$(tail -1 "$GIT_CACHE_FILE")
else
    GIT_BRANCH=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git branch --show-current 2>/dev/null || echo "unknown")
    GIT_DIRTY=$(cd "${CLAUDE_PROJECT_DIR:-.}" && git diff --stat --quiet 2>/dev/null && echo "clean" || echo "dirty")
    echo "$GIT_BRANCH" > "$GIT_CACHE_FILE"
    echo "$GIT_DIRTY" >> "$GIT_CACHE_FILE"
fi

# --- Count files affected (for search tools) ---
FILES_MATCHED=""
if [[ "$OP_TYPE" == "search" ]]; then
    FILES_MATCHED=$(echo "$TOOL_OUTPUT" | grep -c '^' 2>/dev/null || echo "0")
fi

# --- Build log entry ---
LOG_ENTRY=$(jq -n \
    --arg timestamp "$TIMESTAMP" \
    --arg session_id "$SESSION_ID" \
    --arg project "$PROJECT_NAME" \
    --arg tool "$TOOL_NAME" \
    --arg op_type "$OP_TYPE" \
    --arg file "$FILE_PATH" \
    --arg command "$COMMAND" \
    --arg search_pattern "$SEARCH_PATTERN" \
    --arg search_glob "$SEARCH_GLOB" \
    --arg lines_read "$LINES_READ" \
    --arg edit_size "$EDIT_SIZE" \
    --arg agent_type "$AGENT_TYPE" \
    --arg skill_name "$SKILL_NAME" \
    --arg mcp_server "$MCP_SERVER" \
    --argjson output_len "$OUTPUT_LEN" \
    --arg output_preview "$OUTPUT_PREVIEW" \
    --argjson has_error "$HAS_ERROR" \
    --arg error_msg "$ERROR_MSG" \
    --argjson output_truncated "$OUTPUT_TRUNCATED" \
    --argjson tokens_in "$TOKENS_IN" \
    --argjson tokens_out "$TOKENS_OUT" \
    --argjson tokens_total "$TOKENS_TOTAL" \
    --arg git_branch "$GIT_BRANCH" \
    --arg git_dirty "$GIT_DIRTY" \
    --arg files_matched "$FILES_MATCHED" \
    '{
        timestamp: $timestamp,
        session_id: $session_id,
        project: $project,
        tool: $tool,
        op_type: $op_type,
        details: (
            {}
            | if $file != "" then . + {file: $file} else . end
            | if $command != "" then . + {command: $command} else . end
            | if $search_pattern != "" then . + {search_pattern: $search_pattern} else . end
            | if $search_glob != "" then . + {search_glob: $search_glob} else . end
            | if $lines_read != "" then . + {lines_read: $lines_read} else . end
            | if $edit_size != "" then . + {edit_size: $edit_size} else . end
            | if $agent_type != "" then . + {agent_type: $agent_type} else . end
            | if $skill_name != "" then . + {skill_name: $skill_name} else . end
            | if $mcp_server != "" then . + {mcp_server: $mcp_server} else . end
            | if $files_matched != "" then . + {files_matched: ($files_matched | tonumber)} else . end
        ),
        output: {
            length: $output_len,
            preview: $output_preview,
            truncated: $output_truncated,
            error: (if $has_error then {detected: true, message: $error_msg} else null end)
        },
        tokens: {
            input: $tokens_in,
            output: $tokens_out,
            total: $tokens_total
        },
        git: {
            branch: $git_branch,
            dirty: $git_dirty
        }
    } | with_entries(select(.value != null and .value != {}))'
)

# Append to log
echo "$LOG_ENTRY" >> "$LOG_FILE"

# Always allow
exit 0
