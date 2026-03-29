# FUTBIN — Software-Specific SOP

## Site Overview

FUTBIN (https://www.futbin.com/) is a **read-only** EA FC Ultimate Team database.
It tracks player prices, ratings, squad building challenges (SBCs), player evolutions,
and market data. No write operations are available to unauthenticated users.

Auth is **not required** for any CLI commands.

---

## API Protocol

**Hybrid: JSON Search API + SSR HTML Scraping**

The site is primarily server-side rendered. Most pages return full HTML.
Only the player search endpoint returns structured JSON.

| Endpoint | Protocol | Returns |
|----------|----------|---------|
| `/players/search` | REST/JSON | Player search results |
| `/players` | SSR HTML | Player database table |
| `/{year}/player/{id}/{name}` | SSR HTML | Player detail + prices + stats |
| `/market/index-table` | HTML fragment | Market index table |
| `/popular` | SSR HTML | Popular/trending player cards |
| `/latest` | SSR HTML | Newly released player cards (table) |
| `/squad-building-challenges` | SSR HTML | SBC list |
| `/{year}/squad-building-challenge/{id}` | SSR HTML | SBC detail |
| `/evolutions` | SSR HTML | Evolutions list |
| `/evolutions/{id}/{name}` | SSR HTML | Evolution detail |

---

## API Endpoints

### Player Search (JSON)
```
GET https://www.futbin.com/players/search
  ?targetPage=PLAYER_PAGE
  &query={name}
  &year={year}        # 26, 25, 24, 23, 22
  &evolutions={bool}  # true/false
```
Returns: JSON array of player matches
```json
[{
  "id": 21747,
  "name": "Kylian Mbappé",
  "position": "ST",
  "version": "TOTY",
  "location": {"url": "/26/player/21747/kylian-mbappe"},
  "ratingSquare": {"rating": "96"},
  "clubImage": {"fixed": {"name": "Real Madrid"}},
  "nationImage": {"fixed": {"name": "France"}}
}]
```

### Players List (HTML scraping)
```
GET https://www.futbin.com/players
  ?name={name}              # filter by name
  ?ps_price={min}-{max}     # filter by PS price range
  ?pc_price={min}-{max}     # filter by PC price range
  ?player_rating={min}-{max} # filter by overall rating (NOT "overall"!)
  ?version={type}           # card version (gold_rare, toty, icons, etc.)
  ?position={pos}           # position filter
  ?sort={field}             # sort field (ps_price, pc_price, etc.)
  ?order={asc|desc}
  ?page={n}
```
Returns: HTML page with player table. Scrape with BeautifulSoup.

**NOTE**: The `player_rating` param works server-side. The `overall` param does NOT
work via plain HTTP — it's handled client-side by JavaScript only.

### Player Detail (HTML scraping)
```
GET https://www.futbin.com/{year}/player/{id}/{slug}
```
Returns: HTML page. Extract:
- Overall rating, position, version
- Stats: PAC, SHO, PAS, DRI, DEF, PHY
- Prices: PS price, XBOX price
- Club, Nation, Weak foot, Skill moves

### Market Index (HTML fragment)
```
GET https://www.futbin.com/market/index-table
```
Returns: HTML `<table>` fragment with Name, Last, Change % columns.

### Popular Players (HTML scraping)
```
GET https://www.futbin.com/popular
```
Returns: HTML page with `a.playercard-wrapper` cards containing rating, position, name,
prices (PS/PC), and stats (PAC/SHO/PAS/DRI/DEF/PHY). Up to 250 cards.

### Latest Players (HTML scraping)
```
GET https://www.futbin.com/latest
  ?page={n}           # pagination
```
Returns: HTML table (same structure as /players but with `table-cross-price` class
for prices and `table-added-on` column for release date).

### Player Price History (embedded in player detail HTML)
```
GET https://www.futbin.com/{year}/player/{id}/{slug}
```
Price history is embedded as JSON in `data-ps-data` and `data-pc-data` attributes
on the price graph elements. Data format: `[[timestamp_ms, price], ...]`.
Typically 180-200 data points covering ~6 months.

### SBC Cheapest / Fodder Prices (HTML scraping)
```
GET https://www.futbin.com/squad-building-challenges/cheapest
```
Returns: HTML page with `.stc-player-column` sections, each containing a rating
header (`.stc-rating`) and player links with format `Name (POS) Price`.
Covers ratings 81-99 with top 5 cheapest players per tier.

### Market Movers (player list sorted by price change)
```
GET https://www.futbin.com/players
  ?sort=ps_price_change    # or pc_price_change
  ?order=desc              # risers (desc) or fallers (asc)
  ?player_rating=80-99     # filter low-rated noise
  ?ps_price=1000-15000000  # filter extinct cards
```
Returns: Same HTML player table as `/players`, sorted by price change %.

### SBC List (HTML scraping)
```
GET https://www.futbin.com/squad-building-challenges
  ?category={cat}    # optional category filter
```
Returns: HTML page with SBC cards.

### SBC Detail (HTML scraping)
```
GET https://www.futbin.com/{year}/squad-building-challenge/{id}
```
Returns: HTML page with SBC requirements and solutions.

### Evolutions List (HTML scraping)
```
GET https://www.futbin.com/evolutions
  ?last_chance={bool}   # true = expiring soon
  ?category={id}        # category filter
```
Returns: HTML page with evolution cards.

### Evolution Detail (HTML scraping)
```
GET https://www.futbin.com/evolutions/{id}/{slug}
```
Returns: HTML page with evolution requirements and eligible players.

---

## Data Models

### Player
- id: int
- name: str
- position: str (ST, CM, GK, etc.)
- version: str (Normal, TOTY, FUT Birthday, etc.)
- rating: int
- club: str
- nation: str
- ps_price: int | None (coins)
- xbox_price: int | None (coins)
- year: int (26, 25, 24, ...)
- url: str (relative path)
- stats: dict (pac, sho, pas, dri, def, phy)

### SBC
- id: int
- name: str
- category: str
- reward: str
- expires: str
- cost_ps: int | None
- cost_xbox: int | None
- repeatable: bool
- year: int

### Evolution
- id: int
- name: str
- category: str
- expires: str
- unlock_time: str
- repeatable: bool
- year: int

### MarketItem
- name: str
- last: str
- change_pct: str

### PriceHistory
- player_id: int
- player_name: str
- year: int
- ps_prices: list[[timestamp_ms, price]]
- pc_prices: list[[timestamp_ms, price]]

---

## URL Pattern

All year-specific resources use the year prefix:
- Year 26 = EA FC 26 (current)
- Year 25 = EA FC 25
- etc.

Default year: 26

---

## Auth Scheme

**None required.** The site is public. All CLI commands work without login.

The `auth` module is present for future compatibility but `auth login` simply
notes that no auth is needed. Cookies can optionally be stored if the user
wants to access their personal data (My Evolutions, Saved Squads).

---

## Rate Limiting

The site does not enforce aggressive rate limiting for normal browsing.
Add 0.5s delay between requests to be respectful.

---

## CLI Command Structure

```
cli-web-futbin
├── players
│   ├── search --name <query> [--year N] [--evolutions] [--json]
│   ├── get <player_id> [--year N] [--json]
│   ├── list [--name <filter>] [--min-price N] [--max-price N] [--sort field] [--page N] [--json]
│   ├── compare <id1> <id2> [--year N] [--json]
│   └── price-history <player_id> [--year N] [--json]
├── market
│   ├── index [--json]
│   ├── popular [--limit N] [--json]
│   ├── latest [--page N] [--json]
│   ├── cheapest [--rating-min N] [--rating-max N] [--max-price N] [--platform ps|pc] [--json]
│   ├── movers [--fallers] [--rating-min N] [--platform ps|pc] [--json]
│   └── fodder [--rating-min N] [--rating-max N] [--json]
├── sbc
│   ├── list [--category <cat>] [--json]
│   └── get <sbc_id> [--year N] [--json]
├── evolutions
│   ├── list [--category <cat>] [--expiring] [--json]
│   └── get <evo_id> [--json]
└── config
    ├── set <key> <value>    # keys: year, platform
    ├── show [--json]
    └── reset
```

---

## Notes for Read-Only Site

- This is a genuine read-only site (no create/update/delete for public users)
- All commands are GET operations
- HTML scraping with BeautifulSoup is required for most endpoints
- The player search JSON API is the most reliable data source
- Prices may be None if the player has no active market listing
