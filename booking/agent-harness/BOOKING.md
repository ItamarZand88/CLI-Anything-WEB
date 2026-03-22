# BOOKING.md — Booking.com API Map

## Site Profile
- **Type**: No-auth, read-only search
- **Framework**: Custom SSR (server-side rendered HTML) + GraphQL overlay
- **Protection**: AWS WAF JavaScript challenge — blocks raw httpx; bypassed by `curl_cffi` with `impersonate='chrome'` + WAF cookies from playwright-cli session
- **Auth required**: No (for search/browse). WAF cookies needed for SSR pages.
- **Protocol**: Hybrid SSR HTML + GraphQL API

## API Endpoints

### 1. GraphQL API (no WAF cookies needed)

**Endpoint**: `POST https://www.booking.com/dml/graphql?lang=en-us`

#### AutoComplete
Resolve destination names to dest_id/dest_type.

```graphql
query AutoComplete($input: AutoCompleteRequestInput!) {
  autoCompleteSuggestions(input: $input) {
    results {
      metaData { autocompleteResultId autocompleteResultSource }
      displayInfo { title label }
    }
  }
}
```

**Variables**:
```json
{
  "input": {
    "prefixQuery": "Paris",
    "nbSuggestions": 5,
    "fallbackConfig": {
      "mergeResults": true,
      "nbMaxMergedResults": 6,
      "nbMaxThirdPartyResults": 3,
      "sources": ["GOOGLE", "HERE"]
    },
    "requestConfig": {
      "enableRequestContextBoost": true
    }
  }
}
```

**Response** (key fields):
- `results[].metaData.autocompleteResultId` — e.g., `"city/-1456928"` (type/id format)
- `results[].displayInfo.title` — e.g., `"Paris"`
- `results[].displayInfo.label` — e.g., `"Paris, Ile de France, France"`

**Parsing autocompleteResultId**: Split on `/` → `type = parts[0]`, `id = parts[1]`
- `city/-1456928` → destType=city, destId=-1456928
- `district/2281` → destType=district, destId=2281
- `airport/8` → destType=airport, destId=8
- `region/1569` → destType=region, destId=1569
- `landmark/938` → destType=landmark, destId=938

### 2. Search Results (SSR — WAF cookies required)

**Endpoint**: `GET https://www.booking.com/searchresults.html`

**Parameters**:
| Param | Required | Description | Example |
|-------|----------|-------------|---------|
| `ss` | Yes | Search string | `Paris` |
| `dest_id` | Yes | Destination ID from autocomplete | `-1456928` |
| `dest_type` | Yes | Destination type | `city` |
| `checkin` | Yes | Check-in date (YYYY-MM-DD) | `2026-03-25` |
| `checkout` | Yes | Check-out date (YYYY-MM-DD) | `2026-03-28` |
| `group_adults` | Yes | Number of adults | `2` |
| `no_rooms` | Yes | Number of rooms | `1` |
| `group_children` | No | Number of children | `0` |
| `lang` | No | Language | `en-us` |
| `sr_order` | No | Sort order | `popularity`, `price`, `review_score`, `distance` |
| `offset` | No | Pagination offset | `25` (25 per page) |
| `nflt` | No | Filters (URL-encoded) | `class%3D4` (4-star) |

**HTML Parsing** (BeautifulSoup4):
```python
# Property cards
cards = soup.find_all(attrs={'data-testid': 'property-card'})

# Per card:
title = card.find(attrs={'data-testid': 'title'}).text.strip()
score_el = card.find(attrs={'data-testid': 'review-score'})
# score text: "Scored 8.6  8.6 Excellent   677 reviews"
price_el = card.find(attrs={'data-testid': 'price-and-discounted-price'})
address_el = card.find(attrs={'data-testid': 'address'})
link = card.find('a', attrs={'data-testid': 'title-link'})
# slug: /hotel/fr/lesenatparis.html -> "fr/lesenatparis.html"
```

**Extracted fields per property**:
- `title` — Hotel name
- `score` — Review score (float, e.g., 8.6)
- `score_label` — Score label (e.g., "Excellent")
- `review_count` — Number of reviews
- `price` — Price (string with currency, e.g., "₪ 2,945")
- `address` — Location text (e.g., "6th arr., Paris")
- `slug` — Hotel URL slug (e.g., "fr/lesenatparis.html")
- `distance` — Distance from center (e.g., "1.2 km from downtown")

### 3. Hotel Detail (SSR — WAF cookies required)

**Endpoint**: `GET https://www.booking.com/hotel/{slug}`

Example: `https://www.booking.com/hotel/fr/lesenatparis.html?checkin=2026-03-25&checkout=2026-03-28&group_adults=2&no_rooms=1&lang=en-us`

**Contains JSON-LD** (`<script type="application/ld+json">`) with structured data:
```json
{
  "@type": "Hotel",
  "name": "Le Senat",
  "description": "Located between...",
  "image": "https://cf.bstatic.com/...",
  "url": "https://www.booking.com/hotel/fr/lesenatparis.html",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "10 rue de Vaugirard, 6th arr., 75006 Paris, France",
    "postalCode": "75006",
    "addressCountry": "France"
  },
  "aggregateRating": {
    "ratingValue": 8.6,
    "reviewCount": 676,
    "bestRating": 10
  }
}
```

## Data Model

### Destination
- `dest_id`: int (negative for cities, positive for other types)
- `dest_type`: str (city, district, airport, region, landmark)
- `title`: str (display name)
- `label`: str (full label with country)

### Property (search result)
- `title`: str
- `slug`: str (URL path, e.g., "fr/lesenatparis.html")
- `score`: float (0-10)
- `score_label`: str (Wonderful, Excellent, Very Good, Good, Pleasant)
- `review_count`: int
- `price`: str (currency + amount)
- `price_amount`: float (parsed numeric)
- `address`: str
- `distance`: str
- `property_type`: str (Hotel, Apartment, Guesthouse, etc.)
- `star_rating`: int (1-5)

### Property Detail (from JSON-LD)
- Inherits all from Property
- `description`: str
- `image_url`: str
- `full_address`: str
- `postal_code`: str
- `country`: str
- `latitude`: float
- `longitude`: float

## WAF / Auth Architecture

### WAF Challenge Flow
1. First request to booking.com returns HTTP 202 with JavaScript challenge
2. Browser (playwright-cli) solves the challenge automatically
3. Sets `aws-waf-token` cookie (valid ~hours)
4. Subsequent requests with this cookie + `bkng` session cookie work

### CLI Auth Flow
1. `cli-web-booking auth login` — opens playwright-cli browser
2. User navigates to booking.com (WAF challenge auto-solved by browser)
3. `state-save` extracts cookies (aws-waf-token, bkng, etc.)
4. Stored in `~/.config/cli-web-booking/auth.json`
5. CLI uses curl_cffi with `impersonate='chrome'` + stored cookies

### GraphQL Bypass
The GraphQL endpoint at `/dml/graphql` does NOT require WAF cookies when using
`curl_cffi` with `impersonate='chrome'`. AutoComplete works without any cookies.

## CLI Commands

### `search` — Search properties
```bash
cli-web-booking search "Paris" --checkin 2026-03-25 --checkout 2026-03-28 --adults 2 --rooms 1
cli-web-booking search "London" --sort price --json
```

### `get` — Property details
```bash
cli-web-booking get fr/lesenatparis.html
cli-web-booking get fr/lesenatparis.html --checkin 2026-03-25 --checkout 2026-03-28 --json
```

### `autocomplete` — Resolve destinations
```bash
cli-web-booking autocomplete "Paris"
cli-web-booking autocomplete "Tokyo" --json
```

### `auth` — Manage WAF cookies
```bash
cli-web-booking auth login    # Opens browser, solves WAF challenge
cli-web-booking auth status   # Check if cookies are valid
cli-web-booking auth logout   # Clear stored cookies
```

## Rate Limits
- No explicit rate limits observed
- WAF may block on rapid requests — add 0.5-1s delay between requests
- Search pagination: 25 results per page

## Notes
- Read-only site — no WRITE operations (no create/update/delete)
- Currency based on user's detected location (ILS for Israel)
- Add `selected_currency=USD` param to force USD
- Hotels have slugs like `fr/lesenatparis.html` (country/name.html)
