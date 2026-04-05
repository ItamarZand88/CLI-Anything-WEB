# AIRBNB.md — API Map for cli-web-airbnb

> **Traffic source:** raw-traffic.json captured 2026-04-03 via playwright-cli (438 requests)
> **Site:** https://www.airbnb.com (locale: he.airbnb.com — Hebrew, redirected from Israeli IP)
> **Protocol:** SSR HTML + embedded `niobeClientData` JSON (persisted GraphQL response inline in HTML)
> **Auth:** Optional — public for search/listings; cookie login for wishlists/booking
> **Bot protection:** DataDome + Akamai → use `curl_cffi` with `impersonate='chrome'`

---

## Architecture Overview

Airbnb does **NOT** use client-side JSON API calls for search or listing pages. Instead:

1. Browser GETs search/detail URL → server renders HTML + inlines full GraphQL response
2. HTML contains `<script type="application/json">` tags with `niobeClientData` JSON
3. CLI fetches HTML page via `curl_cffi`, parses `<script>` tags, extracts `niobeClientData`
4. No API key needed for HTML pages; API key `d306zoyjsyarp7ifhu67rjxn52tv0t20` needed for `/api/v2/` REST calls

---

## Data Extraction Pattern (niobeClientData)

```python
import re, json, base64
from curl_cffi import requests as curl_requests

def extract_niobe_data(html: str, operation: str) -> dict:
    """Extract embedded GraphQL response from Airbnb HTML page."""
    scripts = re.findall(
        r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    for script in scripts:
        try:
            data = json.loads(script)
            if 'niobeClientData' not in data:
                continue
            for key, value in data['niobeClientData']:
                if key.startswith(operation + ':'):
                    return value  # {'data': {...}, 'variables': {...}}
        except Exception:
            continue
    return None

def decode_listing_id(encoded_id: str) -> str:
    """Decode base64 listing ID to integer string."""
    decoded = base64.b64decode(encoded_id + '==').decode('utf-8')
    # Format: "DemandStayListing:770993223449115417"
    return decoded.split(':')[-1]

def encode_listing_id(int_id: str) -> str:
    """Encode integer listing ID to base64 for GraphQL variables."""
    raw = f"DemandStayListing:{int_id}"
    return base64.b64encode(raw.encode()).decode().rstrip('=')
```

---

## Command Structure

```
cli-web-airbnb
├── search                  # Search stays (public, no auth)
│   ├── stays               # Search for accommodation
│   └── experiences         # Search for experiences
├── listings                # Listing operations (public)
│   └── get                 # Get listing details
├── autocomplete            # Location autocomplete
│   └── locations           # Suggest locations for search input
└── auth                    # Authentication (for wishlist/booking)
    ├── login               # Browser login
    └── status              # Check auth status
```

---

## API Endpoints

### 1. Search Stays (`search stays`)

**URL Pattern:** `GET https://www.airbnb.com/s/{location}/homes`

**URL Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | path | Yes | Location slug, e.g. `London--UK`, `Paris--France`, `New-York--NY--United-States` |
| `adults` | int | No | Number of adults (default: 1) |
| `children` | int | No | Number of children |
| `infants` | int | No | Number of infants |
| `pets` | int | No | 0 or 1 |
| `checkin` | date | No | Check-in date YYYY-MM-DD |
| `checkout` | date | No | Check-out date YYYY-MM-DD |
| `price_min` | int | No | Minimum price per night |
| `price_max` | int | No | Maximum price per night |
| `room_types[]` | enum | No | `Entire home/apt`, `Private room`, `Shared room`, `Hotel room` |
| `amenities[]` | int[] | No | Amenity IDs (4=WiFi, 8=Kitchen, 40=AC, 33=Pool) |
| `cursor` | base64 | No | Pagination cursor |
| `locale` | string | No | Language code (use `en` for English) |
| `currency` | string | No | Currency code (use `USD`) |

**Response Extraction:**
```python
niobe = extract_niobe_data(html, 'StaysSearch')
results = niobe['data']['presentation']['staysSearch']['results']
listings = results['searchResults']  # list of 18 listings
pagination = results['paginationInfo']
next_cursor = pagination['nextPageCursor']  # base64 encoded

# Per listing:
listing = listings[0]
listing_id_b64  = listing['demandStayListing']['id']
listing_id_int  = decode_listing_id(listing_id_b64)  # "770993223449115417"
name            = listing['nameLocalized']['localizedStringWithTranslationPreference']
rating          = listing['avgRatingLocalized']  # "4.98 (42)"
price           = listing['structuredDisplayPrice']['primaryLine']['price']  # "₪514"
price_qualifier = listing['structuredDisplayPrice']['primaryLine']['qualifier']  # "total"
lat             = listing['demandStayListing']['location']['coordinate']['latitude']
lon             = listing['demandStayListing']['location']['coordinate']['longitude']
badges          = [b['text'] for b in listing.get('badges', [])]  # ["Guest favorite"]
photo_id        = listing.get('listingParamOverrides', {}) and \
                  listing['listingParamOverrides'].get('photoId')
```

**CLI Output (`--json`):**
```json
{
  "success": true,
  "count": 18,
  "next_cursor": "eyJzZWN0aW9uX29mZnNldCI6MCwiaXRlbXNfb2Zmc2V0IjoxOH0=",
  "listings": [
    {
      "id": "770993223449115417",
      "id_b64": "RGVtYW5kU3RheUxpc3Rpbmc6NzcwOTkzMjIzNDQ5MTE1NDE3",
      "name": "Room with Wembley view",
      "rating": "4.98 (42)",
      "price": "$142",
      "price_qualifier": "total",
      "latitude": 51.5589,
      "longitude": -0.2789,
      "badges": ["Guest favorite"],
      "url": "https://www.airbnb.com/rooms/770993223449115417"
    }
  ]
}
```

---

### 2. Get Listing Detail (`listings get`)

**URL Pattern:** `GET https://www.airbnb.com/rooms/{listing_id}`

**URL Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `listing_id` | path | Yes | Integer listing ID, e.g. `770993223449115417` |
| `adults` | int | No | Number of adults |
| `check_in` | date | No | Check-in date YYYY-MM-DD |
| `check_out` | date | No | Check-out date YYYY-MM-DD |
| `locale` | string | No | Language code |
| `currency` | string | No | Currency code |

**Response Extraction:**
```python
niobe = extract_niobe_data(html, 'StaysPdpSections')
pdp = niobe['data']['presentation']['stayProductDetailPage']
sections = pdp.get('sections', [])

# Also in bootstrap data (server initializer script):
# Look for <script type="application/json"> with "bootstrapData" structure
# Contains host info, amenities, description, reviews summary
```

**CLI Output (`--json`):**
```json
{
  "success": true,
  "listing": {
    "id": "770993223449115417",
    "name": "Room with Wembley view",
    "rating": "4.98",
    "review_count": 42,
    "price_per_night": "$142",
    "location": "Wembley Park, London",
    "latitude": 51.5589,
    "longitude": -0.2789,
    "room_type": "Private room",
    "url": "https://www.airbnb.com/rooms/770993223449115417"
  }
}
```

---

### 3. Location Autocomplete (`autocomplete locations`)

**URL:** `GET https://www.airbnb.com/api/v2/autocompletes-personalized`

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | string | Yes | `d306zoyjsyarp7ifhu67rjxn52tv0t20` |
| `user_input` | string | Yes | User's partial location input |
| `locale` | string | Yes | Language code (e.g. `en`) |
| `currency` | string | Yes | Currency code (e.g. `USD`) |
| `num_results` | int | No | Number of suggestions (default 5) |
| `api_version` | string | No | `1.2.0` |

**Response (v1.2.0 API):**
```python
data = response.json()
suggestions = data['autocomplete_terms']
# Each suggestion (api_version=1.2.0):
# {
#   "explore_search_params": {
#     "place_id": "ChIJdd4hrwug2EcRmSrV3Vo6llI",   ← top-level field (NOT in params array)
#     "query": "London",                             ← top-level field
#     "params": [{"key": "acp_id", "value": "..."}] ← only acp_id in array
#   },
#   "display_name": "London",
#   "location": {"google_place_id": "ChIJdd4hrwug2EcRmSrV3Vo6llI", ...}
# }
# NOTE: In api_version 1.2.0, place_id and query are top-level esp fields,
# NOT inside the params array (changed from older API versions).
place_id = esp.get("place_id") or item.get("location", {}).get("google_place_id")
query_text = esp.get("query") or item.get("display_name")
acp_id = next((p["value"] for p in esp.get("params", []) if p.get("key") == "acp_id"), None)
```

**CLI Output (`--json`):**
```json
{
  "success": true,
  "suggestions": [
    {
      "query": "London, United Kingdom",
      "place_id": "ChIJdd4hrwug2EcRmSrV3Vo6llI",
      "display": "London, United Kingdom"
    }
  ]
}
```

---

## Client Implementation Notes

### HTTP Client
```python
from curl_cffi import requests as curl_requests

class AirbnbClient:
    BASE_URL = "https://www.airbnb.com"
    API_KEY = "d306zoyjsyarp7ifhu67rjxn52tv0t20"
    DEFAULT_HEADERS = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    def get_html(self, url: str, params: dict = None) -> str:
        """Fetch Airbnb page with anti-bot evasion."""
        resp = curl_requests.get(
            url,
            params=params,
            headers=self.DEFAULT_HEADERS,
            impersonate="chrome",
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text

    def api_get(self, path: str, params: dict = None) -> dict:
        """Call /api/v2/ REST endpoint."""
        params = params or {}
        params['key'] = self.API_KEY
        resp = curl_requests.get(
            f"{self.BASE_URL}{path}",
            params=params,
            headers=self.DEFAULT_HEADERS,
            impersonate="chrome",
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def search_stays(self, location: str, adults: int = 1, checkin: str = None,
                     checkout: str = None, price_max: int = None, cursor: str = None,
                     locale: str = "en", currency: str = "USD") -> dict:
        """Search stays for a given location."""
        params = {
            "adults": adults,
            "locale": locale,
            "currency": currency,
        }
        if checkin: params["checkin"] = checkin
        if checkout: params["checkout"] = checkout
        if price_max: params["price_max"] = price_max
        if cursor: params["cursor"] = cursor

        url = f"{self.BASE_URL}/s/{location}/homes"
        html = self.get_html(url, params)
        niobe = extract_niobe_data(html, "StaysSearch")
        if not niobe:
            raise ServerError("No StaysSearch data in page HTML")
        results = niobe['data']['presentation']['staysSearch']['results']
        return {
            "listings": results['searchResults'],
            "pagination": results['paginationInfo'],
        }
```

### Location Slug Format
Convert location name to Airbnb URL slug:
- `"London, UK"` → `"London--UK"`
- `"Paris, France"` → `"Paris--France"`
- `"New York, NY, United States"` → `"New-York--NY--United-States"`

Pattern: Replace `, ` with `--`, replace spaces with `-`

### Pagination
```python
# Next page: pass nextPageCursor as cursor param
cursor = results['paginationInfo']['nextPageCursor']  # base64 encoded
# URL param: ?cursor=<base64>
```

---

## Auth (for Wishlists/Booking — Not Yet Captured)

Auth uses cookie-based session. Login flow:
1. Browser login via `sync_playwright()` → `launch_persistent_context()`
2. Extract session cookies: `_airbed_session_id`, `_csrf_token`, `jitney_client_id`
3. Store in `~/.config/cli-web-airbnb/auth.json`
4. Include cookies in all requests

**NOT YET IMPLEMENTED** — Phase 1 only captured public (no-auth) endpoints.

---

## Known Limitations

1. **Locale**: Without `?locale=en`, results may be in local language (Hebrew/etc. based on IP)
2. **Currency**: Price shown in local currency by default — pass `?currency=USD` for USD
3. **Bot protection**: DataDome may still block even with curl_cffi — may need additional headers or rotating user agents
4. **No booking/payment**: Only search and detail viewing is captured; booking requires auth
5. **SSR dependency**: Page HTML must include niobeClientData — Cloudflare/CDN caching may affect this
