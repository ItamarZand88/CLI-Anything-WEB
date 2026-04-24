# CAPITOLTRADES.md — API Map & Design

## Overview

- **URL**: https://www.capitoltrades.com/
- **Backend**: Next.js 15 App Router with React Server Components (SSR) + a limited BFF at `bff.capitoltrades.com`
- **Auth**: **none** (public read-only site)
- **Protection**: AWS CloudFront TLS fingerprint check → use `curl_cffi` with `impersonate='chrome136'`
- **Protocol**: hybrid SSR HTML scraping + JSON autocomplete

Note: This is a **read-only** CLI. No create/update/delete operations — the site
is a public data aggregator.

## API Surface

### BFF JSON API
| Method | Path | Params | Returns |
|--------|------|--------|---------|
| GET | `https://bff.capitoltrades.com/issuers` | `search=<str>` | `{meta:{paging}, data:[{_issuerId, issuerName, issuerTicker, sector, mcap, performance{eodPrices,trailing...}, stats}]}` |

All other `bff.*` paths return 503 — only issuer autocomplete is exposed.

### SSR HTML pages

Pages rendered with data embedded in HTML. Fetch with `curl_cffi` (chrome136) and
parse with BeautifulSoup.

| Path | Query params | Content |
|------|--------------|---------|
| `/trades` | `page`, `pageSize`, `politician`, `issuer`, `txType`, `party`, `chamber`, `sector`, `tradeSize` (int 1–10), `sortBy`, `sortDirection` | 12-row table per page; total counts at top |
| `/trades/{id}` | — | Trade detail (politician, issuer, dates, size, price) |
| `/politicians` | `page`, `pageSize`, `party`, `chamber`, `state`, `sortBy` (`tradeCount`, `volume`), `sortDirection` | Politician cards |
| `/politicians/{bioguide_id}` | — | Politician detail + recent trades table |
| `/issuers` | `page`, `pageSize`, `sector` | Issuer cards |
| `/issuers/{id}` | — | Issuer detail + recent trades table |
| `/articles` | `page` | Insight/article list |
| `/articles/{slug}` | — | Article detail |
| `/buzz` | `page`, `pageSize` | Curated third-party news snippets |
| `/buzz/{slug}` | — | Buzz item detail |
| `/press` | `page`, `pageSize` | Press coverage list |
| `/press/{slug}` | — | Press item detail |

### `tradeSize` integer mapping (discovered by probing)

| ID | Bracket | ID | Bracket |
|----|---------|----|---------|
| 1 | `<1K` | 6 | `250K-500K` |
| 2 | `1K-15K` | 7 | `500K-1M` |
| 3 | `15K-50K` | 8 | `1M-5M` |
| 4 | `50K-100K` | 9 | `5M-25M` |
| 5 | `100K-250K` | 10 | `25M-50M` |

### Parameters that DON'T work (tested and confirmed ignored)

- `size=<text>` — pass the integer `tradeSize=<N>` instead.
- `assetType=<name>` — the site doesn't filter on this query param.
- `publishedFrom` / `publishedTo` — not honored by the server.

### Identifiers
- **Politician ID**: 7-char bioguide ID, e.g. `Y000067`, `C001123`
- **Issuer ID**: numeric string, e.g. `435544`, `429725`
- **Trade ID**: 11-digit numeric, e.g. `20003797393`
- **Article slug**: kebab-case with `YYYY-MM-DD` suffix

## Command Structure

```
cli-web-capitoltrades [--json]
├── trades
│   ├── list              # paginated, filter: politician, issuer, party, chamber,
│   │                     # tx-type, sector, size, sort, sort-direction
│   ├── get <id>          # single trade (all fields incl. filing URL)
│   ├── by-ticker <SYM>   # resolves ticker → issuer_id via BFF, then lists trades
│   └── stats             # overview aggregates
├── politicians
│   ├── list              # paginated, filter: party, chamber, state
│   ├── top [--by ...]    # leaderboard by trades or volume
│   └── get <id>          # single politician + trades
├── issuers
│   ├── list              # paginated
│   ├── get <id>          # single issuer + trades
│   └── search <q>        # BFF search (rich JSON: prices, stats, sector)
├── articles
│   ├── list
│   └── get <slug>
├── buzz
│   ├── list              # third-party news snippets
│   └── get <slug>
└── press
    ├── list              # press coverage about Capitol Trades
    └── get <slug>
```

## Implementation Notes

### HTTP client
- `curl_cffi.requests.Session` with `impersonate='chrome136'`
- No cookies, no auth tokens needed
- Default headers set Origin/Referer to capitoltrades.com for BFF requests

### Parsers
- `bs4.BeautifulSoup(html, "html.parser")`
- Trades list: `<table>` with fixed 9-column structure
- Politicians/issuers list: `<a href="/politicians/...">` card divs
- Trade detail: look for `tx-type--(buy|sell|exchange)` classes + `/politicians/` + `/issuers/` links

### Exit codes
- 0 — success
- 1 — user-level error (e.g. `NotFoundError` on a missing trade)
- 2 — system error (network, server 5xx)
- 130 — Ctrl-C

### JSON output
- `{success: true, data: ..., meta: ...}` on success
- `{error: true, code: <CODE>, message: ...}` on failure
- Error codes: `NOT_FOUND`, `SERVER_ERROR`, `NETWORK_ERROR`, `RATE_LIMITED`, `INTERNAL_ERROR`

### Data shape examples

Trade (list row):
```json
{
  "trade_id": "20003797393",
  "politician_id": "S001203",
  "politician_name": "Maria Elvira Salazar",
  "issuer_id": "429725",
  "issuer_name": "Amgen Inc",
  "ticker": "AMGN:US",
  "tx_type": "buy",
  "size": "15K–50K",
  "price": "$348.43",
  "traded": "24 Mar 2026",
  "published": "13:05 Yesterday",
  "filed_after_days": "days 28",
  "owner": "Undisclosed"
}
```

Issuer (from `issuers search`):
```json
{
  "_issuerId": 429725,
  "issuerName": "Amgen Inc",
  "issuerTicker": "AMGN:US",
  "sector": "health-care",
  "mcap": 187470072000,
  "performance": {
    "trailing1": 1.06,
    "trailing30": -2.51,
    "ytd": 18.61,
    "latest_price": ["2026-04-22", 345.92]
  },
  "stats": {"countPoliticians": 21, "countTrades": 63, "volume": 1072500}
}
```
