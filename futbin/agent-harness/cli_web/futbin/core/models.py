from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Position(Enum):
    GK = "GK"
    CB = "CB"
    LB = "LB"
    RB = "RB"
    LWB = "LWB"
    RWB = "RWB"
    CDM = "CDM"
    CM = "CM"
    CAM = "CAM"
    RM = "RM"
    LM = "LM"
    RW = "RW"
    LW = "LW"
    RF = "RF"
    LF = "LF"
    CF = "CF"
    ST = "ST"


class Platform(Enum):
    PS = "ps"
    PC = "pc"


@dataclass
class Player:
    id: int
    name: str
    position: str
    version: str
    rating: int
    club: str
    nation: str
    year: int
    url: str
    ps_price: Optional[int] = None
    xbox_price: Optional[int] = None
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "version": self.version,
            "rating": self.rating,
            "club": self.club,
            "nation": self.nation,
            "year": self.year,
            "url": f"https://www.futbin.com{self.url}",
            "ps_price": self.ps_price,
            "xbox_price": self.xbox_price,
            "stats": self.stats,
        }


@dataclass
class SBC:
    id: int
    name: str
    category: str
    reward: str
    expires: str
    year: int
    cost_ps: Optional[int] = None
    cost_xbox: Optional[int] = None
    repeatable: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "reward": self.reward,
            "expires": self.expires,
            "year": self.year,
            "cost_ps": self.cost_ps,
            "cost_xbox": self.cost_xbox,
            "repeatable": self.repeatable,
            "url": f"https://www.futbin.com/{self.year}/squad-building-challenge/{self.id}",
        }


@dataclass
class Evolution:
    id: int
    name: str
    category: str
    expires: str
    year: int
    unlock_time: str = ""
    repeatable: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "expires": self.expires,
            "year": self.year,
            "unlock_time": self.unlock_time,
            "repeatable": self.repeatable,
            "url": f"https://www.futbin.com/evolutions/{self.id}",
        }


@dataclass
class SBCDetail:
    """Full SBC with structured requirements and rewards."""
    id: str
    name: str
    category: str = ""
    reward: str = ""
    expires: str = ""
    year: int = 26
    cost_ps: str = ""
    cost_xbox: str = ""
    repeatable: bool = False
    requirements: list = field(default_factory=list)
    description: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "reward": self.reward, "expires": self.expires, "year": self.year,
            "cost_ps": self.cost_ps, "cost_xbox": self.cost_xbox,
            "repeatable": self.repeatable, "requirements": self.requirements,
            "description": self.description, "url": self.url,
        }


@dataclass
class EvolutionDetail:
    """Full evolution with structured requirements and upgrades."""
    id: str
    name: str
    category: str = ""
    expires: str = ""
    year: int = 26
    requirements: list = field(default_factory=list)
    upgrades: list = field(default_factory=list)
    description: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "expires": self.expires, "year": self.year,
            "requirements": self.requirements, "upgrades": self.upgrades,
            "description": self.description, "url": self.url,
        }


@dataclass
class PlayerComparison:
    """Side-by-side comparison of two players."""
    player1: "Player"
    player2: "Player"
    stat_diffs: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "player1": self.player1.to_dict(),
            "player2": self.player2.to_dict(),
            "stat_diffs": self.stat_diffs,
        }


@dataclass
class MarketItem:
    name: str
    last: str
    change_pct: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "last": self.last,
            "change_pct": self.change_pct,
        }
