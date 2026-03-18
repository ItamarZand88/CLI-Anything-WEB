"""Session state management for FUTBIN CLI."""

import json
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "cli-web-futbin"
SESSION_FILE = CONFIG_DIR / "session.json"


class Session:
    """Manages persistent session state like preferred platform and output format."""

    def __init__(self):
        self.platform: str = "ps"
        self.year: str = "26"
        self.output_format: str = "table"
        self._load()

    def _load(self):
        if SESSION_FILE.exists():
            try:
                data = json.loads(SESSION_FILE.read_text())
                self.platform = data.get("platform", self.platform)
                self.year = data.get("year", self.year)
                self.output_format = data.get("output_format", self.output_format)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps({
            "platform": self.platform,
            "year": self.year,
            "output_format": self.output_format,
        }, indent=2))

    def set_platform(self, platform: str):
        if platform not in ("ps", "pc"):
            raise ValueError(f"Invalid platform: {platform}. Use 'ps' or 'pc'.")
        self.platform = platform
        self.save()

    def set_year(self, year: str):
        self.year = year
        self.save()
