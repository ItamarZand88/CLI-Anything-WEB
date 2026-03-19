---
name: cli-anything-web:list
description: List all available CLI-Anything-Web CLIs (installed and generated).
argument-hint: "[--json]"
allowed-tools: Bash(*)
---

# cli-anything-web:list

List all CLI-Anything-Web CLIs — both installed packages and local generated sources.

## Process

1. **Find installed CLIs**: Use `pip list` or `importlib.metadata` to find `cli-web-*` packages.
   For each, check `shutil.which(f"cli-web-{app}")` for the executable path.

2. **Find generated CLIs**: Glob for `**/agent-harness/cli_web/*/__init__.py` from the
   current directory. Extract app name from the path. Read version from `setup.py` if present.

3. **Merge**: Deduplicate by app name. Prefer installed data when both exist.

4. **Output**:

**Table (default):**
```
CLI-Anything-Web CLIs (found 3)

Name       Status      Version   Source
───────────────────────────────────────────
monday     installed   1.0.0     ./monday/agent-harness
notion     generated   1.0.0     ./notion/agent-harness
```

**JSON (`--json`):**
```json
{
  "tools": [{"name": "monday", "status": "installed", "version": "1.0.0", "executable": "/usr/local/bin/cli-web-monday", "source": "./monday/agent-harness"}],
  "total": 1
}
```

If no CLIs found, say "No CLI-Anything-Web CLIs found."
