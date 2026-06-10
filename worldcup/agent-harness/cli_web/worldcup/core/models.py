"""Typed models that normalize raw ESPN / Odds API JSON into clean dicts.

The upstream JSON is deep and noisy; commands work with these flat models so
``--json`` output is stable and predictable regardless of upstream churn.
Each model has a ``from_*`` parser and ``to_dict()``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Match:
    id: str
    date: str
    name: str
    short_name: str
    status: str
    stage: str
    venue: str
    home: str
    away: str
    home_score: str | None
    away_score: str | None
    odds: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_event(cls, ev: dict) -> Match:
        comps = ev.get("competitions") or [{}]
        comp = comps[0]
        home = away = ""
        home_score = away_score = None
        for c in comp.get("competitors", []):
            name = (c.get("team") or {}).get("displayName", "")
            score = c.get("score")
            if c.get("homeAway") == "home":
                home, home_score = name, score
            else:
                away, away_score = name, score
        notes = comp.get("notes") or []
        stage = notes[0].get("headline", "") if notes else ""
        venue = (ev.get("venue") or comp.get("venue") or {}).get("fullName", "")
        return cls(
            id=str(ev.get("id", "")),
            date=ev.get("date", ""),
            name=ev.get("name", ""),
            short_name=ev.get("shortName", ""),
            status=((ev.get("status") or {}).get("type") or {}).get("description", ""),
            stage=stage,
            venue=venue,
            home=home,
            away=away,
            home_score=home_score,
            away_score=away_score,
            odds=_odds_line(comp.get("odds") or []),
        )


def _odds_line(odds: list) -> str:
    """One-line odds summary from ESPN's embedded provider entry.

    Knockout-bracket placeholder fixtures carry ``odds: [null]``, so guard
    against a missing/None first entry.
    """
    if not odds or not odds[0]:
        return ""
    o = odds[0]
    provider = (o.get("provider") or {}).get("displayName", "")
    bits = []
    if o.get("details"):
        bits.append(str(o["details"]))
    if o.get("overUnder") is not None:
        bits.append(f"O/U {o['overUnder']}")
    return f"{provider}: {' '.join(bits)}".strip().rstrip(":") if bits else provider


@dataclass
class Team:
    id: str
    name: str
    abbreviation: str
    location: str
    color: str
    logo: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_team(cls, t: dict) -> Team:
        logos = t.get("logos") or []
        return cls(
            id=str(t.get("id", "")),
            name=t.get("displayName", ""),
            abbreviation=t.get("abbreviation", ""),
            location=t.get("location", ""),
            color=t.get("color", ""),
            logo=logos[0].get("href", "") if logos else "",
        )


@dataclass
class Player:
    id: str
    name: str
    jersey: str
    position: str
    age: int | None
    nationality: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_athlete(cls, a: dict) -> Player:
        pos = a.get("position") or {}
        return cls(
            id=str(a.get("id", "")),
            name=a.get("fullName") or a.get("displayName", ""),
            jersey=a.get("jersey", ""),
            position=pos.get("abbreviation", "") if isinstance(pos, dict) else str(pos),
            age=a.get("age"),
            nationality=a.get("citizenship", ""),
        )


@dataclass
class StandingRow:
    group: str
    rank: str
    team: str
    played: str
    wins: str
    draws: str
    losses: str
    goals_for: str
    goals_against: str
    goal_diff: str
    points: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_entry(cls, group: str, entry: dict) -> StandingRow:
        stats = {s.get("name"): s.get("displayValue", "") for s in entry.get("stats", [])}
        return cls(
            group=group,
            rank=stats.get("rank", ""),
            team=(entry.get("team") or {}).get("displayName", ""),
            played=stats.get("gamesPlayed", ""),
            wins=stats.get("wins", ""),
            draws=stats.get("ties", ""),
            losses=stats.get("losses", ""),
            goals_for=stats.get("pointsFor", ""),
            goals_against=stats.get("pointsAgainst", ""),
            goal_diff=stats.get("pointDifferential", ""),
            points=stats.get("points", ""),
        )


@dataclass
class OddsMatch:
    id: str
    commence_time: str
    home: str
    away: str
    bookmakers: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_event(cls, ev: dict) -> OddsMatch:
        books = []
        for b in ev.get("bookmakers", []):
            prices: dict[str, float] = {}
            for market in b.get("markets", []):
                if market.get("key") == "h2h":
                    for outcome in market.get("outcomes", []):
                        prices[outcome.get("name", "")] = outcome.get("price")
            books.append({"bookmaker": b.get("title", b.get("key", "")), "h2h": prices})
        return cls(
            id=str(ev.get("id", "")),
            commence_time=ev.get("commence_time", ""),
            home=ev.get("home_team", ""),
            away=ev.get("away_team", ""),
            bookmakers=books,
        )
