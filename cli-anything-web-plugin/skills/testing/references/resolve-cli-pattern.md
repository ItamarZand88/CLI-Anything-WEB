# _resolve_cli Pattern Reference

The standard pattern for subprocess testing in cli-web-* CLIs. Every E2E test
file must use this helper -- never hardcode paths.

## The `_resolve_cli` Helper

```python
import os, sys, shutil, subprocess

def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev."""
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-web-", "cli_web.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]
```

## The `TestCLISubprocess` Class

```python
class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-web-<app>")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True,
            check=check,
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
```

## Key Rules for Subprocess Tests

- Always use `_resolve_cli("cli-web-<app>")` -- never hardcode module paths
- Do NOT set `cwd` -- installed commands must work from any directory
- Use `CLI_WEB_FORCE_INSTALLED=1` in CI to ensure the installed command is tested
- After running, verify `[_resolve_cli] Using installed command:` appears in output
