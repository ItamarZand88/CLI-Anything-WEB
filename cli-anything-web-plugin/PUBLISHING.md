# Publishing the cli-anything-web Plugin

This guide explains how to make the cli-anything-web plugin installable and how to
publish generated `cli-web-*` CLIs.

## Option 1: Local Installation (Development)

### For Testing

1. **Copy to Claude Code plugins directory:**
   ```bash
   cp -r /path/to/cli-anything-web-plugin ~/.claude/plugins/cli-anything-web
   ```

2. **Reload plugins in Claude Code:**
   ```bash
   /reload-plugins
   ```

3. **Verify installation:**
   ```bash
   /help cli-anything-web
   ```

### For Sharing Locally

```bash
tar -czf cli-anything-web-plugin-v0.1.0.tar.gz cli-anything-web-plugin/
```

Others can install:
```bash
cd ~/.claude/plugins
tar -xzf cli-anything-web-plugin-v0.1.0.tar.gz
```

## Option 2: GitHub Repository (Recommended)

```bash
cd cli-anything-web-plugin
git init
git add .
git commit -m "Initial commit: cli-anything-web plugin v0.1.0"
gh repo create cli-anything-web-plugin --public --source=. --remote=origin
git push -u origin main
```

Users can install directly:
```bash
cd ~/.claude/plugins
git clone https://github.com/yourusername/cli-anything-web-plugin.git cli-anything-web
```

## Publishing Generated CLIs to PyPI

After generating a CLI with `/cli-anything-web <url>`, make it installable:

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
