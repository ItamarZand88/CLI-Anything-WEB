---
name: airbnb-cli
description: Use cli-web-airbnb to search Airbnb stays, get listing details, check
  availability calendars, read guest reviews, and look up location suggestions. Invoke
  this skill whenever the user asks about Airbnb accommodations, vacation rentals,
  listing prices, availability, guest reviews, or wants to search for places to stay.
  Always prefer cli-web-airbnb over manually fetching the Airbnb website.
---

# cli-web-airbnb

Search Airbnb stays by location, dates, and filters; get detailed listing information including reviews and availability calendars; autocomplete location names. Installed at: `cli-web-airbnb`.

## Quick Start

```bash
# Search for stays — returns listings with id, name, price, rating
cli-web-airbnb search stays "London, UK" --json

# Get full details for a specific listing
cli-web-airbnb listings get 770993223449115417 --json
```

Always use `--json` when parsing output programmatically.

---

## Commands

### `search stays LOCATION`
Search for stays in a location. Returns paginated listings with price, rating, coordinates.

```bash
cli-web-airbnb search stays "Paris, France" --json
cli-web-airbnb search stays "New York, NY" --checkin 2024-06-01 --checkout 2024-06-05 --adults 2 --json
cli-web-airbnb search stays "Tokyo, Japan" --max-price 150 --room-type private_room --json
cli-web-airbnb search stays "Barcelona, Spain" --cursor "eyJ..." --json
```

**Key options:** `--checkin DATE`, `--checkout DATE`, `--adults N`, `--children N`, `--infants N`, `--pets N`, `--min-price N`, `--max-price N`, `--room-type [entire_home|private_room|shared_room|hotel_room]`, `--cursor TOKEN`, `--locale CODE`, `--currency CODE`

**Output fields:** `success`, `count`, `next_cursor`, `total_count`, `location_slug`, `listings[]` (each: `id`, `id_b64`, `name`, `url`, `rating`, `price`, `price_qualifier`, `latitude`, `longitude`, `badges`)

---

### `listings get LISTING_ID`
Get full details for a specific listing.

```bash
cli-web-airbnb listings get 770993223449115417 --json
cli-web-airbnb listings get 1603496841117193305 --checkin 2024-06-01 --checkout 2024-06-05 --json
```

**Key options:** `--adults N`, `--checkin DATE`, `--checkout DATE`, `--locale CODE`, `--currency CODE`

**Output fields:** `id`, `id_b64`, `name`, `url`, `rating`, `review_count`, `host_name`, `description`, `amenities[]`, `bedrooms`, `bathrooms`, `max_guests`, `price`, `price_qualifier`, `latitude`, `longitude`, `badges`


---

### `listings reviews LISTING_ID`
Get guest reviews for a listing (sorted by quality, recency, or rating).

```bash
cli-web-airbnb listings reviews 770993223449115417 --json
cli-web-airbnb listings reviews 770993223449115417 --sort RECENT --limit 10 --json
```

**Key options:** `--limit N` (default 24), `--offset N` (pagination), `--sort [BEST_QUALITY|RECENT|RATING_DESC|RATING_ASC]`, `--locale CODE`, `--currency CODE`

**Output fields:** `success`, `listing_id`, `total_count`, `count`, `reviews[]` (each: `id`, `rating`, `date`, `reviewer`, `reviewer_location`, `comment`, `host_response`)

---

### `listings availability LISTING_ID`
Get 12-month availability calendar for a listing.

```bash
cli-web-airbnb listings availability 770993223449115417 --json
cli-web-airbnb listings availability 770993223449115417 --month 6 --year 2026 --count 3 --json
```

**Key options:** `--month N` (1-12, default current), `--year N` (default current), `--count N` (months, default 12), `--available-only`, `--locale CODE`, `--currency CODE`

**Output fields:** `success`, `listing_id`, `months[]` (each: `month`, `year`, `days[]` (each: `date`, `available`, `checkin`, `checkout`, `min_nights`, `max_nights`, `price`))

---

### `autocomplete locations QUERY`
Suggest locations matching a partial query string.

```bash
cli-web-airbnb autocomplete locations "New Yor" --json
cli-web-airbnb autocomplete locations "Lond" --num-results 10 --json
```

**Key options:** `--num-results N` (default: 5), `--locale CODE`, `--currency CODE`

**Output fields:** `success`, `query`, `suggestions[]` (each: `query`, `place_id`, `display`, `acp_id`)

---

## Agent Patterns

```bash
# Find affordable stays and inspect the cheapest one
cli-web-airbnb search stays "Amsterdam, Netherlands" --max-price 100 --json | \
  python -c "import json,sys; d=json.load(sys.stdin); l=d['listings'][0]; print(l['id'], l['price'])"

# Search then get full details round-trip
ID=$(cli-web-airbnb search stays "London, UK" --json | python -c "import json,sys; print(json.load(sys.stdin)['listings'][0]['id'])")
cli-web-airbnb listings get $ID --json

# Paginate through results
CURSOR=$(cli-web-airbnb search stays "Rome, Italy" --json | python -c "import json,sys; print(json.load(sys.stdin)['next_cursor'])")
cli-web-airbnb search stays "Rome, Italy" --cursor "$CURSOR" --json

# Resolve partial location before searching
cli-web-airbnb autocomplete locations "Barce" --json
```

---

## Notes

- **Auth:** No authentication required. Airbnb is a fully public no-auth site.
- **Bot protection:** Akamai/DataDome bypassed automatically with curl_cffi Chrome impersonation.
- **Rate limiting:** No explicit limit. If blocked, retry after a short delay.
- **Listing IDs:** Long integer strings (e.g. `1603496841117193305`). Use `id_b64` for Airbnb internal API.
- **Pagination:** Cursor-based. Use `next_cursor` value with `--cursor` for the next page.
- **Read-only:** Search and view only. Booking is not implemented.
- **Installation:** `pip install -e airbnb/agent-harness`
