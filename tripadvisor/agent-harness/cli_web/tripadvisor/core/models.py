"""Data models for cli-web-tripadvisor."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Location:
    """A TripAdvisor location (destination) from TypeAheadJson."""

    geo_id: str
    name: str
    url: str
    type: str = "GEO"  # GEO, HOTEL, EATERY, ATTRACTION, etc.
    coords: str | None = None  # "lat,lon"
    parent_name: str | None = None
    geo_name: str | None = None

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

    id: str  # numeric d-number (e.g. "229968")
    name: str
    url: str  # full TripAdvisor URL
    rating: str | None = None
    review_count: int | None = None
    price_range: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    telephone: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    image: str | None = None
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
    rating: str | None = None
    review_count: int | None = None
    price_range: str | None = None
    cuisines: list = field(default_factory=list)
    address: str | None = None
    city: str | None = None
    telephone: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    image: str | None = None
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
    rating: str | None = None
    review_count: int | None = None
    address: str | None = None
    city: str | None = None
    telephone: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    image: str | None = None
    opening_hours: list = field(default_factory=list)
    description: str | None = None

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
