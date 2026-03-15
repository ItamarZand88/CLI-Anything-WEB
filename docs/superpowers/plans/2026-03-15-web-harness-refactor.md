# Web-Harness Plugin Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `cli-anything-web-plugin` to match cli-anything-plugin standards — fixing broken MCP tool references, aligning command structure, adding missing commands/docs, and cleaning up artifacts.

**Architecture:** All changes are to plugin files (Markdown commands, Bash scripts, docs). No Python code is written. Verification for each task is done by reading the modified file and confirming correctness by eye.

**Tech Stack:** Markdown (commands/docs), Bash (setup script), chrome-devtools-mcp tool names

**Spec:** `docs/superpowers/specs/2026-03-15-web-harness-refactor-design.md`

---

## Chunk 1: Fix WEB-HARNESS.md and Core Commands

### Task 1: Fix WEB-HARNESS.md Phase 1 tool names

**Files:**
- Modify: `cli-anything-web-plugin/WEB-HARNESS.md`

The Phase 1 section currently describes `start_chrome_and_connect` (doesn't exist) and `execute_javascript` (wrong name). Replace with correct chrome-devtools-mcp tool names.

- [ ] **Step 1: Find all broken references**

Read `cli-anything-web-plugin/WEB-HARNESS.md` and note every occurrence of:
- `start_chrome_and_connect`
- `execute_javascript`

- [ ] **Step 2: Update Phase 1 — Chrome connection**

Find this text in WEB-HARNESS.md Phase 1:
```
1. Open Chrome via DevTools MCP (`start_chrome_and_connect`)
2. Navigate to target URL
```

Replace with:
```
1. chrome-devtools-mcp auto-launches Chrome on first tool call — no setup step needed
2. Call `navigate_page` with the target URL
3. If login required — pause and ask user to log in manually
4. Enable network monitoring (`list_network_requests`)
```

- [ ] **Step 3: Update `execute_javascript` → `evaluate_script`**

Find every instance of `execute_javascript` in WEB-HARNESS.md and replace with `evaluate_script`.

- [ ] **Step 4: Verify**

Read the updated WEB-HARNESS.md Phase 1 section and confirm:
- No mention of `start_chrome_and_connect`
- No mention of `execute_javascript`
- `navigate_page` and `evaluate_script` appear correctly

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add cli-anything-web-plugin/WEB-HARNESS.md
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "fix: correct chrome-devtools-mcp tool names in WEB-HARNESS.md"
```

---

### Task 2: Fix commands/web-harness.md

**Files:**
- Modify: `cli-anything-web-plugin/commands/web-harness.md`

Add the "CRITICAL: Read WEB-HARNESS.md First" gate (matching cli-anything pattern) and fix the broken tool references in the Phase 1 execution block.

- [ ] **Step 1: Add CRITICAL header**

After the frontmatter block (after the closing `---`) and before `# Web-Harness: Full Pipeline`, insert:

```markdown
## CRITICAL: Read WEB-HARNESS.md First

**Before doing anything else, you MUST read `${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md`.** It defines the complete methodology, all phases, and implementation standards. Every phase below follows WEB-HARNESS.md. Do not improvise — follow the harness specification.
```

- [ ] **Step 2: Fix Phase 1 Chrome connection**

Find the Phase 1 block that says:
```
1. Use Chrome DevTools MCP to open the target URL:
   - Call `start_chrome_and_connect` with the target URL
   - If the page shows a login screen, STOP and ask the user to log in manually
   - Wait for user confirmation before proceeding
```

Replace with:
```
1. Use chrome-devtools-mcp to open the target URL:
   - chrome-devtools-mcp auto-launches Chrome on first tool call
   - Call `navigate_page` with the target URL
   - If the page shows a login screen, STOP and ask the user to log in manually
   - Wait for user confirmation before proceeding
```

- [ ] **Step 3: Fix `execute_javascript` reference**

Find any `execute_javascript` reference in this file and replace with `evaluate_script`.

- [ ] **Step 4: Fix allowed-tools**

In the frontmatter, the `allowed-tools` line should read:
```
allowed-tools: Bash(*), Read, Write, Edit, mcp__chrome-devtools__*
```
Read the frontmatter and confirm this value. If it says anything other than `mcp__chrome-devtools__*` (e.g., `mcp__claude-in-chrome__*`), update it to the correct value shown above.

- [ ] **Step 5: Verify**

Read the file and confirm:
- CRITICAL header appears right after frontmatter
- No `start_chrome_and_connect`
- No `execute_javascript`

- [ ] **Step 6: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add cli-anything-web-plugin/commands/web-harness.md
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "fix: add CRITICAL header and fix tool names in web-harness.md"
```

---

### Task 3: Fix commands/record.md

**Files:**
- Modify: `cli-anything-web-plugin/commands/record.md`

Same two fixes: CRITICAL header + broken tool references.

- [ ] **Step 1: Add CRITICAL header**

After the frontmatter closing `---`, before `# Web-Harness: Record Traffic Only`, insert:

```markdown
## CRITICAL: Read WEB-HARNESS.md First

**Before doing anything else, you MUST read `${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md`.** Phase 1 of the methodology defines the complete recording process. Follow it exactly.
```

- [ ] **Step 2: Fix Phase 1 Chrome connection**

Find any reference to `start_chrome_and_connect` in this file and replace the description with:
```
1. chrome-devtools-mcp auto-launches Chrome on first tool call
2. Call `navigate_page` with the target URL
```

- [ ] **Step 3: Fix `execute_javascript`**

Replace any `execute_javascript` with `evaluate_script`.

- [ ] **Step 4: Verify**

Read the file and confirm no broken references remain.

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add cli-anything-web-plugin/commands/record.md
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "fix: add CRITICAL header and fix tool names in record.md"
```

---

## Chunk 2: Add CRITICAL Headers to Remaining Commands

### Task 4: Add CRITICAL header to commands/refine.md

**Files:**
- Modify: `cli-anything-web-plugin/commands/refine.md`

- [ ] **Step 1: Add CRITICAL header**

After the frontmatter closing `---`, before `# Web-Harness: Refine Existing Harness`, insert:

```markdown
## CRITICAL: Read WEB-HARNESS.md First

**Before refining, read `${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md`.** All new commands and tests must follow the same standards as the original build. WEB-HARNESS.md is the single source of truth for architecture, patterns, and quality requirements.
```

- [ ] **Step 2: Verify**

Read the file and confirm the CRITICAL block appears correctly.

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add cli-anything-web-plugin/commands/refine.md
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "fix: add CRITICAL header to refine.md"
```

---

### Task 5: Add CRITICAL header to commands/test.md

**Files:**
- Modify: `cli-anything-web-plugin/commands/test.md`

- [ ] **Step 1: Add CRITICAL header**

After the frontmatter closing `---`, before `# Web-Harness: Test Runner`, insert:

```markdown
## CRITICAL: Read WEB-HARNESS.md First

**Before running tests, read `${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md`.** It defines the test standards, expected structure, and what constitutes a passing test suite.
```

- [ ] **Step 2: Verify**

Read the file and confirm the CRITICAL block appears correctly.

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add cli-anything-web-plugin/commands/test.md
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "fix: add CRITICAL header to test.md"
```

---

### Task 6: Add CRITICAL header to commands/validate.md

**Files:**
- Modify: `cli-anything-web-plugin/commands/validate.md`

- [ ] **Step 1: Add CRITICAL header**

After the frontmatter closing `---`, before `# Web-Harness: Validate Standards`, insert:

```markdown
## CRITICAL: Read WEB-HARNESS.md First

**Before validating, read `${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md`.** It is the single source of truth for all validation checks below. Every check in this command maps to a requirement in WEB-HARNESS.md.
```

- [ ] **Step 2: Verify**

Read the file and confirm the CRITICAL block appears correctly.

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add cli-anything-web-plugin/commands/validate.md
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "fix: add CRITICAL header to validate.md"
```

---

## Chunk 3: New list Command

### Task 7: Create commands/list.md

**Files:**
- Create: `cli-anything-web-plugin/commands/list.md`

This is the `web-harness:list` command — parallel to `cli-anything:list`. Scans for installed and generated `cli-web-*` CLIs.

- [ ] **Step 1: Create the file**

Create `cli-anything-web-plugin/commands/list.md` with this exact content:

```markdown
---
name: web-harness:list
description: List all available Web-Harness CLIs (installed and generated).
argument-hint: "[--path <directory>] [--depth <n>] [--json]"
allowed-tools: Bash(*)
---

# web-harness:list Command

List all available Web-Harness CLIs (installed and generated).

## CRITICAL: Read WEB-HARNESS.md First

**Before doing anything else, read `${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md`.** It defines the package structure this command scans for.

## Usage

```bash
/web-harness:list [--path <directory>] [--depth <n>] [--json]
```

## Options

- `--path <directory>` - Directory to search for generated CLIs (default: current directory)
- `--depth <n>` - Maximum recursion depth (default: unlimited). Use `0` for current directory only.
- `--json` - Output in JSON format for machine parsing

## What This Command Does

Displays all Web-Harness CLIs available in the system.

### 1. Installed CLIs

Uses `importlib.metadata` to find installed `cli-web-*` packages:

```python
from importlib.metadata import distributions
import shutil

installed = {}
for dist in distributions():
    name = dist.metadata.get("Name", "")
    if name.startswith("cli-web-"):
        app = name.replace("cli-web-", "")
        version = dist.version
        executable = shutil.which(f"cli-web-{app}")
        installed[app] = {
            "status": "installed",
            "version": version,
            "executable": executable
        }
```

### 2. Generated CLIs

Uses `glob` to find local CLI directories:
- Pattern: `**/agent-harness/cli_web/*/__init__.py` (or depth-limited variant)
- Extracts: app name, version (from setup.py), source path

```python
from pathlib import Path
import glob
import re

search_path = args.get("path", ".")
max_depth = args.get("depth", None)
generated = {}

def extract_version_from_setup(setup_path):
    try:
        content = Path(setup_path).read_text()
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        return match.group(1) if match else None
    except:
        return None

def build_glob_patterns(base_path, depth):
    base = Path(base_path)
    suffix = "agent-harness/cli_web/*/__init__.py"
    if depth is None:
        return [str(base / "**" / suffix)]
    patterns = []
    for d in range(depth + 1):
        if d == 0:
            patterns.append(str(base / suffix))
        else:
            prefix = "/".join(["*"] * d)
            patterns.append(str(base / prefix / suffix))
    return patterns

patterns = build_glob_patterns(search_path, max_depth)
for pattern in patterns:
    for init_file in glob.glob(pattern, recursive=True):
        parts = Path(init_file).parts
        for i, p in enumerate(parts):
            if p == "cli_web" and i + 1 < len(parts):
                app = parts[i + 1]
                agent_harness_idx = parts.index("agent-harness") if "agent-harness" in parts else i - 1
                source = str(Path(*parts[:agent_harness_idx + 2]))
                setup_path = Path(*parts[:agent_harness_idx + 1]) / "setup.py"
                version = extract_version_from_setup(setup_path)
                generated[app] = {
                    "status": "generated",
                    "version": version,
                    "executable": None,
                    "source": source
                }
                break
```

### 3. Merge and Output

- Deduplicate by app name; prefer installed data when both exist
- Keep source path from generated entry if available

## Output Formats

### Table (default)

```
Web-Harness CLIs (found 3)

Name       Status      Version   Source
─────────────────────────────────────────────────────────
monday     installed   1.0.0     ./monday/agent-harness
notion     generated   1.0.0     ./notion/agent-harness
linear     generated   0.9.0     ./linear/agent-harness
```

### JSON (--json)

```json
{
  "tools": [
    {
      "name": "monday",
      "status": "installed",
      "version": "1.0.0",
      "executable": "/usr/local/bin/cli-web-monday",
      "source": "./monday/agent-harness"
    }
  ],
  "total": 1,
  "installed": 1,
  "generated_only": 0
}
```

## Error Handling

| Scenario | Action |
|----------|--------|
| No CLIs found | Show "No Web-Harness CLIs found" |
| Invalid --path | Show error: "Path not found: <path>" |
| Permission denied | Skip directory, continue, show warning |

## Examples

```bash
/web-harness:list
/web-harness:list --depth 2
/web-harness:list --json
/web-harness:list --path ./projects --depth 3 --json
```
```

- [ ] **Step 2: Verify**

Read the created file. Confirm:
- Frontmatter has `name: web-harness:list`
- CRITICAL header is present
- Python code scans for `cli_web/*` (not `cli_anything/*`)
- CLI names use `cli-web-` prefix (not `cli-anything-`)

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add cli-anything-web-plugin/commands/list.md
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "feat: add web-harness:list command"
```

---

## Chunk 4: Docs and Setup Script

### Task 8: Fix QUICKSTART.md

**Files:**
- Modify: `cli-anything-web-plugin/QUICKSTART.md`

Remove the fake marketplace references. Replace with manual install instructions that match cli-anything's QUICKSTART pattern.

- [ ] **Step 1: Replace install section**

Find the current Step 1 install block:
```
## Step 1: Install the Plugin (30 seconds)

\`\`\`bash
# Option A: Marketplace (when published)
/plugin marketplace add <your-github>/web-harness
/plugin install web-harness

# Option B: Manual
git clone https://github.com/<your-github>/web-harness.git
bash web-harness/scripts/setup-web-harness.sh
\`\`\`
```

Replace with:
```markdown
## Step 1: Install the Plugin (30 seconds)

```bash
# Copy plugin to Claude Code plugins directory
cp -r /path/to/cli-anything-web-plugin ~/.claude/plugins/web-harness

# Reload plugins in Claude Code
/reload-plugins

# Verify installation
/help web-harness
```
```

- [ ] **Step 2: Verify**

Read QUICKSTART.md and confirm no marketplace references remain.

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add cli-anything-web-plugin/QUICKSTART.md
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "fix: remove fake marketplace references from QUICKSTART.md"
```

---

### Task 9: Create PUBLISHING.md

**Files:**
- Create: `cli-anything-web-plugin/PUBLISHING.md`

Matches cli-anything's PUBLISHING.md structure but for `cli-web-*` packages and the `cli_web.*` namespace.

- [ ] **Step 1: Create the file**

Create `cli-anything-web-plugin/PUBLISHING.md` with this content:

```markdown
# Publishing the web-harness Plugin

This guide explains how to make the web-harness plugin installable and how to
publish generated `cli-web-*` CLIs.

## Option 1: Local Installation (Development)

### For Testing

1. **Copy to Claude Code plugins directory:**
   ```bash
   cp -r /path/to/cli-anything-web-plugin ~/.claude/plugins/web-harness
   ```

2. **Reload plugins in Claude Code:**
   ```bash
   /reload-plugins
   ```

3. **Verify installation:**
   ```bash
   /help web-harness
   ```

### For Sharing Locally

```bash
tar -czf web-harness-plugin-v0.1.0.tar.gz cli-anything-web-plugin/
```

Others can install:
```bash
cd ~/.claude/plugins
tar -xzf web-harness-plugin-v0.1.0.tar.gz
```

## Option 2: GitHub Repository (Recommended)

```bash
cd cli-anything-web-plugin
git init
git add .
git commit -m "Initial commit: web-harness plugin v0.1.0"
gh repo create cli-anything-web-plugin --public --source=. --remote=origin
git push -u origin main
```

Users can install directly:
```bash
cd ~/.claude/plugins
git clone https://github.com/yourusername/cli-anything-web-plugin.git web-harness
```

## Publishing Generated CLIs to PyPI

After generating a CLI with `/web-harness <url>`, make it installable:

### Package structure (PEP 420 namespace)

```
<app>/agent-harness/
├── setup.py
└── cli_web/              # NO __init__.py (namespace package)
    └── <app>/            # HAS __init__.py
        ├── <app>_cli.py
        ├── core/
        └── tests/
```

### setup.py template

```python
from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-<app>",
    version="1.0.0",
    packages=find_namespace_packages(include=["cli_web.*"]),
    install_requires=[
        "click>=8.0.0",
        "httpx>=0.24.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-<app>=cli_web.<app>.<app>_cli:main",
        ],
    },
    python_requires=">=3.10",
)
```

Key rules:
- Use `find_namespace_packages`, NOT `find_packages`
- Use `include=["cli_web.*"]` to scope discovery
- Entry point: `cli_web.<app>.<app>_cli:main`

### Install and test locally

```bash
cd <app>/agent-harness
pip install -e .
which cli-web-<app>
cli-web-<app> --help
CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/<app>/tests/ -v -s
```

### Publish to PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```

Users install with:
```bash
pip install cli-web-monday cli-web-notion
cli-web-monday --help
cli-web-notion --help
```

Multiple `cli-web-*` packages coexist in the same Python environment without
conflicts — the `cli_web/` namespace package ensures isolation.

## Versioning

Follow semantic versioning:
- **Major**: Breaking API changes
- **Minor**: New commands, backward compatible
- **Patch**: Bug fixes

Update version in `setup.py` and git tags.

## Distribution Checklist

Before publishing:

- [ ] All commands tested and working
- [ ] README.md is comprehensive
- [ ] LICENSE file included
- [ ] setup.py has correct namespace config
- [ ] No hardcoded credentials or tokens
- [ ] Tests pass (unit + E2E)
- [ ] `cli-web-<app> --help` shows all commands
- [ ] `cli-web-<app> --json <cmd>` works
```

- [ ] **Step 2: Verify**

Read the file. Confirm:
- Uses `cli-web-*` (not `cli-anything-*`) throughout
- Uses `cli_web.*` namespace (not `cli_anything.*`)
- `find_namespace_packages(include=["cli_web.*"])` is correct
- Entry point format is correct

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add cli-anything-web-plugin/PUBLISHING.md
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "feat: add PUBLISHING.md for web-harness plugin and cli-web-* packages"
```

---

### Task 10: Fix setup-web-harness.sh

**Files:**
- Modify: `cli-anything-web-plugin/scripts/setup-web-harness.sh`

Add Windows bash/cygpath detection (matching cli-anything's setup script pattern) and fix the fragile file copy logic.

- [ ] **Step 1: Read the current script**

Read `cli-anything-web-plugin/scripts/setup-web-harness.sh` to understand the current structure.

- [ ] **Step 2: Rewrite the script**

Replace the entire file with:

```bash
#!/usr/bin/env bash
# web-harness plugin setup script

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
PLUGIN_NAME="web-harness"
PLUGIN_VERSION="0.1.0"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  web-harness Plugin v${PLUGIN_VERSION}${NC}"
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
    echo -e "${RED}✗${NC} npx not found. Install Node.js >= 14${NC}"
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
echo -e "  ${BLUE}/web-harness${NC} <url>              - Full 7-phase pipeline"
echo -e "  ${BLUE}/web-harness:record${NC} <url>       - Record traffic only"
echo -e "  ${BLUE}/web-harness:refine${NC} <path> [f]  - Expand coverage"
echo -e "  ${BLUE}/web-harness:test${NC} <path>        - Run tests, update TEST.md"
echo -e "  ${BLUE}/web-harness:validate${NC} <path>    - Validate against standards"
echo -e "  ${BLUE}/web-harness:list${NC}               - List all generated CLIs"
echo ""
echo "Examples:"
echo ""
echo -e "  ${BLUE}/web-harness${NC} https://monday.com"
echo -e "  ${BLUE}/web-harness:refine${NC} ./monday \"reporting and export features\""
echo -e "  ${BLUE}/web-harness:test${NC} ./monday"
echo -e "  ${BLUE}/web-harness:validate${NC} ./monday"
echo ""
echo "Documentation:"
echo ""
echo "  WEB-HARNESS.md: See plugin directory"
echo "  QUICKSTART.md:  See plugin directory"
echo ""
echo -e "${GREEN}Ready to build web CLI harnesses!${NC}"
echo ""
```

- [ ] **Step 3: Make executable**

```bash
chmod +x "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web/cli-anything-web-plugin/scripts/setup-web-harness.sh"
```

- [ ] **Step 4: Verify**

Read the script. Confirm:
- `is_windows_bash()` function and cygpath check are present
- Colors defined with `RED`, `GREEN`, `YELLOW`, `BLUE`, `NC`
- Checks Node.js, npx, Python3
- Lists all 6 commands including `web-harness:list`
- No references to old fragile copy logic

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add cli-anything-web-plugin/scripts/setup-web-harness.sh
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "fix: rewrite setup script with Windows detection and proper dependency checks"
```

---

## Chunk 5: Cleanup

### Task 11: Delete bogus directory

**Files:**
- Delete: `cli-anything-web-plugin/skills/web-harness-methodology/{references,scripts}/`

This is a literal directory whose name is the unexpanded glob string `{references,scripts}`. The real `references/` directory (containing `auth-strategies.md` and `traffic-patterns.md`) must NOT be touched.

- [ ] **Step 1: Confirm the bogus directory exists**

```bash
ls "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web/cli-anything-web-plugin/skills/web-harness-methodology/"
```

Expected output should include both `references` (the real one) and `{references,scripts}` (the bogus literal).

- [ ] **Step 2: Confirm the real references directory has content**

```bash
ls "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web/cli-anything-web-plugin/skills/web-harness-methodology/references/"
```

Expected: `auth-strategies.md` and `traffic-patterns.md`

- [ ] **Step 3: Delete only the bogus directory**

```bash
rm -rf "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web/cli-anything-web-plugin/skills/web-harness-methodology/{references,scripts}"
```

- [ ] **Step 4: Verify real references directory is intact**

```bash
ls "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web/cli-anything-web-plugin/skills/web-harness-methodology/"
```

Confirm:
- `references/` still exists
- `{references,scripts}/` is gone
- `SKILL.md` still exists

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" add -A cli-anything-web-plugin/skills/web-harness-methodology/
git -C "C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything-Web" commit -m "chore: delete bogus {references,scripts} directory artifact"
```

---

## Final Verification

After all tasks complete, do a full sanity check:

- [ ] Grep for `start_chrome_and_connect` across all plugin files — should return zero results
- [ ] Grep for `execute_javascript` across all plugin files — should return zero results
- [ ] Confirm `commands/` has exactly 6 files: `web-harness.md`, `record.md`, `refine.md`, `test.md`, `validate.md`, `list.md`
- [ ] Confirm each command file has a `## CRITICAL: Read WEB-HARNESS.md First` section
- [ ] Confirm `PUBLISHING.md` exists
- [ ] Confirm `{references,scripts}` directory is gone
- [ ] Confirm `references/` directory still has `auth-strategies.md` and `traffic-patterns.md`
