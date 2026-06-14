---
name: airbnb-cli
description: Searches Airbnb from the terminal via cli-web-airbnb — find stays by location, dates, and filters; get listing details, guest reviews, and availability calendars; autocomplete location names. Use when the user asks about Airbnb, vacation rentals, listing prices, availability, or finding places to stay. Prefer cli-web-airbnb over fetching the Airbnb website. No auth required.
---

# cli-web-airbnb

Read-only Airbnb search: stays, listing details, reviews, availability, location autocomplete. Bot protection (Akamai/DataDome) is bypassed automatically.
Install: `pip install cli-web-airbnb`

## Commands

### search
- `search stays LOCATION` — search stays (e.g. `"London, UK"`). Options: `--checkin DATE --checkout DATE`, `--adults N` (default 1), `--children N`, `--infants N`, `--pets N`, `--min-price N`, `--max-price N`, `--room-type [entire_home|private_room|shared_room|hotel_room]` (repeatable), `--amenity ID` (repeatable; 4=WiFi, 8=Kitchen, 40=AC, 33=Pool), `--cursor TOKEN` (pagination), `--locale`, `--currency`

### listings
- `listings get LISTING_ID` — full details (description, amenities, host, price). Options: `--checkin`, `--checkout`, `--adults`
- `listings reviews LISTING_ID` — guest reviews. Options: `--limit N` (default 24), `--offset N`, `--sort [best_quality|recent|rating_desc|rating_asc]`
- `listings availability LISTING_ID` — calendar. Options: `--month N`, `--year N`, `--count N` (months, default 12), `--available-only`

### autocomplete
- `autocomplete locations QUERY` — location suggestions. Options: `-n/--num-results N` (default 5)

## Examples

```bash
# Search with dates and budget — returns listings with id, name, price, rating
cli-web-airbnb search stays "Paris, France" --checkin 2026-07-01 --checkout 2026-07-05 --adults 2 --max-price 200 --json

# Search → inspect top result
ID=$(cli-web-airbnb search stays "London, UK" --json | python3 -c "import json,sys; print(json.load(sys.stdin)['listings'][0]['id'])")
cli-web-airbnb listings get $ID --json

# Recent reviews for a listing
cli-web-airbnb listings reviews 770993223449115417 --sort recent --limit 10 --json

# Next 3 months of availability
cli-web-airbnb listings availability 770993223449115417 --count 3 --available-only --json

# Resolve a partial location before searching
cli-web-airbnb autocomplete locations "New Yor" --json
```

## JSON output

Add `--json` to any command for structured output. Success responses are flat envelopes, e.g. search: `{"success": true, "count", "next_cursor", "total_count", "listings": [{id, id_b64, name, url, rating, price, price_qualifier, latitude, longitude, badges}]}`. Errors: `{"error": true, "code": "...", "message": "..."}`.

## Utilities

`cli-web-airbnb doctor [--json]` diagnoses local setup (install, dependencies). `cli-web-airbnb mcp-serve` exposes the commands as MCP tools over stdio. Running with no subcommand opens an interactive REPL.

## Agent tips

- Pagination is cursor-based: pass the `next_cursor` value from one search as `--cursor` in the next.
- Listing IDs are long integer strings; `id_b64` is the base64 form Airbnb uses internally.
- Search and view only — booking is not implemented.
