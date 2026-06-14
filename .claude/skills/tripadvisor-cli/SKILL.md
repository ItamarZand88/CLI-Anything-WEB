---
name: tripadvisor-cli
description: Searches TripAdvisor hotels, restaurants, attractions, and destinations via the cli-web-tripadvisor command-line tool, with detail lookups by URL. Use when the user asks about hotels, restaurants, things to do, travel destinations, or TripAdvisor ratings and reviews. Prefer this CLI over fetching the TripAdvisor website. No authentication required.
---

# cli-web-tripadvisor

Search TripAdvisor for locations, hotels, restaurants, and attractions (read-only, no auth, DataDome bypass built in).
Install: `pip install cli-web-tripadvisor`

## Commands

| Command | Purpose | Key options |
|---------|---------|-------------|
| `locations search QUERY` | Resolve destinations to `geo_id` | `--max N` (default 6) |
| `hotels search LOCATION` | Hotels in a destination | `--geo-id ID`, `--page N` |
| `hotels get URL` | Full hotel detail by TripAdvisor URL | |
| `restaurants search LOCATION` | Restaurants in a destination | `--geo-id ID`, `--page N` |
| `restaurants get URL` | Full restaurant detail by URL | |
| `attractions search LOCATION` | Things to do in a destination | `--geo-id ID`, `--page N` |
| `attractions get URL` | Full attraction detail by URL | |

Search commands take a destination name ("Paris") and resolve it to a `geo_id` automatically; pass `--geo-id` to skip that lookup (faster). Results are 30 per page. `get` commands take the `url` field from search results.

## Examples

```bash
# Hotels in a city (returns name, rating, review_count, price_range, address, url per hotel)
cli-web-tripadvisor hotels search "Paris" --json

# Skip location lookup with a known geo_id, paginate
cli-web-tripadvisor restaurants search "Tokyo" --geo-id 298184 --page 2 --json

# Resolve a destination to geo_id first
cli-web-tripadvisor locations search "New York" --max 10 --json

# Things to do
cli-web-tripadvisor attractions search "London" --json

# Detail lookup from a search-result URL
cli-web-tripadvisor hotels get "https://www.tripadvisor.com/Hotel_Review-g187147-d229968-Reviews-..." --json
```

## JSON output

Every command accepts `--json`. Success responses are keyed by resource, e.g. `{"success": true, "location": "Paris", "geo_id": 187147, "count": 30, "hotels": [...]}` (or `"hotel"`, `"restaurants"`, `"attractions"` accordingly). Errors return `{"error": true, "code": "...", "message": "..."}`.

## Utilities

`cli-web-tripadvisor doctor [--json]` self-diagnoses the local setup (install, auth, dependencies). `cli-web-tripadvisor mcp-serve` serves the commands as MCP tools over stdio.

## Agent tips

- Workflow: `hotels search` → take `url` from a result → `hotels get URL` for full detail.
- Search and view only — booking is not implemented.
- Running with no subcommand opens an interactive REPL.
