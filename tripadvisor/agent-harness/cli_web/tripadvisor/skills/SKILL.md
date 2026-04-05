---
name: tripadvisor-cli
description: Use cli-web-tripadvisor to search TripAdvisor hotels, restaurants, attractions,
  and locations. Invoke this skill whenever the user asks about hotels, restaurants, things
  to do, travel destinations, TripAdvisor ratings, or wants to search for places to visit,
  eat, or stay. Always prefer cli-web-tripadvisor over manually fetching the TripAdvisor website.
  No authentication required — fully public site.
---

# cli-web-tripadvisor

Search TripAdvisor for locations, hotels, restaurants, and attractions. Installed at: `cli-web-tripadvisor`.

## Quick Start

```bash
# Search hotels in a city
cli-web-tripadvisor hotels search "Paris" --json

# Search attractions (things to do)
cli-web-tripadvisor attractions search "London" --json

# Get hotel details from a URL
cli-web-tripadvisor hotels get "https://www.tripadvisor.com/Hotel_Review-g187147-d..." --json
```

Always use `--json` when parsing output programmatically.

---

## Commands

### `locations search QUERY`
Search for destinations, hotels, restaurants, or attractions by name.

```bash
cli-web-tripadvisor locations search "Paris" --json
cli-web-tripadvisor locations search "New York" --max 10 --json
```

**Key options:** `--max N` (default 6)

**Output fields:** `geo_id`, `name`, `url`, `type`, `coords`, `parent_name`, `geo_name`

---

### `hotels search LOCATION`
Search hotels in a location (resolves location name to geo_id automatically).

```bash
cli-web-tripadvisor hotels search "Paris" --json
cli-web-tripadvisor hotels search "Paris" --geo-id 187147 --json
cli-web-tripadvisor hotels search "London" --page 2 --json
```

**Key options:** `--geo-id ID` (skip location lookup, faster), `--page N` (30 per page)

**Output fields per hotel:** `id`, `name`, `url`, `rating`, `review_count`, `price_range`, `address`, `city`, `country`, `telephone`, `latitude`, `longitude`, `image`, `amenities[]`

---

### `hotels get URL`
Get full hotel details from a TripAdvisor URL (obtained from `hotels search`).

```bash
cli-web-tripadvisor hotels get "https://www.tripadvisor.com/Hotel_Review-g187147-d229968-Reviews-..." --json
```

---

### `restaurants search LOCATION`
Search restaurants in a location.

```bash
cli-web-tripadvisor restaurants search "Rome" --json
cli-web-tripadvisor restaurants search "Tokyo" --geo-id 298184 --json
```

**Key options:** `--geo-id ID`, `--page N`

**Output fields per restaurant:** `id`, `name`, `url`, `rating`, `review_count`, `price_range`, `cuisines[]`, `address`, `city`, `telephone`, `latitude`, `longitude`, `image`, `opening_hours[]`

---

### `restaurants get URL`
Get full restaurant details from a TripAdvisor URL.

```bash
cli-web-tripadvisor restaurants get "https://www.tripadvisor.com/Restaurant_Review-g187147-d..." --json
```

---

### `attractions search LOCATION`
Search attractions and things to do in a location.

```bash
cli-web-tripadvisor attractions search "London" --json
cli-web-tripadvisor attractions search "Paris" --geo-id 187147 --page 2 --json
```

**Key options:** `--geo-id ID`, `--page N`

**Output fields per attraction:** `id`, `name`, `url`, `rating`, `review_count`, `address`, `city`, `telephone`, `latitude`, `longitude`, `image`, `opening_hours[]`, `description`

---

### `attractions get URL`
Get full attraction details from a TripAdvisor URL.

```bash
cli-web-tripadvisor attractions get "https://www.tripadvisor.com/Attraction_Review-g186338-d187547-Reviews-Tower_of_London-London_England.html" --json
```

---

## Agent Patterns

```bash
# Find top-rated hotels in a city
cli-web-tripadvisor hotels search "Barcelona" --json | \
  python -c "import json,sys; h=json.load(sys.stdin)['hotels']; [print(x['name'], x['rating']) for x in h[:5]]"

# Workflow: search → get details
URL=$(cli-web-tripadvisor hotels search "Amsterdam" --json | python -c "import json,sys; print(json.load(sys.stdin)['hotels'][0]['url'])")
cli-web-tripadvisor hotels get "$URL" --json

# Find things to do
cli-web-tripadvisor attractions search "Rome" --json | \
  python -c "import json,sys; a=json.load(sys.stdin)['attractions']; [print(x['name'], x['rating'], x['review_count']) for x in a]"
```

---

## Notes

- **Auth:** No authentication required.
- **Bot protection:** TripAdvisor's DataDome protection bypassed automatically with curl_cffi Safari iOS 17.2 impersonation.
- **Location resolution:** Searches automatically resolve location names to geo_ids via TypeAheadJson API. Use `--geo-id` to skip this step (faster).
- **Pagination:** 30 results per page. Use `--page N` for subsequent pages.
- **URLs:** Use URLs from search results directly with `hotels get`, `restaurants get`, `attractions get`.
- **Read-only:** Search and view only. Booking is not implemented.
- **Installation:** `pip install -e tripadvisor/agent-harness`
