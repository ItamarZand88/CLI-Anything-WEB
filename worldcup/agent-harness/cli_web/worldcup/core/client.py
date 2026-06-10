"""HTTP client for cli-web-worldcup.

Two read-only upstreams, both plain JSON over httpx:

- **ESPN** (``site.api.espn.com``) — public, no auth. ``fifa.world`` is the
  men's FIFA World Cup. Fixtures, teams, rosters, and group standings.
- **The Odds API** (``api.the-odds-api.com``) — bookmaker odds, gated by a
  free API key passed as the ``apiKey`` query param (not a login/session).
  Only the ``odds`` command needs it; everything else works with no key.
"""

from __future__ import annotations

import httpx

from .exceptions import AuthError, NetworkError, raise_for_status

# ESPN public JSON API. The men's World Cup league slug is ``fifa.world``.
ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
ESPN_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"

# The Odds API (https://the-odds-api.com). Sport key for the men's World Cup.
ODDS_API = "https://api.the-odds-api.com/v4"
ODDS_SPORT_KEY = "soccer_fifa_world_cup"


class WorldcupClient:
    """Read-only client for ESPN World Cup data + optional Odds API odds."""

    def __init__(self, odds_api_key: str | None = None):
        self._odds_api_key = odds_api_key
        self._client = httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0),
            headers={"User-Agent": "cli-web-worldcup/0.1.0"},
            follow_redirects=True,
        )

    def _get(self, url: str, params: dict | None = None) -> dict:
        try:
            resp = self._client.get(url, params=params)
        except httpx.ConnectError as exc:
            raise NetworkError(f"Connection failed: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}") from exc
        raise_for_status(resp)
        try:
            return resp.json()
        except ValueError as exc:
            raise NetworkError(f"Invalid JSON from {url}: {exc}") from exc

    # ── ESPN: fixtures ────────────────────────────────────────────────
    def scoreboard(self, dates: str | None = None) -> dict:
        """Raw scoreboard. ``dates`` is ``YYYYMMDD`` or ``YYYYMMDD-YYYYMMDD``."""
        return self._get(f"{ESPN_SITE}/scoreboard", {"dates": dates} if dates else None)

    def event_summary(self, event_id: str) -> dict:
        """Full detail for one match (lineups, odds providers, head-to-head)."""
        return self._get(f"{ESPN_SITE}/summary", {"event": event_id})

    # ── ESPN: teams & players ─────────────────────────────────────────
    def teams(self) -> dict:
        return self._get(f"{ESPN_SITE}/teams")

    def team(self, team_id: str) -> dict:
        return self._get(f"{ESPN_SITE}/teams/{team_id}")

    def roster(self, team_id: str) -> dict:
        return self._get(f"{ESPN_SITE}/teams/{team_id}/roster")

    # ── ESPN: standings ───────────────────────────────────────────────
    def standings(self) -> dict:
        return self._get(ESPN_STANDINGS)

    # ── The Odds API ──────────────────────────────────────────────────
    def odds(
        self,
        regions: str = "us",
        markets: str = "h2h",
        odds_format: str = "decimal",
        sport_key: str = ODDS_SPORT_KEY,
    ) -> list:
        """Bookmaker odds for World Cup matches. Requires an Odds API key."""
        if not self._odds_api_key:
            raise AuthError(
                "Odds require an API key. Get a free key at https://the-odds-api.com "
                "and set CLI_WEB_WORLDCUP_ODDS_API_KEY (or pass --api-key).",
                recoverable=False,
            )
        return self._get(  # type: ignore[return-value]
            f"{ODDS_API}/sports/{sport_key}/odds",
            {
                "apiKey": self._odds_api_key,
                "regions": regions,
                "markets": markets,
                "oddsFormat": odds_format,
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> WorldcupClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
