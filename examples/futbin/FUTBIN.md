# FUTBIN.md — Software-Specific SOP

## Overview

**App:** FUTBIN (futbin.com)
**Purpose:** EA FC 26 Ultimate Team database — player stats, prices, SBCs, market index, evolutions
**Protocol:** Server-side rendered HTML (Kotlin backend) with one JSON search API + HTMX fragments
**Auth:** Cookie-based (most features public, login required for comments/voting/saved content)

---

## API Surface

### JSON API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/players/search?query={name}&year=26&targetPage=PLAYER_PAGE&evolutions=false` | GET | Player search — returns JSON array |

### HTML Pages (scrape with BeautifulSoup)

| URL Pattern | Description | Key Data |
|-------------|-------------|----------|
| `/players?page={n}&position={pos}&sort={field}&order={asc\|desc}` | Player list | Table rows: name, rating, position, price, stats |
| `/26/player/{id}/{slug}` | Player detail | Embedded JSON ratings, price sparkline, stats |
| `/26/player/{id}/{slug}/prices` | Price history | `data-ps-data`/`data-pc-data` attrs: `[[timestamp,price],...]` |
| `/squad-building-challenges` | SBC list | SBC names, costs, expiry |
| `/squad-building-challenges/{category}` | SBC category | Players, Upgrades, Challenges, Icons, Expiring-soon |
| `/market` | Market index | Index 100 value, change % |
| `/market/{rating}` | Rating index | Index per rating tier (81-86) |
| `/evolutions` | Evolutions list | Active evolutions |
| `/popular` | Popular players | Trending player list |
| `/latest` | Latest players | Recently added players |

### HTMX Fragments

| URL Pattern | Description |
|-------------|-------------|
| `/26/player/chemistry-link-fragment?playerCardId={id}&linkType={perfect\|strong\|weak}&page=1` | Chemistry links |
| `/26/comments/threads?pageType=1&pageId={id}&sorting={top\|new\|controversial}` | Comments |
| `/26/reviews/player/{id}` | Player reviews |
| `/market/index-table` | Market index table (Name, Last, Change %) |

---

## Data Model

### Player
- `id` (int) — unique FUTBIN player card ID
- `name` (str)
- `position` (str) — ST, CM, CB, LW, RW, CAM, CDM, LB, RB, GK
- `rating` (int) — overall rating
- `version` (str) — card type (Gold, TOTY, FUT Birthday, etc.)
- `club` (str), `league` (str), `nation` (str)
- `price_ps` (int) — PlayStation price
- `price_pc` (int) — PC price
- `futbin_rating` (float) — FUTBIN community rating
- `stats` — PAC, SHO, PAS, DRI, DEF, PHY
- `skill_moves` (int), `weak_foot` (int)
- `slug` (str) — URL slug

### Price Point
- `timestamp` (int) — Unix ms
- `price` (int) — coin value

### SBC
- `name` (str)
- `category` (str) — Players, Upgrades, Challenges, Icons
- `cost` (str) — estimated cost
- `expires` (str) — expiry info

### Market Index
- `name` (str) — e.g. "Index 100"
- `value` (float) — current index value
- `change_pct` (float) — daily change percentage

---

## Auth Scheme

- **Most features are public** — no auth required for player search, stats, prices, SBCs, market
- Cookie-based session for login-required features (comments, voting, saved squads)
- Cloudflare protection: `cf_clearance` cookie
- For CLI purposes: cookie auth via Playwright or Chrome CDP, stored at `~/.config/cli-web-futbin/auth.json`

---

## CLI Command Architecture

```
cli-web-futbin
├── players
│   ├── search --query <name> [--year 26]
│   ├── list [--page N] [--position POS] [--sort FIELD] [--order asc|desc] [--version VER]
│   ├── get --id <id>
│   └── prices --id <id> [--platform ps|pc]
├── sbc
│   ├── list [--category CAT]
│   ├── cheapest [--rating N]
│   └── best
├── market
│   ├── index [--rating N]
│   └── players
├── evolutions
│   ├── list [--category CAT] [--expiring]
│   └── popular
├── popular
├── latest
└── auth
    ├── login [--from-chrome | --cookies-json FILE]
    ├── status
    └── logout
```

Every command supports `--json` for structured output.

---

## Scraping Strategy

Since FUTBIN is primarily server-rendered, the client uses `httpx` + `BeautifulSoup4` to:
1. Fetch HTML pages with proper headers (User-Agent, Referer)
2. Parse tables for player lists
3. Extract embedded JSON from `<script type="application/json">` tags
4. Parse `data-ps-data`/`data-pc-data` attributes for price history
5. Use the one JSON API (`/players/search`) directly

### Required Headers
```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Referer: https://www.futbin.com/
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
```

### Cloudflare Considerations
- May need `cf_clearance` cookie for anti-bot protection
- Respect rate limits — add delays between requests
- Use session persistence for cookie management

---

## Implementation Notes

- **No RPC subpackage needed** — this is standard HTTP + HTML scraping
- **BeautifulSoup4** is a required dependency for HTML parsing
- Player IDs are numeric (e.g., 21610)
- Player slugs are lowercase hyphenated names (e.g., "lionel-messi")
- Year prefix in URLs (e.g., `/26/`) — default to current year (26)
- Platform prices: PS (default) and PC
- Price data in `data-ps-data` attributes is `[[timestamp_ms, price], ...]` JSON arrays
