---
name: booking-cli
description: Use cli-web-booking to search Booking.com for hotels, apartments, hostels, and accommodations by destination, dates, and filters. Invoke this skill whenever the user asks about Booking.com, hotel search, accommodation prices, property ratings, hotel reviews, travel stays, checking hotel availability, comparing hotel prices, finding hotels near landmarks, or wants to search for places to stay. Also trigger for destination resolution (city/airport/district IDs). Always prefer cli-web-booking over manually fetching the Booking.com website.
---

# cli-web-booking

Search Booking.com for hotels, apartments, and accommodations from the command line. Installed at: `cli-web-booking`.

## Quick Start

```bash
# Search hotels in a city
cli-web-booking search find "Paris" --checkin 2026-04-01 --checkout 2026-04-04 --json

# Get property details
cli-web-booking get fr/lesenatparis.html --json

# Resolve destination names (no auth needed)
cli-web-booking autocomplete "Tokyo" --json
```

Always use `--json` when parsing output programmatically.

---

## Commands

### `search find <destination>`
Search properties by destination and dates.

```bash
cli-web-booking search find "London" --checkin 2026-04-01 --checkout 2026-04-04 --json
```

**Key options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--checkin` | Check-in date (YYYY-MM-DD) | Tomorrow |
| `--checkout` | Check-out date (YYYY-MM-DD) | +3 days |
| `--adults N` | Number of adults | 2 |
| `--rooms N` | Number of rooms | 1 |
| `--children N` | Number of children | 0 |
| `--sort` | `popularity`, `price`, `review_score`, `distance` | popularity |
| `--page N` | Results page (25 per page) | 1 |

**Output fields:** `title`, `slug`, `score`, `score_label`, `review_count`, `price`, `price_amount`, `address`, `distance`, `property_type`

**Response envelope:** `{"success", "destination", "checkin", "checkout", "count", "properties": [...]}`

Note: `address` may be empty for some properties. Prices reflect user's locale currency.

### `get <slug>`
Get detailed property information from hotel page.

```bash
cli-web-booking get fr/lesenatparis.html --json
```

**Output fields:** `name`, `description`, `score`, `review_count`, `full_address`, `country`, `postal_code`, `property_type`, `image_url`, `url`, `amenities`

### `autocomplete <query>`
Resolve destination names to Booking.com IDs. No auth needed.

```bash
cli-web-booking autocomplete "Paris" --json
```

**Output fields:** `dest_id`, `dest_type` (city/district/airport/region/landmark), `title`, `label`

### `auth login`
Open browser to solve AWS WAF challenge and save cookies.

### `auth status`
Check if WAF cookies are available.

### `auth logout`
Clear stored WAF cookies.

---

## Agent Patterns

```bash
# Find cheapest hotels in Paris
cli-web-booking search find "Paris" --sort price --checkin 2026-04-01 --checkout 2026-04-04 --json

# Get details of a specific hotel from search results
SLUG=$(cli-web-booking search find "Rome" --json | python -c "import json,sys; print(json.load(sys.stdin)['properties'][0]['slug'])")
cli-web-booking get "$SLUG" --json

# Resolve destination ID for scripting
cli-web-booking autocomplete "Tokyo" --json | python -c "import json,sys; d=json.load(sys.stdin); print(d['results'][0]['dest_id'])"
```

---

## Notes

- **Auth**: WAF cookies required for search and property detail. Autocomplete works without auth.
- **Setup**: Run `cli-web-booking auth login` once to solve the WAF challenge.
- **Prices**: Currency depends on user's location. Use `selected_currency=USD` in manual requests.
- **Rate limiting**: No explicit limits, but add delays between rapid requests.
- **Read-only**: No write operations — search, browse, and get details only.
- **Property slugs**: Format is `{country}/{name}.html` (e.g., `fr/lesenatparis.html`).
