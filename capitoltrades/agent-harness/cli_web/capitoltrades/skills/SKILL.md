---
name: capitoltrades-cli
description: Use cli-web-capitoltrades to query US congressional stock trades, politicians,
  issuers, and insight articles from capitoltrades.com. Invoke this skill whenever the
  user asks about congressional trading, senator/representative stock trades, STOCK Act
  filings, insider trades by politicians, specific tickers (e.g. "what did Pelosi buy"),
  or US Capitol Trades data. Always prefer cli-web-capitoltrades over manually fetching
  the website — no auth is required and the CLI returns structured JSON.
---

# cli-web-capitoltrades

Browse US congressional stock trades tracked on capitoltrades.com (by 2iQ Research).
Installed at: `cli-web-capitoltrades`.

The site is a fully public data aggregator covering STOCK Act disclosures: ~35,000
trades, ~200 politicians, ~3,000 issuers. No authentication required.

## Quick Start

```bash
# Latest trades across Congress
cli-web-capitoltrades --json trades list --page-size 20

# Trades by a specific politician (bioguide ID)
cli-web-capitoltrades --json trades list --politician P000197

# Trades for a ticker (auto-resolves via BFF)
cli-web-capitoltrades --json trades by-ticker NVDA --page-size 20

# Only large-size trades ($1M-$5M)
cli-web-capitoltrades --json trades list --size 1M-5M

# Top politicians by trade volume
cli-web-capitoltrades --json politicians top --by volume --page-size 10

# Aggregate stats (total trades, volume, politicians)
cli-web-capitoltrades --json trades stats

# Rich issuer data (sector, market cap, 1-year price history, #politicians holding)
cli-web-capitoltrades --json issuers search nvidia
```

Always pass `--json` when parsing output programmatically.

---

## Commands

### `trades list`
List trades, paginated and filterable.

```bash
cli-web-capitoltrades trades list [options] --json
```

**Key options:**
- `--page N` / `--page-size N` — pagination (default 1, 12)
- `--politician <bioguide_id>` — e.g. `P000197` (Pelosi)
- `--issuer <issuer_id>` — e.g. `429725` (Amgen)
- `--party republican|democrat|independent`
- `--chamber house|senate`
- `--tx-type buy|sell|exchange`
- `--sector <name>` (e.g. `health-care`, `information-technology`)
- `--size <bracket>` — one of `<1K`, `1K-15K`, `15K-50K`, `50K-100K`, `100K-250K`, `250K-500K`, `500K-1M`, `1M-5M`, `5M-25M`, `25M-50M`
- `--sort traded|pubDate|filedAfter|tradeSize` — sort column
- `--sort-direction asc|desc` (default `desc`)

**Output fields:** `trade_id`, `politician_id`, `politician_name`, `politician_party`,
`politician_chamber`, `politician_state`, `issuer_id`, `issuer_name`, `ticker`,
`tx_type`, `size`, `price`, `traded`, `published`, `filed_after_days`, `owner`.

### `trades get <trade_id>`
Get full detail for a single trade (adds `price`, `shares`, `filing_url`, `comment`, `reporting_gap`).

### `trades by-ticker <SYM>`
Convenience: resolve a ticker (e.g. `NVDA`, `AMGN`) via BFF search, then list trades for
that issuer. Accepts `--party`, `--tx-type`, `--page`, `--page-size`. Returned `meta.resolved_issuer`
includes name, ticker, sector, issuer_id.

### `trades stats`
Overview stats from the `/trades` landing page. Returns `trades`, `filings`, `volume`,
`politicians`, `issuers`.

### `politicians list`
List politicians with filters.

**Key options:** `--party republican|democrat|independent`, `--chamber house|senate`, `--state <ST>`.

**Output fields:** `politician_id` (bioguide), `name`, `party`, `state`, `trades_count`,
`issuers_count`, `volume`, `last_traded`.

### `politicians top`
Leaderboard of politicians ranked by recent activity.

**Key options:** `--by trades|volume` (default `trades`), `--page-size N`, `--party`, `--chamber`.

### `politicians get <bioguide_id>`
Politician detail + recent trades table. Example: `cli-web-capitoltrades politicians get Y000067`.

### `issuers list`
List issuers (companies, funds, treasuries). Output: `issuer_id`, `name`, `ticker`.

### `issuers get <issuer_id>`
Issuer detail + recent trades. Example: `cli-web-capitoltrades issuers get 435544` (US Treasury Bills).

### `issuers search <query>`
**Richest endpoint.** Uses the BFF JSON API — returns sector, market cap, 1-year price
history (`performance.eodPrices`), trailing returns, and `stats.countPoliticians` /
`countTrades` / `volume` / `dateFirstTraded`. Use `--full` to include the full `eodPrices` array.

### `articles list` / `articles get <slug>`
List or view insight articles. Slug format: `kebab-title-YYYY-MM-DD`.

### `buzz list` / `buzz get <slug>`
Third-party news snippets curated by Capitol Trades (Twitter, external articles about
companies and politicians). Same slug format as articles.

### `press list` / `press get <slug>`
Press coverage about Capitol Trades data and congressional trading news (articles
published by external publications like CNN, Forbes, Politico).

---

## Agent Patterns

```bash
# Find all buys of NVIDIA this year by Republicans
cli-web-capitoltrades --json issuers search nvidia | \
  python -c "import json, sys; d=json.load(sys.stdin); print(d['data'][0]['_issuerId'])"
# → take the issuer_id, then:
cli-web-capitoltrades --json trades list --issuer 433382 --party republican --tx-type buy --page-size 50

# Summary of a politician's most active tickers
cli-web-capitoltrades --json politicians get P000197 | \
  python -c "import json, sys, collections; d=json.load(sys.stdin); \
    trades=d['data']['recent_trades']; \
    print(collections.Counter(t['ticker'] for t in trades).most_common(5))"

# Today's biggest trades
cli-web-capitoltrades --json trades list --page-size 50 | \
  python -c "import json, sys; d=json.load(sys.stdin); \
    for t in d['data'][:10]: print(f\"{t['traded']}  {t['tx_type']:<5} {t['politician_name']:<25} {t['ticker']:<10} {t['size']}\")"
```

---

## Data Model Notes

- **Bioguide IDs** (`politician_id`): 7 chars, `[A-Z]\d{6}`, the same ID used by bioguide.congress.gov
- **Issuer IDs**: numeric strings assigned by 2iQ Research
- **Trade IDs**: 11-digit numeric strings
- **Trade sizes** are ranges (`1K–15K`, `15K–50K`, `50K–100K`, `100K–250K`, `250K–500K`, `500K–1M`, `1M–5M`, `5M–25M`, `25M–50M`, `>50M`) — the STOCK Act only requires range disclosure, not exact amounts
- **`owner`** = `Self`, `Spouse`, `Child`, `Joint`, `Undisclosed`, `Dependent`, etc.
- **`filed_after_days`** = days between trade and disclosure (45 days = late, per STOCK Act)

## Notes

- **Auth:** None — fully public site
- **Rate limits:** Site is served via AWS CloudFront; the CLI uses `curl_cffi` with Chrome 136 TLS
  fingerprinting, which is what makes the BFF accessible. No observed rate limits in normal use.
- **Freshness:** Data is typically <24h behind actual filings. Politician disclosures may lag up
  to 45 days (legal requirement) after the trade date.
- **Exit codes:** 0 success, 1 user error (not found / invalid arg), 2 system error (network / 5xx).
- **BFF quirks:** Only `/issuers?search=...` is exposed publicly. Other endpoints on bff.capitoltrades.com return 503.

## Known limitations

- **No full politician search** in the BFF — use `politicians list` with filters, or browse the
  paginated list.
- **No trades search by ticker directly** — search the issuer by ticker first, take its `_issuerId`,
  then filter trades by `--issuer <id>`.
- Reading large result sets (`--page-size 100`) may take a few seconds per page (HTML scraping).
