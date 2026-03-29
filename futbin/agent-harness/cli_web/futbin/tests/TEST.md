# TEST.md — cli-web-futbin Test Plan & Results

## Part 1: Test Plan

### Overview

FUTBIN is a **read-only** public site. No auth is required.
Tests focus on:
1. HTTP client correctness (player search JSON parsing)
2. HTML scraper robustness (player detail, market, SBC, evolutions)
3. CLI command integration (subprocess tests)

---

### Test Layers

| Layer | File | Description |
|-------|------|-------------|
| Unit | `test_core.py` | HTTP client with mocked responses |
| E2E Fixture | `test_e2e.py::test_*_fixture` | Commands replaying cached HTML |
| E2E Live | `test_e2e.py::test_*_live` | Real API calls (network required) |
| CLI subprocess | `test_e2e.py::test_cli_*` | Installed `cli-web-futbin` binary |

---

### Test Cases

#### Unit Tests (`test_core.py`)

**Player Search JSON parsing:**
- `test_parse_player_search` — parse mocked JSON response, verify player fields
- `test_parse_player_search_empty` — empty array returns empty list
- `test_coin_str_to_int` — "150K" → 150000, "1.2M" → 1200000, "1,234" → 1234

**Market index HTML parsing:**
- `test_parse_market_index` — parse mocked HTML table, verify MarketItem fields

**SBC list HTML parsing:**
- `test_parse_sbc_list` — parse mocked SBC page, verify SBC fields

**Evolution list HTML parsing:**
- `test_parse_evolution_list` — parse mocked evolutions page, verify fields

**Client rate limiting:**
- `test_request_delay` — verify >= 0.5s delay between requests

#### E2E Live Tests (`test_e2e.py`)

**Players:**
- `test_players_search_live` — search "Mbappe", expect >= 1 result, id=40 or similar
- `test_players_search_json_live` — `--json` output is valid JSON with expected fields

**Market:**
- `test_market_index_live` — GET /market/index-table, expect >= 1 item

**SBC:**
- `test_sbc_list_live` — GET /squad-building-challenges, expect >= 1 SBC

**Evolutions:**
- `test_evolutions_list_live` — GET /evolutions, expect >= 1 evolution

#### CLI Subprocess Tests (`test_e2e.py`)

- `test_cli_help` — `cli-web-futbin --help` exits 0
- `test_cli_players_search` — `cli-web-futbin players search --name Mbappe --json`
- `test_cli_market_index` — `cli-web-futbin market index --json`
- `test_cli_sbc_list` — `cli-web-futbin sbc list --json`
- `test_cli_evolutions_list` — `cli-web-futbin evolutions list --json`
- `test_cli_auth_status` — `cli-web-futbin auth status --json`
- `test_cli_list_players_filters_json` — `players list --position CAM --rating-min 85 --sort overall --order desc --json`
- `test_cli_list_players_cheapest` — `players list --position GK --cheapest --json`

#### Filter Tests (`test_e2e.py`)

- `test_list_players_position_filter` — `list_players(position="GK")` returns list
- `test_list_players_rating_filter` — `list_players(rating_min=90, rating_max=99)` returns list
- `test_list_players_version_filter` — `list_players(version="toty")` returns list
- `test_list_players_cheapest` — `list_players(position="ST", version="gold_rare", sort="ps_price", order="asc")` returns list

---

## Part 2: Test Results

**Date:** 2026-03-18
**Python:** 3.12.8
**Platform:** Windows 11

### Unit Tests (`test_core.py`)

```
13 passed in 0.44s
```

| Test | Status |
|------|--------|
| test_coin_str_to_int (7 params) | PASS |
| test_parse_player_search | PASS |
| test_parse_player_search_empty | PASS |
| test_parse_market_index | PASS |
| test_parse_sbc_list | PASS |
| test_parse_evolution_list | PASS |
| test_player_to_dict | PASS |

### E2E + CLI Tests (`test_e2e.py`)

```
13 passed in 17.97s
```

| Test | Status |
|------|--------|
| test_cli_help | PASS |
| test_cli_version | PASS |
| test_cli_auth_status_json | PASS |
| test_cli_players_search_json | PASS |
| test_cli_market_index_json | PASS |
| test_cli_sbc_list_json | PASS |
| test_cli_evolutions_list_json | PASS |
| test_players_search_live | PASS |
| test_players_search_returns_player_model | PASS |
| test_market_index_live | PASS |
| test_sbc_list_live | PASS |
| test_evolutions_list_live | PASS |
| test_player_search_json_output | PASS |

**Total: 26/26 PASS (100%)**

### After Parser Improvements

Updated SBC and evolution HTML fixture tests to use exact CSS classes from live site.

**Final run: 26/26 PASS (100%)**

```
Unit:   13/13 passed in 0.44s
E2E:    13/13 passed in 19.30s
Total:  26 passed
```

---

## Part 3: Filter Expansion (Refine)

**Date:** 2026-03-18

Added comprehensive player filter options to `players list` command.

### New Filters Added

| Filter | CLI Option | URL Param | Values |
|--------|-----------|-----------|--------|
| Position | `--position` | `position` | GK, CB, LB, RB, CAM, CM, CDM, RM, LM, ST, RW, LW |
| Min rating | `--rating-min` | `overall` (range) | 40-99 |
| Max rating | `--rating-max` | `overall` (range) | 40-99 |
| Card version | `--version` | `version` | gold_rare, toty, fut_birthday, icons, heroes, ... |
| Platform | `--platform` | `ps_price`/`pc_price` | ps, pc |
| Cheapest | `--cheapest` | sort=ps_price&order=asc | flag |
| Min skills | `--min-skills` | `min_skills` | 1-5 |
| Min weak foot | `--min-wf` | `min_wf` | 1-5 |
| Gender | `--gender` | `gender` | men, women |
| League | `--league` | `league` | numeric ID |
| Nation | `--nation` | `nation` | numeric ID |
| Club | `--club` | `club` | numeric ID |

### Test Results

```
Unit:   13/13 passed in 0.42s
E2E:    19/19 passed in 24.76s
Total:  32 passed
```

| Test | Status |
|------|--------|
| test_list_players_position_filter | PASS |
| test_list_players_rating_filter | PASS |
| test_list_players_version_filter | PASS |
| test_list_players_cheapest | PASS |
| test_cli_list_players_filters_json | PASS |
| test_cli_list_players_cheapest | PASS |

**Total: 32/32 PASS (100%)**

---

## Part 4: Market & Trading Features (Refine)

**Date:** 2026-03-29

Added market analysis commands for finding deals: popular players, latest cards,
cheapest by rating, price history, SBC fodder prices, market movers. Also fixed
`players get` and `players compare` HTML scraping (broken by FUTBIN site redesign).

### New Commands Added

| Command | Description |
|---------|-------------|
| `market popular` | Trending/most-viewed players |
| `market latest` | Newly released cards |
| `market cheapest` | Cheapest players by rating |
| `market movers` | Biggest price risers/fallers |
| `market fodder` | SBC fodder prices per rating tier |
| `market index --rating` | Detailed index for specific tier |
| `players price-history` | Historical price data with trends |

### Bugs Fixed

| Bug | Fix |
|-----|-----|
| `players get` returned rating=0, stats={}, price=None | Rewrote `_parse_player_detail` with current CSS classes |
| `players compare` returned no diffs | Fixed (depends on `get`) |
| `player_rating` vs `overall` param | FUTBIN uses `player_rating` server-side, not `overall` |
| `/latest` page prices null | Added `table-cross-price` / `table-pc-price` CSS classes |

### Test Results

```
Unit:   35/35 passed in 0.5s
E2E:    29/29 passed in 34s
Total:  64 passed
```

| New Test | Status |
|----------|--------|
| test_price_history_to_dict | PASS |
| test_fodder_tier_to_dict | PASS |
| test_price_history_empty | PASS |
| test_cli_market_popular_json | PASS |
| test_cli_market_latest_json | PASS |
| test_cli_market_cheapest_json | PASS |
| test_cli_players_price_history_json | PASS |
| test_cli_market_fodder_json | PASS |
| test_cli_market_movers_json | PASS |
| test_cli_market_movers_fallers_json | PASS |
| test_popular_players_live | PASS |
| test_latest_players_live | PASS |
| test_price_history_live | PASS |
| test_sbc_fodder_live | PASS |
| test_market_movers_live | PASS |

**Total: 64/64 PASS (100%)**
