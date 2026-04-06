#!/usr/bin/env bash
# cli-anything-web plugin setup script

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Windows bash environment check (helps avoid cryptic cygpath errors later)
is_windows_bash() {
    case "$(uname -s 2>/dev/null)" in
        CYGWIN*|MINGW*|MSYS*) return 0 ;;
    esac
    return 1
}

if is_windows_bash && ! command -v cygpath >/dev/null 2>&1; then
    echo -e "${RED}✗${NC} Windows bash environment detected but 'cygpath' was not found."
    echo -e "${YELLOW}  Please install Git for Windows (Git Bash) or use WSL, then rerun this script.${NC}"
    exit 1
fi

# Plugin info
PLUGIN_NAME="cli-anything-web"
PLUGIN_VERSION="0.1.0"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  cli-anything-web Plugin v${PLUGIN_VERSION}${NC}"
echo -e "${BLUE}  CLI-Anything for the Web${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check Node.js (required for chrome-devtools-mcp via npx)
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    echo -e "${GREEN}✓${NC} Node.js detected: ${NODE_VERSION}"
else
    echo -e "${RED}✗${NC} Node.js not found. Required for chrome-devtools-mcp."
    echo -e "${YELLOW}  Install from https://nodejs.org (v18+)${NC}"
    exit 1
fi

if command -v npx &>/dev/null; then
    echo -e "${GREEN}✓${NC} npx available"
else
    echo -e "${RED}✗${NC} npx not found. Install Node.js >= 14"
    exit 1
fi

# Check Python version
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python 3 detected: ${PYTHON_VERSION}"
else
    echo -e "${RED}✗${NC} Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Check for required Python packages
echo ""
echo "Checking Python dependencies..."

check_package() {
    local package=$1
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $package installed"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $package not installed"
        return 1
    fi
}

MISSING_PACKAGES=()
check_package "click" || MISSING_PACKAGES+=("click")
check_package "httpx" || MISSING_PACKAGES+=("httpx")
check_package "pytest" || MISSING_PACKAGES+=("pytest")

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Missing packages: ${MISSING_PACKAGES[*]}${NC}"
    echo -e "${YELLOW}Install with: pip install ${MISSING_PACKAGES[*]}${NC}"
fi

# Check playwright-cli
echo ""
echo "Checking playwright-cli..."
if npx @playwright/cli@latest --version > /dev/null 2>&1; then
    echo -e "  ${GREEN}playwright-cli: $(npx @playwright/cli@latest --version 2>&1)${NC}"
else
    echo -e "  ${YELLOW}playwright-cli: not cached (will download on first use via npx)${NC}"
fi

# Verify Chrome DevTools MCP is available
echo ""
echo "Testing chrome-devtools-mcp..."
if npx -y chrome-devtools-mcp@latest --help &>/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} chrome-devtools-mcp available"
else
    echo -e "${YELLOW}⚠${NC} chrome-devtools-mcp will be installed on first use (via npx)"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Plugin installed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Available commands:"
echo ""
echo -e "  ${BLUE}/cli-anything-web${NC} <url>              - Full 4-phase pipeline"
echo -e "  ${BLUE}/cli-anything-web:record${NC} <url>       - Record traffic only"
echo -e "  ${BLUE}/cli-anything-web:refine${NC} <path> [f]  - Expand coverage"
echo -e "  ${BLUE}/cli-anything-web:test${NC} <path>        - Run tests, update TEST.md"
echo -e "  ${BLUE}/cli-anything-web:validate${NC} <path>    - Validate against standards"
echo -e "  ${BLUE}/cli-anything-web:list${NC}               - List all generated CLIs"
echo ""
echo "Examples:"
echo ""
echo -e "  ${BLUE}/cli-anything-web${NC} https://monday.com"
echo -e "  ${BLUE}/cli-anything-web:refine${NC} ./monday \"reporting and export features\""
echo -e "  ${BLUE}/cli-anything-web:test${NC} ./monday"
echo -e "  ${BLUE}/cli-anything-web:validate${NC} ./monday"
echo ""
echo "Documentation:"
echo ""
echo "  HARNESS.md: See plugin directory"
echo "  QUICKSTART.md:  See plugin directory"
echo ""
echo -e "${GREEN}Ready to build CLI-Anything-Web harnesses!${NC}"
echo ""
