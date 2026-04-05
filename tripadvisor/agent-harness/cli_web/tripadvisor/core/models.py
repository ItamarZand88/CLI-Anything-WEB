"""Data models for cli-web-tripadvisor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Location:
    """A TripAdvisor location (destination) from TypeAheadJson."""

    geo_id: str
    name: str
    url: str
    type: str = "GEO"  # GEO, HOTEL, EATERY, ATTRACTION, etc.
    coords: Optional[str] = None  # "lat,lon"
    parent_name: Optional[str] = None
    geo_name: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "geo_id": self.geo_id,
            "name": self.name,
            "url": self.url,
            "type": self.type,
            "coords": self.coords,
            "parent_name": self.parent_name,
            "geo_name": self.geo_name,
        }


@dataclass
class Hotel:
    """A TripAdvisor hotel from listing or detail page."""

    id: str              # numeric d-number (e.g. "229968")
    name: str
    url: str             # full TripAdvisor URL
    rating: Optional[str] = None
    review_count: Optional[int] = None
    price_range: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    telephone: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    image: Optional[str] = None
    amenities: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "rating": self.rating,
            "review_count": self.review_count,
            "price_range": self.price_range,
            "address": self.address,
            "city": self.city,
            "country": self.country,
            "telephone": self.telephone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "image": self.image,
            "amenities": self.amenities,
        }


@dataclass
class Restaurant:
    """A TripAdvisor restaurant from listing or detail page."""

    id: str
    name: str
    url: str
    rating: Optional[str] = None
    review_count: Optional[int] = None
    price_range: Optional[str] = None
    cuisines: list = field(default_factory=list)
    address: Optional[str] = None
    city: Optional[str] = None
    telephone: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    image: Optional[str] = None
    opening_hours: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "rating": self.rating,
            "review_count": self.review_count,
            "price_range": self.price_range,
            "cuisines": self.cuisines,
            "address": self.address,
            "city": self.city,
            "telephone": self.telephone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "image": self.image,
            "opening_hours": self.opening_hours,
        }


@dataclass
class Attraction:
    """A TripAdvisor attraction from listing or detail page."""

    id: str
    name: str
    url: str
    rating: Optional[str] = None
    review_count: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    telephone: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    image: Optional[str] = None
    opening_hours: list = field(default_factory=list)
    description: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "rating": self.rating,
            "review_count": self.review_count,
            "address": self.address,
            "city": self.city,
            "telephone": self.telephone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "image": self.image,
            "opening_hours": self.opening_hours,
            "description": self.description,
        }
