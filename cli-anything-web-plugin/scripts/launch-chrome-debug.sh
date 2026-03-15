#!/usr/bin/env bash
# launch-chrome-debug.sh — Launch Chrome with a dedicated debug profile
#
# This creates a persistent Chrome profile at ~/.chrome-debug-profile
# with remote debugging enabled on port 9222. Log in once — your
# session cookies persist across restarts.
#
# Usage:
#   bash scripts/launch-chrome-debug.sh [url]
#
# Examples:
#   bash scripts/launch-chrome-debug.sh
#   bash scripts/launch-chrome-debug.sh https://notebooklm.google.com/

set -uo pipefail

URL="${1:-about:blank}"
PORT=9222
PROFILE_DIR="$HOME/.chrome-debug-profile"

# Detect Chrome path
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash / WSL)
    CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
    if [ ! -f "$CHROME" ]; then
        CHROME="/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
else
    # Linux
    CHROME="$(which google-chrome 2>/dev/null || which chromium-browser 2>/dev/null || echo "")"
fi

if [ -z "$CHROME" ] || [ ! -f "$CHROME" ]; then
    echo "ERROR: Chrome not found. Install Google Chrome first."
    exit 1
fi

# Check if port is already in use
if command -v lsof &>/dev/null; then
    if lsof -i ":$PORT" &>/dev/null; then
        echo "Debug Chrome already running on port $PORT"
        echo "Connect with: npx chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:$PORT"
        exit 0
    fi
elif command -v netstat &>/dev/null; then
    if netstat -an 2>/dev/null | grep -q ":$PORT.*LISTEN"; then
        echo "Debug Chrome already running on port $PORT"
        exit 0
    fi
fi

echo "Launching Chrome debug profile..."
echo "  Profile: $PROFILE_DIR"
echo "  Port:    $PORT"
echo "  URL:     $URL"
echo ""
echo "First time? Log into your accounts in this Chrome window."
echo "Your sessions will persist across restarts."
echo ""

"$CHROME" \
    --remote-debugging-port="$PORT" \
    --user-data-dir="$PROFILE_DIR" \
    "$URL" \
    > /dev/null 2>&1 &

echo "Chrome launched (PID: $!)"
echo "Ready for: claude --plugin-dir /path/to/cli-anything-web-plugin"
