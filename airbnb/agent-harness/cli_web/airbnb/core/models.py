"""Data models for cli-web-airbnb."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Listing:
    """An Airbnb stay listing (search result or detail)."""

    id: str
    id_b64: str
    name: str
    url: str
    rating: str | None = None
    price: str | None = None
    price_qualifier: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    badges: list = field(default_factory=list)
    room_type: str | None = None
    location: str | None = None
    review_count: int | None = None
    host_name: str | None = None
    description: str | None = None
    amenities: list = field(default_factory=list)
    bedrooms: int | None = None
    bathrooms: float | None = None
    max_guests: int | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "id_b64": self.id_b64,
            "name": self.name,
            "url": self.url,
            "rating": self.rating,
            "price": self.price,
            "price_qualifier": self.price_qualifier,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "badges": self.badges,
            "room_type": self.room_type,
            "location": self.location,
            "review_count": self.review_count,
            "host_name": self.host_name,
            "description": self.description,
            "amenities": self.amenities,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "max_guests": self.max_guests,
        }


@dataclass
class Review:
    """A single Airbnb guest review."""

    id: str
    rating: int | None = None
    date: str | None = None
    reviewer: str | None = None
    reviewer_location: str | None = None
    comment: str | None = None
    host_response: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rating": self.rating,
            "date": self.date,
            "reviewer": self.reviewer,
            "reviewer_location": self.reviewer_location,
            "comment": self.comment,
            "host_response": self.host_response,
        }


@dataclass
class AvailabilityDay:
    """A single day in an Airbnb availability calendar."""

    date: str
    available: bool = False
    checkin: bool = False
    checkout: bool = False
    bookable: bool = False
    min_nights: int | None = None
    max_nights: int | None = None
    price: str | None = None

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "available": self.available,
            "checkin": self.checkin,
            "checkout": self.checkout,
            "bookable": self.bookable,
            "min_nights": self.min_nights,
            "max_nights": self.max_nights,
            "price": self.price,
        }


@dataclass
class AvailabilityMonth:
    """A single month in an Airbnb availability calendar."""

    month: int
    year: int
    days: list[AvailabilityDay] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "month": self.month,
            "year": self.year,
            "days": [d.to_dict() for d in self.days],
        }


@dataclass
class LocationSuggestion:
    """An autocomplete location suggestion."""

    query: str
    place_id: str | None = None
    display: str | None = None
    acp_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "place_id": self.place_id,
            "display": self.display or self.query,
            "acp_id": self.acp_id,
        }
