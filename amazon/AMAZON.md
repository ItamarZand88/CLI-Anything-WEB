# Amazon.com — API Map

Generated from Phase 1 traffic capture (2026-04-04).

---

## Protocol Summary

- **Base URL**: `https://www.amazon.com`
- **Protocol type**: SSR HTML (primary) + REST JSON (dynamic components)
- **Auth**: Amazon OpenID 2.0 — email/password → `session-id` + `session-token` cookies
- **CSRF**: `anti-csrftoken-a2z` token (extracted from each page's form HTML)
- **Locale**: Page is served in browser/account locale (tested: `he-il`). Use English locale by setting `Accept-Language: en-US` header or appending `?language=en_US` to URLs.

---

## Authentication

### Sign-In Flow

```
Step 1: GET https://www.amazon.com/ap/signin
        ?openid.pape.max_auth_age=0
        &openid.return_to=https://www.amazon.com/
        &openid.identity=http://specs.openid.net/auth/2.0/identifier_select
        &openid.assoc_handle=usflex
        &openid.mode=checkid_setup
        &openid.claimed_id=http://specs.openid.net/auth/2.0/identifier_select
        &openid.ns=http://specs.openid.net/auth/2.0
        Response: HTML form (id=ap_login_form)
                  Extract: anti-csrftoken-a2z, metadata1, arb (random nonce), webAuthnChallengeId

Step 2: POST https://www.amazon.com/ax/claim
        ?policy_handle=Retail-Checkout
        &openid.return_to=<return_to>
        &openid.ns=...
        &arb=<nonce from step 1>
        &openid.assoc_handle=usflex
        &openid.mode=checkid_setup
        Body (form-urlencoded):
          appAction=SIGNIN_CLAIM_COLLECT
          subPageType=FullPageUnifiedClaimCollect
          claimCollectionWorkflow=unified
          metadata1=<large base64 device fingerprint — extract live from page>
          anti-csrftoken-a2z=<from step 1 form>
          openid.ns=http://specs.openid.net/auth/2.0
          openid.mode=checkid_setup
          openid.return_to=https://www.amazon.com/
          openid.assoc_handle=usflex
          email=<user email>
          password=<user password>
        Response: Set-Cookie headers (session-id, session-token, ubid-main, x-main)
                  302 redirect to openid.return_to
```

### Session Cookies

| Cookie Name | Scope | Purpose |
|-------------|-------|---------|
| `session-id` | `.amazon.com` | Primary session identifier |
| `session-id-time` | `.amazon.com` | Session creation timestamp |
| `session-token` | `.amazon.com` | Session auth token |
| `ubid-main` | `.amazon.com` | Ubiquitous user ID |
| `x-main` | `.amazon.com` | Auth state marker |

Store cookies at `~/.config/cli-web-amazon/auth.json` (chmod 600).

### Pre-auth Check

```
GET https://www.amazon.com/ax/preauth
Response: {"icaEligible": true, "token": "<ica-token>", ...}
```

---

## Public API Endpoints (No Auth Required)

### 1. Search

```
GET https://www.amazon.com/s
    ?k=<query>                    # Search keywords (required)
    &page=<n>                     # Page number (default: 1, max: ~7)
    &rh=<refinement-hash>         # Filter/refinement (optional)
    &s=<sort>                     # Sort: price-asc-rank, price-desc-rank, review-rank, date-desc-rank
    &i=<store>                    # Store: computers, electronics, fashion, etc.

Response: HTML page
  Extract: product cards with ASIN, title, price, rating, review_count, badge (Prime, etc.)
  Note: Data is in SSR HTML, no embedded JSON. Use BeautifulSoup4 to parse.
  Pagination: links with &page= query param
```

### 2. Search Autocomplete

```
GET https://www.amazon.com/suggestions
    ?alias=aps                    # Search index (aps = all, electronics, etc.)
    &prefix=<partial-query>       # Partial search term
    &mid=ATVPDKIKX0DER            # Marketplace ID (US)
    &session-id=<session-id>      # Optional — improves personalization
    &customer-id=                 # Optional — leave empty for anonymous
    &request-id=<uuid>            # Random request ID
    &page-type=Search
    &lop=en_US                    # Language/locale
    &np=1                         # No personalization flag (optional)

Response: JSON
  {"alias": "aps", "prefix": "", "suffix": "", "suggestions": [
    {"value": "laptop", "type": "..."},
    ...
  ]}

# Alternative endpoint:
GET https://completion.amazon.com/api/2017/suggestions
    ?mid=ATVPDKIKX0DER&alias=aps&fresh=1&q=<query>&session-id=<id>&...
```

### 3. Product Detail

```
GET https://www.amazon.com/dp/<ASIN>
    ?th=1                         # Select default variant
    &language=en_US               # Force English (optional)

Response: HTML page
  Extract: title, price, rating, review_count, ASIN, merchantID, images, description
  Note: Full product page — parse with BeautifulSoup4
  ASIN format: 10-char alphanumeric, e.g. "B0GRZ78683"

# Localized URL format (also works):
GET https://www.amazon.com/-/he/<url-title>/dp/<ASIN>
```

### 4. Product Variants

```
GET https://www.amazon.com/gp/product/ajax/twisterDimensionSlotsDefault
    ?ASIN=<ASIN>                  # Product ASIN
    &Type=JSON
    &merchantId=<merchantId>      # Optional

Response: JSON
  {"ASIN": "B0GRZ78683", "dimensionToAsinMap": {...}, "colorImages": {...}, ...}
  Contains: available ASINs for each size/color variant combination
```

### 5. Best Sellers

```
GET https://www.amazon.com/Best-Sellers/zgbs/<category>
    # category examples: electronics, computers, books, home-kitchen

Response: HTML page
  Extract: ranked product list with ASIN, title, price, rating
```

### 6. Deals / Gold Box

```
GET https://www.amazon.com/gp/goldbox
    ?ref_=nav_cs_gb               # Navigation ref

Response: HTML page
  Extract: deal cards with ASIN, discount percentage, original/deal price, ends-at timestamp
```

### 7. Category Browse

```
GET https://www.amazon.com/gp/browse.html
    ?node=<nodeId>                # Category node ID (e.g., 172282=Electronics)
    &ref_=<nav-ref>               # Navigation reference

Response: HTML page
  Common node IDs: 172282 (Electronics), 1036592 (Computers), 283155 (Books)
```

---

## Dynamic / Lazy-loaded Endpoints

### Cart Config

```
GET https://www.amazon.com/cart/add-to-cart/patc-config
Response: JSON
  {"patcConfig": {"rules": [{"id": "byg_desktop_optimistic_qs_...", ...}]}}
  Used for "Add to Cart" button behavior rules
```

### Recommended Products Shoveler

```
GET https://www.amazon.com/hz/rhf
    ?reftag=<ref>                 # Reference tag
Response: JSON
  {"html": "<div class='rhf-shoveler'>...</div>"}
```

---

## Auth-Gated Endpoints (Require Valid Session Cookies)

### Cart Operations

```
# View cart
GET https://www.amazon.com/gp/cart/view.html
Response: HTML

# Add to cart
POST https://www.amazon.com/gp/product/handle-buy-box
     ?ref=dp_start-bbf_1_glance
Body (form-urlencoded):
  anti-csrftoken-a2z=<token from product page>
  ASIN=<ASIN>
  session-id=<session-id>
  merchantID=<merchantId>
  offerListingID=<offerListingId>  # Optional — preferred over merchantID
  isMerchantExclusive=0
  isAddon=0
  usePrimeHandler=0
  qid=<search-query-id>           # Optional
  viewID=glance
  ctaPageType=detail
Response: 302 redirect to cart or auth if session invalid

# Cart items (AJAX)
GET https://www.amazon.com/cart/add-to-cart/get-cart-items
Response: JSON (cart item list)
```

### Orders

```
GET https://www.amazon.com/gp/your-account/order-history
    ?opt=ab&digitalOrders=0&unifiedOrders=1&returnTo=&orderFilter=<filter>
    # filter: last30, last3months, year-2024, etc.
Response: HTML

GET https://www.amazon.com/gp/your-account/order-details
    ?orderID=<order-id>
Response: HTML
```

### Product Reviews

```
GET https://www.amazon.com/product-reviews/<ASIN>
    ?reviewerType=all_reviews      # or verified_purchase_reviews
    &sortBy=recent                 # or helpful
    &pageNumber=<n>
Response: HTML (requires auth — 302 redirect to sign-in without session)
```

---

## Request Headers

Required for all requests:

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-US,en;q=0.5
```

For auth/write requests, also include cookies:

```http
Cookie: session-id=<id>; session-token=<token>; ubid-main=<ubid>
```

---

## CSRF Token Extraction

The `anti-csrftoken-a2z` token changes per page. Extract it from the HTML:

```python
import re
from bs4 import BeautifulSoup

def extract_csrf(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    token_input = soup.find('input', {'name': 'anti-csrftoken-a2z'})
    if token_input:
        return token_input.get('value', '')
    # Fallback: regex
    m = re.search(r'"anti-csrftoken-a2z"\s+value="([^"]+)"', html)
    return m.group(1) if m else ''
```

---

## HTML Parsing Notes

Amazon's product pages are SSR HTML (not JSON APIs). Key CSS selectors:

| Data | Selector |
|------|----------|
| Product title | `#productTitle` |
| Price | `.a-price .a-offscreen` or `#priceblock_ourprice` |
| Rating | `.a-icon-star .a-icon-alt` |
| Review count | `#acrCustomerReviewText` |
| ASIN | `input[name="ASIN"]` in `#addToCart` form |
| Search result items | `[data-component-type="s-search-result"]` |
| Product ASIN (search) | `[data-asin]` attribute |
| Best seller rank | `#SalesRank` or `.zg-badge-wrapper` |

---

## Rate Limiting

- No explicit rate limit headers observed (no 429 responses in capture)
- Amazon uses bot-detection JS (`BotDetectionJSSignalCollectionAsset`) — avoid high-frequency requests
- Recommended: 1-2 req/sec for scraping, use `time.sleep(0.5-1)` between requests
- The `session-id` and `session-token` cookies are used for both auth and rate-limit tracking

---

## Notes

1. **Locale**: Amazon auto-detects locale from IP/browser. Israeli IPs get `he-il` locale. Force English with `Accept-Language: en-US` header or `?language=en_US` param.
2. **ASIN format**: Always 10 characters, e.g. `B0GRZ78683`, `0306406152` (books)
3. **Pagination**: Search results go up to ~page 7 typically. Use `&page=<n>` param.
4. **Product URL formats**: Both `/dp/<ASIN>` and `/-/<locale>/<title>/dp/<ASIN>` work. Use `/dp/<ASIN>` for simplicity.
5. **Service Worker**: Active on all pages — blocks SW in playwright browser context with `service_workers="block"`.
6. **Cart without auth**: Cart page loads but is empty; add-to-cart requires valid session cookies.
