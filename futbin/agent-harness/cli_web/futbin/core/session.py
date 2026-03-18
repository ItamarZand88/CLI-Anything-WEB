"""Session state management for cli-web-futbin.

Loads persistent config from ~/.config/cli-web-futbin/config.json.
Used by commands to get default year/platform without explicit flags.
"""
from ..utils.helpers import get_config_value, set_config_value


class FutbinSession:
    """Runtime session with persistent config backing."""

    @property
    def year(self) -> int:
        val = get_config_value("year")
        return int(val) if val is not None else 26

    @property
    def platform(self) -> str:
        val = get_config_value("platform")
        return str(val) if val else "ps"

    def set_year(self, year: int) -> None:
        set_config_value("year", year)

    def set_platform(self, platform: str) -> None:
        set_config_value("platform", platform)


_session = FutbinSession()


def get_session() -> FutbinSession:
    return _session
