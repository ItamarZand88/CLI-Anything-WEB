"""Data models for Booking.com API responses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Destination:
    """A resolved destination from autocomplete."""

    dest_id: str
    dest_type: str  # city, district, airport, region, landmark
    title: str
    label: str

    @classmethod
    def from_graphql(cls, result: dict) -> Destination:
        meta = result.get("metaData", {})
        display = result.get("displayInfo", {})
        raw_id = meta.get("autocompleteResultId", "")
        parts = raw_id.split("/", 1)
        return cls(
            dest_id=parts[1] if len(parts) == 2 else raw_id,
            dest_type=parts[0] if len(parts) == 2 else "unknown",
            title=display.get("title", ""),
            label=display.get("label", ""),
        )

    def to_dict(self) -> dict:
        return {
            "dest_id": self.dest_id,
            "dest_type": self.dest_type,
            "title": self.title,
            "label": self.label,
        }


@dataclass
class Property:
    """A property from search results."""

    title: str
    slug: str
    score: float | None = None
    score_label: str = ""
    review_count: int = 0
    price: str = ""
    price_amount: float | None = None
    address: str = ""
    distance: str = ""
    property_type: str = ""
    star_rating: int | None = None

    def to_dict(self) -> dict:
        d = {
            "title": self.title,
            "slug": self.slug,
            "score": self.score,
            "score_label": self.score_label,
            "review_count": self.review_count,
            "price": self.price,
            "address": self.address,
            "distance": self.distance,
            "property_type": self.property_type,
        }
        if self.price_amount is not None:
            d["price_amount"] = self.price_amount
        if self.star_rating is not None:
            d["star_rating"] = self.star_rating
        return d

    @classmethod
    def parse_score_text(cls, text: str) -> tuple[float | None, str, int]:
        """Parse score text like 'Scored 8.6  8.6 Excellent   677 reviews'."""
        score = None
        label = ""
        count = 0
        score_match = re.search(r"(\d+\.?\d*)", text)
        if score_match:
            score = float(score_match.group(1))
        for lbl in ("Exceptional", "Wonderful", "Superb", "Excellent",
                     "Very Good", "Good", "Pleasant", "Review score"):
            if lbl.lower() in text.lower():
                label = lbl
                break
        count_match = re.search(r"([\d,]+)\s*review", text)
        if count_match:
            count = int(count_match.group(1).replace(",", ""))
        return score, label, count

    @classmethod
    def parse_price_text(cls, text: str) -> tuple[str, float | None]:
        """Parse price text like '₪ 2,945' or 'US$150'."""
        amount = None
        nums = re.findall(r"[\d,]+\.?\d*", text)
        if nums:
            amount = float(nums[-1].replace(",", ""))
        return text.strip(), amount


@dataclass
class PropertyDetail:
    """Detailed property info from hotel detail page (JSON-LD)."""

    name: str
    slug: str
    description: str = ""
    image_url: str = ""
    url: str = ""
    score: float | None = None
    review_count: int = 0
    full_address: str = ""
    postal_code: str = ""
    country: str = ""
    latitude: float | None = None
    longitude: float | None = None
    property_type: str = ""
    price_range: str | None = None
    checkin_time: str = ""
    checkout_time: str = ""
    amenities: list[str] = field(default_factory=list)

    @classmethod
    def from_json_ld(cls, data: dict, slug: str) -> PropertyDetail:
        address = data.get("address", {})
        rating = data.get("aggregateRating", {})
        geo = data.get("geo", {})
        return cls(
            name=data.get("name", ""),
            slug=slug,
            description=data.get("description", ""),
            image_url=data.get("image", ""),
            url=data.get("url", ""),
            score=rating.get("ratingValue"),
            review_count=rating.get("reviewCount", 0),
            full_address=address.get("streetAddress", ""),
            postal_code=address.get("postalCode", ""),
            country=address.get("addressCountry", ""),
            latitude=geo.get("latitude"),
            longitude=geo.get("longitude"),
            property_type=data.get("@type", ""),
            price_range=data.get("priceRange"),
            checkin_time=data.get("checkinTime", ""),
            checkout_time=data.get("checkoutTime", ""),
            amenities=[
                a.get("name", a) if isinstance(a, dict) else str(a)
                for a in data.get("amenityFeature", [])
            ],
        )

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "image_url": self.image_url,
            "url": self.url,
            "score": self.score,
            "review_count": self.review_count,
            "full_address": self.full_address,
            "postal_code": self.postal_code,
            "country": self.country,
            "property_type": self.property_type,
        }
        if self.latitude is not None:
            d["latitude"] = self.latitude
            d["longitude"] = self.longitude
        if self.amenities:
            d["amenities"] = self.amenities
        if self.checkin_time:
            d["checkin_time"] = self.checkin_time
        if self.checkout_time:
            d["checkout_time"] = self.checkout_time
        return d
