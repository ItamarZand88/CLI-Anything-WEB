# AMAZON.md — API Map & CLI Spec

## Site Overview

- **URL**: https://www.amazon.com
- **Protocol**: SSR HTML + REST JSON (hybrid)
- **Auth**: None — all implemented commands use public Amazon endpoints.
- **HTTP Library**: `httpx` — no Cloudflare/WAF protection detected.
- **Site Profile**: No-auth + Read-only.
- **Service Worker**: Active on the site, but irrelevant for CLI (direct HTTP requests).

---

## API Endpoints

### Implemented Endpoints

| Endpoint | Method | Protocol | CLI Command |
|----------|--------|----------|-------------|
| `/suggestions?prefix=<q>&limit=11&...` | GET | JSON | `suggest <query>` |
| `/s?k=<query>&page=<n>` | GET | HTML | `search <query>` |
| `/dp/<ASIN>` | GET | HTML | `product get <ASIN>` |
| `/Best-Sellers/zgbs/<category>` | GET | HTML | `bestsellers [<category>]` |

---

## Data Models

### SearchResult
- `asin` (str): Product ASIN (e.g., "B0GRZ78683")
- `title` (str): Product title
- `price` (str): Displayed price string
- `rating` (str): Rating (e.g., "4.5 out of 5 stars")
- `review_count` (str): Number of ratings
- `url` (str): Relative product URL

### Product
- `asin` (str): ASIN
- `title` (str): Full product title
- `price` (str): Price (from a-offscreen span)
- `rating` (str): Rating title from `#acrPopover`
- `review_count` (str): Review count from `#acrCustomerReviewText`
- `brand` (str): Brand/seller from `#bylineInfo`
- `image_url` (str): Main product image URL
- `url` (str): Product page URL

### BestSeller
- `rank` (int): Bestseller rank (1-50+)
- `asin` (str): ASIN
- `title` (str): Product title
- `price` (str): Price
- `url` (str): Product URL

### Suggestion
- `value` (str): Suggestion text
- `type` (str): Suggestion type (KEYWORD, WIDGET, etc.)

---

## Request Headers Required

```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate, br
```

---

## HTML Parsing Notes

### Search Results (`/s?k=<query>`)
- Product cards: `div[data-component-type="s-search-result"]`
- ASIN: `card.get('data-asin')`
- Title: `h2` element text
- Price: `span.a-price-whole` + `span.a-price-fraction`, or `span.a-offscreen`
- Rating: `span.a-icon-alt` text
- URL: `a.a-link-normal[href]` (first product link)

### Product Detail (`/dp/<ASIN>`)
- Title: `#productTitle`
- Price: `span.a-offscreen` (first) or `#corePrice_feature_div span.a-offscreen`
- Rating: `#acrPopover` title attribute
- Reviews: `#acrCustomerReviewText`
- Brand: `#bylineInfo`
- Image: `#landingImage` src or data-old-hires

### Best Sellers (`/Best-Sellers/zgbs/<category>`)
- Container: `div#gridItemRoot` (or `div[id="gridItemRoot"]`)
- Inner product div: `div[data-asin]`
- Rank: `.zg-bdg-text`
- Title: img alt attribute or `a-link-normal` text
- Price: `.p13n-sc-price`
- URL: `a.a-link-normal[href]`

---

## CLI Command Structure

```
cli-web-amazon [--json]
├── suggest <query>                    # Autocomplete suggestions (JSON API)
├── search <query> [--page N] [--dept <dept>]  # Search products (HTML)
├── product
│   └── get <ASIN>                     # Product detail (HTML)
└── bestsellers [<category>]           # Best sellers list (HTML)
```

---

## Notes

- **No auth required**: All commands use public Amazon endpoints.
- **Page language**: Amazon serves pages in the user's locale. CSS class names are consistent regardless of language. The CLI parses using CSS classes, not text content.
- **ASIN format**: 10 alphanumeric characters, typically `B0XXXXXXXX` for standard products.
- **Pagination**: Search supports `?page=N` (typically 1-7 pages). Best sellers has pgN pages.
- **Price availability**: Some product prices are client-side rendered and may be empty in SSR HTML. The `price_note` field explains the reason.
