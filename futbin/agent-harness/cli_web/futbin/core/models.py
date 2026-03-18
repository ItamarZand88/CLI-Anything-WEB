from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


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
