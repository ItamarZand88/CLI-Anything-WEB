---
name: web-harness:list
description: List all available Web-Harness CLIs (installed and generated).
argument-hint: "[--path <directory>] [--depth <n>] [--json]"
allowed-tools: Bash(*)
---

## CRITICAL: Read CLI-ANYTHING-WEB.md First

**Before doing anything else, read `${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md`.** It defines the package structure this command scans for.

# web-harness:list Command

List all available Web-Harness CLIs (installed and generated).

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
