# TRIPADVISOR.md — API Map for cli-web-tripadvisor

> Traffic source: raw-traffic.json captured 2026-04-04 via playwright-cli
> Site: https://www.tripadvisor.com
> Protocol: SSR HTML + JSON-LD parsing (primary) + REST TypeAheadJson (location search)
> Auth: None — all read operations are publicly accessible without login
> Protection: DataDome — use `curl_cffi` with `impersonate='chrome'`

---

## Overview

TripAdvisor is a travel review platform. The CLI provides:
- **Location search** — autocomplete for cities, regions
- **Hotel search** — list hotels in a city, get hotel details
- **Restaurant search** — list restaurants in a city, get restaurant details
- **Attraction search** — list things to do in a city, get attraction details

All data is read-only and publicly accessible. No authentication required.

---

## Data Architecture

TripAdvisor embeds rich **JSON-LD structured data** directly in server-rendered HTML pages. This is the primary data source — more stable than the GraphQL API (which uses pre-registered query IDs that may rotate with deployments).

### Location ID System

Every TripAdvisor location has a numeric **GEO ID** (geo_id):
- `60763` = New York City
- `187147` = Paris
- `186338` = London

Individual hotels, restaurants, and attractions also have numeric **location IDs**:
- Hotels: `d229968` → location_id = `229968`
- Restaurants: `d1035679` → location_id = `1035679`
- Attractions: `d188151` → location_id = `188151`

These IDs appear in the URL slug: `/Hotel_Review-g{GEO_ID}-d{LOC_ID}-Reviews-{Name}-{Slug}.html`

---

## Endpoint 1: Location Search / Autocomplete

**Purpose**: Find a location by name, get its GEO ID and slug for building listing URLs.

### TypeAheadJson REST API (primary)

```
GET https://www.tripadvisor.com/TypeAheadJson
```

**Query Parameters**:

| Param | Type | Required | Example | Description |
|-------|------|----------|---------|-------------|
| `query` | string | yes | `New York` | Search query |
| `max` | int | no | `6` | Max results (default 6) |
| `types` | string | no | `geo,hotel,attraction,eatery` | Result types to include |
| `details` | bool | no | `true` | Include extra details |
| `interleaved` | bool | no | `true` | Interleave result types |
| `source` | string | no | `MASTHEAD_SEARCH_BOX` | Source identifier |
| `uiOrigin` | string | no | `MASTHEAD_SEARCH` | UI origin |

**Example Request**:
```
GET /TypeAheadJson?query=Paris&max=6&types=geo,hotel,attraction,eatery&details=true
```

**Response Structure**:
```json
{
  "normalized": {"query": "paris"},
  "query": {...},
  "results": [
    {
      "title": "Destinations",
      "type": "GEO",
      "document_id": "187147",
      "url": "/Tourism-g187147-Paris_Ile_de_France-Vacations.html",
      "urls": [
        {
          "url_type": "geo",
          "name": "Paris Tourism",
          "fallback": false,
          "url": "/Tourism-g187147-Paris_Ile_de_France-Vacations.html"
        }
      ]
    }
  ]
}
```

**Key fields**:
- `results[].document_id` — the GEO ID (numeric string)
- `results[].type` — `GEO`, `HOTEL`, `ATTRACTION`, `EATERY`
- `results[].url` — TripAdvisor page URL for the result
- `results[].title` — Group label (e.g., "Destinations", "Hotels")

**CLI command**: `tripadvisor search [query]`

---

## Endpoint 2: Hotel Listings

**Purpose**: List top hotels in a city/location.

### URL Pattern
```
GET https://www.tripadvisor.com/Hotels-g{GEO_ID}-{Location_Slug}-Hotels.html
```

**Pagination**:
```
GET /Hotels-g{GEO_ID}-oa{offset}-{Location_Slug}-Hotels.html
# offset: 0, 30, 60, 90... (30 results per page)
```

**Examples**:
```
/Hotels-g187147-Paris_Ile_de_France-Hotels.html           (page 1)
/Hotels-g187147-oa30-Paris_Ile_de_France-Hotels.html      (page 2)
/Hotels-g60763-New_York_City_New_York-Hotels.html
```

**Data Extraction**: Parse `ItemList` JSON-LD from `<script type="application/ld+json">`

**Response Structure** (from JSON-LD `ItemList`):
```json
{
  "@type": "ItemList",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "item": {
        "@type": "Hotel",
        "name": "Hôtel Astra Opéra - Astotel",
        "address": {
          "@type": "PostalAddress",
          "streetAddress": "29 Rue De Caumartin",
          "addressLocality": "Paris",
          "addressCountry": "France",
          "postalCode": "75009"
        },
        "geo": {
          "@type": "GeoCoordinates",
          "latitude": 48.87178,
          "longitude": 2.328087
        },
        "telephone": "+33 1 42 65 15 15",
        "image": "https://dynamic-media-cdn.tripadvisor.com/...",
        "url": "https://www.tripadvisor.com/Hotel_Review-g187147-d229968-Reviews-..."
      }
    }
  ]
}
```

**Key fields per hotel**:
- `name` — hotel name
- `address.streetAddress`, `addressLocality`, `postalCode`, `addressCountry`
- `geo.latitude`, `geo.longitude`
- `telephone`
- `image`
- `url` — hotel detail page URL (contains location_id as `d{ID}`)

**How to extract location_id**: Parse from `url` field — `/Hotel_Review-g{GEO_ID}-d{LOC_ID}-...`

**CLI command**: `tripadvisor hotels list [location]`

---

## Endpoint 3: Hotel Detail

**Purpose**: Get full details, amenities, ratings, and reviews for a specific hotel.

### URL Pattern
```
GET https://www.tripadvisor.com/Hotel_Review-g{GEO_ID}-d{HOTEL_ID}-Reviews-{Name_Slug}-{Location_Slug}.html
```

**Data Extraction**: Parse `LodgingBusiness` JSON-LD

**Response Structure** (from `LodgingBusiness` JSON-LD):
```json
{
  "@type": "LodgingBusiness",
  "name": "Hôtel Astra Opéra - Astotel",
  "url": "https://www.tripadvisor.com/Hotel_Review-...",
  "priceRange": "$$ (Based on Average Nightly Rates for a Standard Room from our Partners)",
  "telephone": "+33 1 42 65 15 15",
  "sameAs": "http://www.astotel.com/astra",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "5.0",
    "reviewCount": 838
  },
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "29 Rue De Caumartin",
    "addressLocality": "Paris",
    "postalCode": "75009",
    "addressCountry": {"@type": "Country", "name": "FR"}
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 48.87178,
    "longitude": 2.328087
  },
  "amenityFeatures": [
    {"@type": "LocationFeatureSpecification", "name": "Free High Speed Internet (WiFi)", "value": true},
    {"@type": "LocationFeatureSpecification", "name": "Pool", "value": true}
  ],
  "image": "https://dynamic-media-cdn.tripadvisor.com/..."
}
```

**Key fields**:
- `name`, `url`, `priceRange`, `telephone`, `sameAs` (official website)
- `aggregateRating.ratingValue`, `aggregateRating.reviewCount`
- `address` (full postal address)
- `geo` (latitude/longitude)
- `amenityFeatures` (array of amenity name + boolean value)
- `image`

**CLI command**: `tripadvisor hotels get [hotel_url_or_id]`

---

## Endpoint 4: Restaurant Listings

**Purpose**: List top restaurants in a city/location.

### URL Pattern
```
GET https://www.tripadvisor.com/Restaurants-g{GEO_ID}-{Location_Slug}.html
```

**Pagination**:
```
GET /Restaurants-g{GEO_ID}-{Location_Slug}-oa{offset}.html
# offset: 30, 60, 90...
```

**Examples**:
```
/Restaurants-g187147-Paris_Ile_de_France.html
/Restaurants-g60763-New_York_City_New_York.html
```

**Data Extraction**: Parse `ItemList` JSON-LD (typically 30 restaurants per page)

**Response Structure** (from `ItemList` JSON-LD):
```json
{
  "@type": "ItemList",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "item": {
        "@type": "Restaurant",
        "name": "Bistrot Des Tournelles",
        "description": "",
        "url": "https://www.tripadvisor.com/Restaurant_Review-g187147-d26398028-Reviews-...",
        "aggregateRating": {
          "@type": "AggregateRating",
          "ratingValue": "4.1",
          "reviewCount": 31
        },
        "priceRange": "$$ - $$$",
        "image": ["https://dynamic-media-cdn.tripadvisor.com/..."],
        "telephone": "+33 1 57 40 99 96",
        "address": {
          "@type": "PostalAddress",
          "addressCountry": "France",
          "addressLocality": "",
          "addressRegion": "",
          "postalCode": "75004"
        }
      }
    }
  ]
}
```

**Key fields per restaurant**:
- `name`, `description`, `url`, `telephone`
- `aggregateRating.ratingValue`, `reviewCount`
- `priceRange`
- `image[0]` (array)
- `address.postalCode`, `addressLocality`

**CLI command**: `tripadvisor restaurants list [location]`

---

## Endpoint 5: Restaurant Detail

**Purpose**: Get full details, contact info, hours for a specific restaurant.

### URL Pattern
```
GET https://www.tripadvisor.com/Restaurant_Review-g{GEO_ID}-d{REST_ID}-Reviews-{Name_Slug}-{Location_Slug}.html
```

**Data Extraction**: Parse `FoodEstablishment` JSON-LD

**Response Structure** (from `FoodEstablishment` JSON-LD):
```json
{
  "@type": "FoodEstablishment",
  "name": "Da Franco",
  "url": "https://www.tripadvisor.com/Restaurant_Review-g187147-d1035679-Reviews-...",
  "image": "https://dynamic-media-cdn.tripadvisor.com/...",
  "geo": {"@type": "GeoCoordinates", "latitude": 48.881218, "longitude": 2.286114},
  "telephone": "+33 1 45 72 41 20",
  "openingHoursSpecification": [
    {
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": "Monday",
      "opens": "12:00:00",
      "closes": "15:00:00"
    }
  ]
}
```

**Key fields**:
- `name`, `url`, `image`, `telephone`
- `geo.latitude`, `geo.longitude`
- `openingHoursSpecification[]` (dayOfWeek, opens, closes)

**CLI command**: `tripadvisor restaurants get [restaurant_url_or_id]`

---

## Endpoint 6: Attraction Listings

**Purpose**: List top things to do in a city/location.

### URL Pattern
```
GET https://www.tripadvisor.com/Attractions-g{GEO_ID}-Activities-{Location_Slug}.html
```

**Examples**:
```
/Attractions-g187147-Activities-Paris_Ile_de_France.html
/Attractions-g60763-Activities-New_York_City_New_York.html
```

**Data Extraction**: Parse `CollectionPage` JSON-LD → `mainEntity.itemListElement`

**Response Structure** (from `CollectionPage` JSON-LD):
```json
{
  "@type": "CollectionPage",
  "name": "Top Things to Do in Paris",
  "about": {
    "@type": "TouristDestination",
    "name": "Paris",
    "geo": {"@type": "GeoCoordinates", "latitude": 48.857037, "longitude": 2.349401}
  },
  "mainEntity": {
    "@type": "ItemList",
    "itemListElement": [
      {
        "@type": "ListItem",
        "position": 1,
        "item": {
          "@type": "TouristAttraction",
          "name": "Eiffel Tower",
          "geo": {"@type": "GeoCoordinates", "latitude": 48.858353, "longitude": 2.294464}
        }
      }
    ]
  }
}
```

**Note**: The listing JSON-LD has limited fields (name + geo). Use attraction detail endpoint for full data.

**CLI command**: `tripadvisor attractions list [location]`

---

## Endpoint 7: Attraction Detail

**Purpose**: Get full details, ratings, hours for a specific attraction.

### URL Pattern
```
GET https://www.tripadvisor.com/Attraction_Review-g{GEO_ID}-d{ATTR_ID}-Reviews-{Name_Slug}-{Location_Slug}.html
```

**Data Extraction**: Parse `LocalBusiness` JSON-LD

**Response Structure** (from `LocalBusiness` JSON-LD):
```json
{
  "@type": "LocalBusiness",
  "name": "Eiffel Tower",
  "url": "https://www.tripadvisor.com/Attraction_Review-g187147-d188151-Reviews-...",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Av. Gustave Eiffel",
    "addressLocality": "Paris",
    "addressCountry": "FR",
    "postalCode": "75007"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.6",
    "reviewCount": 143818,
    "bestRating": 5
  },
  "openingHours": "Mo-Su 09:30-23:00",
  "image": "https://dynamic-media-cdn.tripadvisor.com/..."
}
```

**Key fields**:
- `name`, `url`, `image`
- `address` (full postal address)
- `aggregateRating.ratingValue`, `reviewCount`, `bestRating`
- `openingHours` (free-form string)

**CLI command**: `tripadvisor attractions get [attraction_url_or_id]`

---

## Authentication

**None required** for all read operations. The site is publicly accessible.

**DataDome protection** requires `curl_cffi` with Chrome impersonation to bypass bot detection:
```python
from curl_cffi import requests as curl_requests
resp = curl_requests.get(url, impersonate="chrome")
```

No cookies or session management needed for basic read operations.

---

## Data Model

### LocationResult (from TypeAheadJson)
```python
@dataclass
class LocationResult:
    location_id: int       # numeric GEO ID
    name: str              # display name
    type: str              # GEO, HOTEL, ATTRACTION, EATERY
    url: str               # TripAdvisor URL
    location_slug: str     # e.g. "Paris_Ile_de_France"
    hierarchy: str         # e.g. "France, Europe"
```

### Hotel (from listing + detail)
```python
@dataclass
class Hotel:
    location_id: int       # numeric ID (from d{ID} in URL)
    name: str
    url: str               # full TripAdvisor URL
    rating: float          # aggregateRating.ratingValue
    review_count: int
    price_range: str        # "$", "$$", "$$$", etc.
    address: str           # formatted address
    postal_code: str
    city: str
    country: str
    latitude: float
    longitude: float
    telephone: str
    website: str           # sameAs field
    amenities: list[str]   # amenityFeatures names where value=true
    image_url: str
```

### Restaurant (from listing + detail)
```python
@dataclass
class Restaurant:
    location_id: int
    name: str
    url: str
    rating: float
    review_count: int
    price_range: str       # "$$ - $$$"
    telephone: str
    address: str
    postal_code: str
    city: str
    latitude: float
    longitude: float
    image_url: str
    opening_hours: list[dict]  # [{dayOfWeek, opens, closes}]
```

### Attraction (from listing + detail)
```python
@dataclass
class Attraction:
    location_id: int
    name: str
    url: str
    rating: float
    review_count: int
    address: str
    postal_code: str
    city: str
    country: str
    latitude: float
    longitude: float
    opening_hours: str     # free-form string
    image_url: str
```

---

## CLI Command Design

```
cli-web-tripadvisor [--json] COMMAND [ARGS]...

Commands:
  search           Search for a location by name (hotels, cities, restaurants, attractions)
  hotels           Hotel commands
    list           List hotels in a location
    get            Get hotel details by URL or ID
  restaurants      Restaurant commands
    list           List restaurants in a location
    get            Get restaurant details by URL or ID
  attractions      Attraction commands
    list           List things to do in a location
    get            Get attraction details by URL or ID
```

### REPL Mode
Default when no subcommand given. Banner: `tripadvisor> `

```
tripadvisor> search Paris
tripadvisor> hotels list 187147
tripadvisor> hotels get /Hotel_Review-g187147-d229968-...
tripadvisor> restaurants list New York City
tripadvisor> attractions list London
```

### Key implementation notes

1. **Location slug resolution**: `hotels list "Paris"` → call TypeAheadJson → get GEO ID + slug → build listing URL
2. **Offset-based pagination**: Use `--page N` or `--offset N` for pagination
3. **URL shortcut**: All `get` commands accept either a full URL or just the location_id (numeric)
4. **Location ID extraction**: Extract from URL using regex `d(\d+)`
5. **No auth module needed**: Skip `auth.py`, no `auth login/status` commands

---

## Tech Stack for Generated CLI

- **HTTP client**: `curl_cffi` with `impersonate='chrome'` (DataDome bypass)
- **HTML parsing**: `beautifulsoup4` (extract JSON-LD from `<script type="application/ld+json">`)
- **JSON-LD parsing**: `json.loads()` on script tag content
- **Output**: `rich` for tables
- **No auth.py** — public site, no login required
