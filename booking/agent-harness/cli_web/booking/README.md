# cli-web-booking

Agent-native CLI for [Booking.com](https://www.booking.com) — search hotels, get property details, and resolve destinations from the command line.

## Install

```bash
cd booking/agent-harness
pip install -e .
```

## Auth Setup

Booking.com uses AWS WAF which requires a browser to solve the initial challenge. Run once:

```bash
cli-web-booking auth login
```

This opens a browser, solves the WAF challenge automatically, and saves cookies.
The `autocomplete` command works without auth (GraphQL endpoint bypasses WAF).

## Usage

### Search Properties

```bash
# Search hotels in Paris
cli-web-booking search find "Paris" --checkin 2026-04-01 --checkout 2026-04-04

# With filters
cli-web-booking search find "London" --adults 2 --rooms 1 --sort price --json

# Paginate
cli-web-booking search find "Tokyo" --page 2
```

### Get Property Details

```bash
# By slug (from search results)
cli-web-booking get fr/lesenatparis.html

# With dates for pricing
cli-web-booking get fr/lesenatparis.html --checkin 2026-04-01 --checkout 2026-04-04 --json
```

### Resolve Destinations

```bash
# Find destination IDs (no auth needed)
cli-web-booking autocomplete "Paris" --json
cli-web-booking autocomplete "Tokyo"
```

### Auth Management

```bash
cli-web-booking auth login    # Open browser for WAF cookies
cli-web-booking auth status   # Check if cookies are valid
cli-web-booking auth logout   # Clear stored cookies
```

### REPL Mode

```bash
# Interactive mode (default when no subcommand)
cli-web-booking

# With JSON output in REPL
cli-web-booking --json
```

## JSON Output

Every command supports `--json` for structured output:

```json
{
  "success": true,
  "destination": "Paris",
  "checkin": "2026-04-01",
  "checkout": "2026-04-04",
  "count": 25,
  "properties": [
    {
      "title": "Le Senat",
      "slug": "fr/lesenatparis.html",
      "score": 8.6,
      "score_label": "Excellent",
      "review_count": 677,
      "price": "₪ 2,945",
      "price_amount": 2945.0
    }
  ]
}
```

## Environment Variables

- `CLI_WEB_BOOKING_AUTH_JSON` — JSON string with cookies (for CI/CD)
- `CLI_WEB_FORCE_INSTALLED` — Set to `1` for subprocess tests
