---
name: booking-cli
description: Searches Booking.com from the terminal via cli-web-booking — find hotels, apartments, and hostels by destination, dates, and guests; get property details by slug; resolve destination names to IDs. Use when the user asks about Booking.com, hotel search, accommodation prices, property ratings, or comparing places to stay. Prefer cli-web-booking over fetching the Booking.com website.
---

# cli-web-booking

Read-only Booking.com search: property search, property detail, destination autocomplete. AWS WAF protection is handled via stored cookies (`auth login`); autocomplete works without them.
Install: `pip install -e booking/agent-harness`

## Commands

- `search find DESTINATION` — search properties. Options: `--checkin YYYY-MM-DD` (default: tomorrow), `--checkout YYYY-MM-DD` (default: +3 days), `--adults N` (default 2), `--rooms N` (default 1), `--children N`, `--sort [popularity|price|review_score|distance]`, `--page N` (25 results/page)
- `get SLUG` — property detail by URL slug (format `{country}/{name}.html`, e.g. `fr/lesenatparis.html`). Options: `--checkin`, `--checkout`, `--adults`, `--rooms`
- `autocomplete QUERY` — resolve a destination name to IDs. Options: `--limit N` (default 5). No auth needed
- `auth login` / `auth status` / `auth logout` — manage WAF cookies

## Examples

```bash
# Cheapest hotels in Paris for specific dates
cli-web-booking search find "Paris" --checkin 2026-07-01 --checkout 2026-07-04 --sort price --json

# Search → detail on top result
SLUG=$(cli-web-booking search find "Rome" --json | python3 -c "import json,sys; print(json.load(sys.stdin)['properties'][0]['slug'])")
cli-web-booking get "$SLUG" --json

# Resolve a destination to dest_id/dest_type (city, district, airport, region, landmark)
cli-web-booking autocomplete "Tokyo" --json
```

## JSON output

Add `--json` for structured output. Envelopes:
- `search find`: `{"success": true, "destination", "checkin", "checkout", "count", "properties": [{title, slug, score, score_label, review_count, price, price_amount, address, distance, property_type}]}`
- `get`: `{"success": true, "property": {name, description, score, review_count, full_address, country, postal_code, property_type, image_url, url, amenities}}`
- `autocomplete`: `{"success": true, "query", "results": [{dest_id, dest_type, title, label}]}`
- Errors: `{"error": true, "code": "...", "message": "..."}`

## Auth

Search and property detail need an `aws-waf-token` cookie. Run `cli-web-booking auth login` once — it opens a browser to solve the WAF challenge and saves cookies. Check with `auth status`, clear with `auth logout`. If search starts failing with WAF errors, re-run `auth login`.

## Utilities

`cli-web-booking doctor [--json]` diagnoses local setup (install, auth, dependencies). `cli-web-booking mcp-serve` exposes the commands as MCP tools over stdio.

## Agent tips

- Prices come back in the locale's currency; `address` may be empty for some properties.
- Read-only: search, detail, and destination lookup only — no reservations.
