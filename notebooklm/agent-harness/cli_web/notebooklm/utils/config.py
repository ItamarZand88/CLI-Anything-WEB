"""Configuration management for cli-web-notebooklm."""
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "cli-web-notebooklm"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get(key: str, default=None):
    return load_config().get(key, default)


def set_value(key: str, value):
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
