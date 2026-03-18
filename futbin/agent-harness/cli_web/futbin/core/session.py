"""Session state for FUTBIN CLI."""
from __future__ import annotations

from typing import Any, Optional

from cli_web.futbin.utils.config import load_config, save_config

DEFAULT_YEAR = 26


class FutbinSession:
    """Tracks CLI session state: current year, platform, output preferences."""

    def __init__(self):
        self._config = load_config()

    @property
    def year(self) -> int:
        return int(self._config.get("year", DEFAULT_YEAR))

    @year.setter
    def year(self, value: int) -> None:
        self._config["year"] = value
        self._save()

    @property
    def platform(self) -> str:
        """ps or xbox."""
        return self._config.get("platform", "ps")

    @platform.setter
    def platform(self, value: str) -> None:
        if value not in ("ps", "xbox"):
            raise ValueError("Platform must be 'ps' or 'xbox'")
        self._config["platform"] = value
        self._save()

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value
        self._save()

    def _save(self) -> None:
        save_config(self._config)

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "platform": self.platform,
        }
