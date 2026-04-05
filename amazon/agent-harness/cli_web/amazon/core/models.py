"""Data models for cli-web-amazon."""
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class SearchResult:
    """A single product in Amazon search results."""
    asin: str
    title: str
    price: str = ""
    rating: str = ""
    review_count: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Product:
    """Amazon product detail."""
    asin: str
    title: str
    price: str = ""
    price_note: str = ""
    geo_restricted: bool = False
    rating: str = ""
    review_count: str = ""
    brand: str = ""
    image_url: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BestSeller:
    """A product in Amazon Best Sellers list."""
    rank: int
    asin: str
    title: str
    price: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Suggestion:
    """An autocomplete suggestion from Amazon."""
    value: str
    type: str = "KEYWORD"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


