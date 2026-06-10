"""Unit tests for cli-web-worldcup — mocked HTTP, no network.

Model parsing is checked against trimmed real ESPN/Odds fixtures captured
from the live APIs (tests/fixtures/).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest
from cli_web.worldcup.core.client import WorldcupClient
from cli_web.worldcup.core.exceptions import (
    AuthError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from cli_web.worldcup.core.models import Match, OddsMatch, Player, StandingRow, Team
from cli_web.worldcup.utils.helpers import odds_api_key, resolve_team

pytestmark = pytest.mark.unit

FIX = Path(__file__).parent / "fixtures"


def _fix(name: str) -> dict:
    return json.loads((FIX / name).read_text())


# ── model parsing (against real captured shapes) ─────────────────────────────


def test_match_from_event():
    sb = _fix("scoreboard.json")
    m = Match.from_event(sb["events"][0])
    assert m.home and m.away
    assert m.status == "Scheduled"
    assert m.date.startswith("2026-")
    assert {m.home, m.away} == {"Mexico", "South Africa"}
    d = m.to_dict()
    assert set(d) >= {"id", "home", "away", "status", "odds"}


def test_match_odds_line_from_espn():
    sb = _fix("scoreboard.json")
    m = Match.from_event(sb["events"][0])
    # The first event carries a DraftKings line in the fixture.
    assert "DraftKings" in m.odds or m.odds == ""


def test_match_venue_prefers_competition_full_name():
    # Event-level venue has only displayName; competition-level has fullName.
    ev = {
        "id": "1",
        "venue": {"displayName": "Short Name"},
        "competitions": [
            {
                "competitors": [],
                "venue": {"fullName": "Estadio Banorte"},
            }
        ],
    }
    assert Match.from_event(ev).venue == "Estadio Banorte"


def test_match_venue_falls_back_to_event_display_name():
    ev = {"id": "1", "venue": {"displayName": "Estadio Akron"}, "competitions": [{}]}
    assert Match.from_event(ev).venue == "Estadio Akron"


def test_odds_line_omits_empty_provider_colon():
    from cli_web.worldcup.core.models import _odds_line

    # Provider missing → no leading ": " (the bug fixed here).
    line = _odds_line([{"details": "KOR +170", "overUnder": 2.5}])
    assert line == "KOR +170 O/U 2.5"
    # Provider present → "Provider: ...".
    line = _odds_line([{"provider": {"displayName": "DraftKings"}, "details": "MEX -250"}])
    assert line == "DraftKings: MEX -250"


def test_team_from_team():
    teams = _fix("teams.json")["sports"][0]["leagues"][0]["teams"]
    t = Team.from_team(teams[0]["team"])
    assert t.id and t.name and len(t.abbreviation) == 3


def test_player_from_athlete():
    a = _fix("roster.json")["athletes"][0]
    p = Player.from_athlete(a)
    assert p.name and p.position
    assert isinstance(p.to_dict(), dict)


def test_standing_row_from_entry():
    g = _fix("standings.json")["children"][0]
    row = StandingRow.from_entry(g["name"], g["standings"]["entries"][0])
    assert row.group == g["name"]
    assert row.team
    assert row.points != "" and row.rank != ""


def test_odds_match_from_event():
    ev = _fix("odds.json")[0]
    om = OddsMatch.from_event(ev)
    assert om.home == "Mexico" and om.away == "South Africa"
    assert om.bookmakers[0]["bookmaker"] == "DraftKings"
    assert om.bookmakers[0]["h2h"]["Mexico"] == 1.8


# ── resolve_team ─────────────────────────────────────────────────────────────


@pytest.fixture()
def team_dicts():
    return [
        {"id": "203", "name": "Mexico", "abbreviation": "MEX"},
        {"id": "467", "name": "South Africa", "abbreviation": "RSA"},
        {"id": "624", "name": "Algeria", "abbreviation": "ALG"},
    ]


def test_resolve_team_by_code(team_dicts):
    assert resolve_team("MEX", team_dicts)["id"] == "203"


def test_resolve_team_by_id(team_dicts):
    assert resolve_team("467", team_dicts)["name"] == "South Africa"


def test_resolve_team_by_name_case_insensitive(team_dicts):
    assert resolve_team("mexico", team_dicts)["abbreviation"] == "MEX"


def test_resolve_team_unknown_raises(team_dicts):
    with pytest.raises(NotFoundError):
        resolve_team("Narnia", team_dicts)


def test_resolve_team_ambiguous_raises():
    teams = [
        {"id": "1", "name": "South Korea", "abbreviation": "KOR"},
        {"id": "2", "name": "South Africa", "abbreviation": "RSA"},
    ]
    with pytest.raises(NotFoundError, match="Ambiguous"):
        resolve_team("South", teams)


# ── odds API key resolution ──────────────────────────────────────────────────


def test_odds_api_key_prefers_explicit(monkeypatch):
    monkeypatch.setenv("CLI_WEB_WORLDCUP_ODDS_API_KEY", "from-env")
    assert odds_api_key("from-flag") == "from-flag"


def test_odds_api_key_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("CLI_WEB_WORLDCUP_ODDS_API_KEY", "from-env")
    assert odds_api_key(None) == "from-env"


def test_odds_without_key_raises_auth_error():
    with WorldcupClient() as client, pytest.raises(AuthError):
        client.odds()


# ── HTTP status mapping (mock httpx) ─────────────────────────────────────────


class _Resp:
    def __init__(self, status_code, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


@pytest.mark.parametrize(
    "status,exc",
    [
        (401, AuthError),
        (403, AuthError),
        (404, NotFoundError),
        (429, RateLimitError),
        (500, ServerError),
        (503, ServerError),
    ],
)
def test_status_maps_to_typed_exception(status, exc):
    with WorldcupClient() as client:
        with mock.patch.object(client._client, "get", return_value=_Resp(status, text="x")):
            with pytest.raises(exc):
                client.scoreboard()


def test_rate_limit_carries_retry_after():
    with WorldcupClient() as client:
        resp = _Resp(429, headers={"Retry-After": "30"}, text="slow down")
        with mock.patch.object(client._client, "get", return_value=resp):
            with pytest.raises(RateLimitError) as ei:
                client.teams()
    assert ei.value.retry_after == 30.0


def test_scoreboard_parses_json_on_success():
    with WorldcupClient() as client:
        resp = _Resp(200, payload={"events": []})
        with mock.patch.object(client._client, "get", return_value=resp):
            assert client.scoreboard() == {"events": []}
