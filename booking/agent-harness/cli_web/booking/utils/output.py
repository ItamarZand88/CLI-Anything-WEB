"""Output formatting for cli-web-booking."""

from __future__ import annotations

from ..core.models import Destination, Property, PropertyDetail


def format_property_row(p: Property) -> list[str]:
    """Format a property for table display."""
    score = f"{p.score:.1f}" if p.score else "-"
    label = p.score_label or ""
    reviews = str(p.review_count) if p.review_count else "-"
    return [p.title[:35], score, label, reviews, p.price or "-", p.address[:25]]


def format_destination_row(d: Destination) -> list[str]:
    """Format a destination for table display."""
    return [d.title, d.dest_type, d.dest_id, d.label[:45]]


def format_property_detail(detail: PropertyDetail) -> str:
    """Format property detail for human-readable display."""
    lines = []
    lines.append(f"  {detail.name}")
    if detail.property_type:
        lines.append(f"  Type: {detail.property_type}")
    if detail.score is not None:
        lines.append(f"  Score: {detail.score}/10 ({detail.review_count} reviews)")
    if detail.full_address:
        lines.append(f"  Address: {detail.full_address}")
    if detail.country:
        lines.append(f"  Country: {detail.country}")
    if detail.description:
        desc = detail.description[:200]
        if len(detail.description) > 200:
            desc += "..."
        lines.append(f"  Description: {desc}")
    if detail.amenities:
        lines.append(f"  Amenities: {', '.join(detail.amenities[:10])}")
    if detail.url:
        lines.append(f"  URL: {detail.url}")
    return "\n".join(lines)
