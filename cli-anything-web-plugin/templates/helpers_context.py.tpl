

# --- Persistent context (self-contained; no core.config dependency) ---
import pathlib as _pathlib

_CONTEXT_DIR = _pathlib.Path.home() / ".config" / "cli-web-${app_name}"
_CONTEXT_FILE = _CONTEXT_DIR / "context.json"


def get_context_value(key: str) -> str | None:
    """Read a value from the persistent context file."""
    import json as _json

    if not _CONTEXT_FILE.exists():
        return None
    data = _json.loads(_CONTEXT_FILE.read_text())
    return data.get(key)


def set_context_value(key: str, value: str) -> None:
    """Write a value to the persistent context file."""
    import json as _json

    _CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    if _CONTEXT_FILE.exists():
        data = _json.loads(_CONTEXT_FILE.read_text())
    data[key] = value
    _CONTEXT_FILE.write_text(_json.dumps(data, indent=2))
