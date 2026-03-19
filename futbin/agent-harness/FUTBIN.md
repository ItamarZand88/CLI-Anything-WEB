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
  ?name={name}        # filter by name
  ?ps_price={min}-{max}  # filter by PS price range
  ?sort={field}       # sort field (ps_price, rating, etc.)
  ?order={asc|desc}
  ?page={n}
```
Returns: HTML page with player table. Scrape with BeautifulSoup.

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
│   ├── get --id <id> [--year N] [--json]
│   ├── list [--name <filter>] [--min-price N] [--max-price N] [--sort field] [--page N] [--json]
│   └── compare <id1> <id2> [--year N] [--json]
├── market
│   └── index [--json]
├── sbc
│   ├── list [--category <cat>] [--json]
│   └── get --id <id> [--year N] [--json]
├── evolutions
│   ├── list [--category <cat>] [--expiring] [--json]
│   └── get --id <id> [--json]
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
