"""Data models for FUTBIN CLI."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Player:
    id: int
    name: str
    rating: int
    position: str
    version: str = ""
    club: str = ""
    league: str = ""
    nation: str = ""
    price_ps: Optional[int] = None
    price_pc: Optional[int] = None
    futbin_rating: Optional[float] = None
    skill_moves: Optional[int] = None
    weak_foot: Optional[int] = None
    foot: str = ""
    pac: Optional[int] = None
    sho: Optional[int] = None
    pas: Optional[int] = None
    dri: Optional[int] = None
    defense: Optional[int] = None
    phy: Optional[int] = None
    igs: Optional[int] = None
    popularity: Optional[int] = None
    body: str = ""
    slug: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != ""}


@dataclass
class PlayerSearchResult:
    id: int
    name: str
    position: str
    version: str
    rating: str
    url: str

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class PricePoint:
    timestamp: int
    price: int

    def to_dict(self) -> dict:
        return {"timestamp": self.timestamp, "price": self.price}


@dataclass
class PriceHistory:
    player_id: int
    player_name: str
    platform: str
    prices: list[PricePoint] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "platform": self.platform,
            "prices": [p.to_dict() for p in self.prices],
        }


@dataclass
class SBC:
    name: str
    url: str
    category: str = ""
    cost: str = ""
    expires: str = ""
    repeatable: bool = False
    num_challenges: int = 0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != "" and v != 0 and v is not False}


@dataclass
class MarketIndex:
    name: str
    value_ps: Optional[float] = None
    value_pc: Optional[float] = None
    change_pct_ps: Optional[float] = None
    change_pct_pc: Optional[float] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Evolution:
    name: str
    url: str
    category: str = ""
    expires: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != ""}
