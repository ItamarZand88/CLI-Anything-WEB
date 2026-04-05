# TRIPADVISOR.md — API Map for cli-web-tripadvisor

> Traffic source: raw-traffic.json captured 2026-04-04 via playwright-cli
> Site: https://www.tripadvisor.com
> Protocol: SSR HTML + JSON-LD scraping + REST TypeAheadJson
> Auth: None — all operations are public (no-auth site)
> Protection: DataDome bot protection → curl_cffi with impersonate='chrome'

---

## Site Profile

**No-auth + Read-only.** TripAdvisor exposes all search, listing, and detail data
publicly without login. Reviews, ratings, addresses, and pricing are available
directly from SSR HTML pages via embedded JSON-LD structured data.

No `auth.py`, no `auth` command group, no credentials storage.

---

## Protocol Analysis

| Layer | Details |
|-------|---------|
| Primary | SSR HTML pages with `<script type="application/ld+json">` blocks |
| Secondary | REST TypeAheadJson for location autocomplete |
| GraphQL | `POST /data/graphql/ids` with persisted query IDs — **NOT used** (IDs change on deploy) |
| Protection | DataDome fingerprinting — bypass with `curl_cffi` + `impersonate='chrome'` |

---

## URL Patterns

| Page | Pattern | Example |
|------|---------|---------|
| Location search | `GET /TypeAheadJson?query={q}&max=6&types=geo,...` | `/TypeAheadJson?query=Paris&max=6` |
| Hotel listing | `GET /Hotels-g{GEO_ID}-{Slug}-Hotels.html` | `/Hotels-g187147-Paris_Ile_de_France-Hotels.html` |
| Hotel listing p2+ | `GET /Hotels-g{GEO_ID}-oa{OFFSET}-{Slug}-Hotels.html` | `/Hotels-g187147-oa30-Paris_...-Hotels.html` |
| Restaurant listing | `GET /Restaurants-g{GEO_ID}-{Slug}.html` | `/Restaurants-g187147-Paris_Ile_de_France.html` |
| Attraction listing | `GET /Attractions-g{GEO_ID}-Activities-{Slug}.html` | `/Attractions-g187147-Activities-Paris_Ile_de_France.html` |
| Hotel detail | `GET /Hotel_Review-g{GEO_ID}-d{ID}-Reviews-{Name}-{Location}.html` | (full URL from search results) |
| Restaurant detail | `GET /Restaurant_Review-g{GEO_ID}-d{ID}-Reviews-{Name}-{Location}.html` | (full URL from search results) |
| Attraction detail | `GET /Attraction_Review-g{GEO_ID}-d{ID}-Reviews-{Name}-{Location}.html` | (full URL from search results) |

---

## TypeAheadJson REST API

**Endpoint:** `GET https://www.tripadvisor.com/TypeAheadJson`

**Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `query` | string | Search text |
| `max` | int | Max results (default 6) |
| `types` | string | `geo,hotel,airline,attraction,eatery` |
| `details` | bool | `true` to include parent/region details |
| `action` | string | `API` |
| `source` | string | `MASTHEAD_SEARCH_BOX` |

**Response shape (captured):**
```json
{
  "results": [
    {
      "type": "GEO",
      "document_id": "60763",
      "name": "New York City, New York, United States",
      "url": "/Tourism-g60763-New_York_City_New_York-Vacations.html",
      "coords": "40.713238,-74.00584",
      "details": {
        "placetype": 10004,
        "parent_name": "New York",
        "geo_name": "New York, United States"
      }
    }
  ]
}
```

**Key fields:** `document_id` = geo_id (numeric), `name` = full location name, `url` path gives location slug.

---

## JSON-LD Data Model

### Hotel Listing Page → `@type: Hotel` (inside ItemList)
```json
{
  "@type": "Hotel",
  "name": "Hôtel Le Meurice Dorchester Collection",
  "url": "https://www.tripadvisor.com/Hotel_Review-g187147-d229968-Reviews-...",
  "telephone": "+33 1 44 58 10 10",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "228 Rue de Rivoli",
    "addressLocality": "Paris",
    "addressRegion": "Ile-de-France",
    "postalCode": "75001",
    "addressCountry": "FR"
  },
  "geo": { "@type": "GeoCoordinates", "latitude": "48.8648", "longitude": "2.3337" },
  "image": "https://media-cdn.tripadvisor.com/...",
  "aggregateRating": { "@type": "AggregateRating", "ratingValue": "5.0", "reviewCount": "2345" },
  "priceRange": "$$$$"
}
```

### Hotel Detail Page → `@type: LodgingBusiness`
```json
{
  "@type": "LodgingBusiness",
  "name": "...",
  "priceRange": "$$$",
  "telephone": "...",
  "aggregateRating": { "ratingValue": "4.5", "reviewCount": 2345 },
  "address": { "streetAddress": "...", "addressLocality": "..." },
  "geo": { "latitude": "...", "longitude": "..." },
  "amenityFeatures": [
    { "@type": "LocationFeatureSpecification", "name": "WiFi", "value": true }
  ],
  "sameAs": ["https://www.tripadvisor.com/..."]
}
```

### Restaurant Listing Page → `@type: Restaurant` (inside ItemList)
```json
{
  "@type": "Restaurant",
  "name": "Da Franco",
  "url": "https://www.tripadvisor.com/Restaurant_Review-g187147-d1035679-Reviews-...",
  "aggregateRating": { "ratingValue": "4.5", "reviewCount": 1200 },
  "priceRange": "$$",
  "servesCuisine": ["Italian", "Pizza"],
  "telephone": "+33 1 ...",
  "address": { ... }
}
```

### Restaurant Detail Page → `@type: FoodEstablishment`
```json
{
  "@type": "FoodEstablishment",
  "name": "...",
  "url": "...",
  "geo": { "latitude": "...", "longitude": "..." },
  "telephone": "...",
  "openingHoursSpecification": [...]
}
```

### Attraction Listing Page → `@type: TouristAttraction` (inside CollectionPage/ItemList)
```json
{
  "@type": "TouristAttraction",
  "name": "Eiffel Tower",
  "url": "https://www.tripadvisor.com/Attraction_Review-g187147-d188151-Reviews-...",
  "geo": { "latitude": "48.8584", "longitude": "2.2945" }
}
```

### Attraction Detail Page → `@type: LocalBusiness`
```json
{
  "@type": "LocalBusiness",
  "name": "Eiffel Tower",
  "address": { ... },
  "aggregateRating": { "ratingValue": "4.7", "reviewCount": 85000 },
  "openingHours": ["Mo-Su 09:00-23:45"],
  "image": "..."
}
```

---

## ID System

| Entity | ID Format | Example | Notes |
|--------|-----------|---------|-------|
| Location (geo) | Numeric | `60763` (NYC), `187147` (Paris) | From TypeAheadJson `document_id` |
| Hotel | Numeric (`d{ID}`) | `229968` | Extracted from URL `d{NUMBER}` |
| Restaurant | Numeric (`d{ID}`) | `1035679` | Extracted from URL `d{NUMBER}` |
| Attraction | Numeric (`d{ID}`) | `188151` | Extracted from URL `d{NUMBER}` |

---

## Location Slug Convention

URL slugs are derived from the location name:
- `Paris, Ile-de-France` → `Paris_Ile_de_France`
- `New York City, New York` → `New_York_City_New_York`

Function: replace spaces with `_`, replace `, ` with `_`, preserve other characters.

The TypeAheadJson `url` field provides the canonical slug directly (e.g., from
`/Tourism-g60763-New_York_City_New_York-Vacations.html` → extract `New_York_City_New_York`).

---

## CLI Command Design

```
cli-web-tripadvisor                    # Enter REPL
cli-web-tripadvisor --json             # All output as JSON

locations search QUERY                 # TypeAheadJson location search
  --max N                             # Max results (default 6)
  --json

hotels search LOCATION                 # Hotel listing page
  --geo-id GEO_ID                     # Use known geo_id directly
  --page N                            # Page number (offset by 30)
  --json

hotels get URL                         # Hotel detail from full URL
  --json

restaurants search LOCATION            # Restaurant listing page
  --geo-id GEO_ID
  --page N
  --json

restaurants get URL                    # Restaurant detail from full URL
  --json

attractions search LOCATION            # Attraction listing page
  --geo-id GEO_ID
  --page N
  --json

attractions get URL                    # Attraction detail from full URL
  --json
```

---

## Rate Limiting

From captured traffic:
- `x-ratelimit-limit: 986` per `x-ratelimit-period: 3` seconds
- `x-rate-limit-limit: 30000` per `x-rate-limit-interval: 60` seconds
- No 429 responses during capture session

**CLI strategy:** No aggressive backoff needed for normal use. On 429, retry after
`retry-after` header value (default 60s).

---

## Anti-bot Strategy

DataDome sets a `datadome` cookie via client-side JS. It fingerprints:
- TLS fingerprint (JA3 hash)
- HTTP/2 settings
- User-Agent

`curl_cffi` with `impersonate='chrome'` replicates Chrome's full TLS fingerprint and
HTTP/2 settings, bypassing DataDome without needing cookies. Confirmed pattern from
Airbnb CLI (same protection stack).

**Headers to include:**
```python
{
  "accept": "text/html,application/xhtml+xml,*/*;q=0.8",
  "accept-language": "en-US,en;q=0.9",
  "cache-control": "no-cache",
  "pragma": "no-cache",
  "sec-fetch-dest": "document",
  "sec-fetch-mode": "navigate",
  "sec-fetch-site": "none",
  "upgrade-insecure-requests": "1",
}
```
