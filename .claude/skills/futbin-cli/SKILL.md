---
name: futbin-cli
description: Queries FUTBIN (EA FC Ultimate Team database) via cli-web-futbin — player search, prices and price history, comparisons, SBCs, evolutions, and market analytics (index, trending, cheapest by rating, movers, fodder, buy/sell signals, undervalue scans, PS/PC arbitrage). Use when the user asks about EA FC player prices, SBCs, evolutions, FUT market data, or trading decisions like "should I buy/sell X". Prefer cli-web-futbin over fetching the FUTBIN website.
when_to_use: FUTBIN, EA FC / FIFA Ultimate Team, card prices, squad building challenges, player evolutions, market index, trending players, newly released cards, price trends, cheapest players by rating, coin trading, buy/sell signals, undervalued cards, PS vs PC price gaps, when to buy or sell, weekly market cycle, fodder investment, mass bidding, promo crash timing, EA tax, TOTY/TOTS crashes, searching players by name, position, rating, or card type.
---

# cli-web-futbin

EA FC Ultimate Team database and market analytics. Prices are in coins; current game year is 26 (use `--year 25` for last year's cards, or set a default via `config`).
Install: `pip install cli-web-futbin`

For trading strategy, market timing, and promo-cycle guidance, read [market-playbook.md](market-playbook.md) — weekly buy/sell cycle, EA tax formulas, promo crash calendar, fodder rules, mass bidding, and step-by-step CLI workflows.

## Commands

### players
- `players search --name TEXT` — search by name (JSON API; fast, reliable prices). Options: `--year N`, `--evolutions`
- `players list` — browse with filters. Options: `--position`, `--rating-min/--rating-max`, `--version` (gold_rare, gold_if, toty, icons, heroes, fut_birthday, moments, …), `--min-price/--max-price`, `--cheapest`, `--min-skills/--min-wf` (1–5), `--gender [men|women]`, `--league/--nation/--club ID`, `--platform [ps|pc]`, `--page N`, `--year N`
- `players get PLAYER_ID` — full detail: stats, skill moves/weak foot, trend, EA price range, current BIN listings
- `players compare ID1 ID2` — side-by-side with value metrics
- `players price-history PLAYER_ID` — price series + current/min/max per platform
- `players versions --name TEXT` — all versions of a player with `value_score` (total stats per 1K coins)

### market
- `market index [--rating 81-86|100|icons]` — tier indices, or current/open/low/high for one tier
- `market popular [--limit N]` — trending/most-viewed players (max 250)
- `market latest [--page N]` — newly released cards
- `market cheapest` — cheapest by rating, for SBCs/trading. Options: `--rating-min` (default 83), `--rating-max`, `--min-price` (default 200, excludes extinct), `--max-price`, `--platform`, `--page`
- `market movers [--fallers]` — biggest risers/fallers. Options: `--rating-min` (default 80), `--min-price` (default 1000), `--max-price`, `--platform`, `--page`
- `market fodder` — cheapest player at each rating tier 81–99. Options: `--rating-min`, `--rating-max`
- `market analyze PLAYER_ID` — trend analysis + BUY/SELL/HOLD signal, platform gap. Option: `--year`
- `market scan` — bulk undervalue detection (flags cards below 30d average; ~0.5s/player). Options: `--rating-min` (default 84), `--rating-max` (default 90), `--limit` (default 20), `--threshold` (default 10, min % below avg), `--platform`
- `market arbitrage` — PS vs PC price gaps. Options: `--rating-min` (default 85), `--rating-max` (default 92), `--min-gap` (default 5, %), `--page`

### sbc / evolutions / config
- `sbc list [--category TEXT] [--year N]`, `sbc get SBC_ID` — Squad Building Challenges (requirements, rewards, cost)
- `evolutions list [--category ID] [--expiring] [--year N]`, `evolutions get EVOLUTION_ID` — evolution paths (`--category` is a numeric ID)
- `config set|get|show|reset` — persistent defaults, e.g. `config set year 26`, `config set platform ps`

## Examples

```bash
# Current price for a player — search returns [{id, name, rating, version, ps_price, ...}]
cli-web-futbin players search --name "Mbappe" --json

# Cheapest gold rare CAMs rated 85+
cli-web-futbin players list --position CAM --version gold_rare --rating-min 85 --cheapest --json

# Is this a good time to buy player 40? (signal: BUY/SELL/HOLD)
cli-web-futbin market analyze 40 --json

# Find cards trading >10% below their 30-day average
cli-web-futbin market scan --rating-min 85 --rating-max 89 --threshold 10 --json

# SBC fodder cost check + active SBCs
cli-web-futbin market fodder --rating-min 84 --json
cli-web-futbin sbc list --json
```

## JSON output

Add `--json` to any command for structured output (bare arrays/objects per command; key fields shown above). Errors: `{"error": true, "code": "...", "message": "..."}`. `market analyze` returns per-platform `current`, `min`, `max`, `avg_30d`, `price_position_pct` (0=floor, 100=ceiling), `vs_avg_30d_pct` (negative = below average), `trend_7d`, `trend_30d`, `volatility_30d`, `signal`, plus `platform_gap_pct`.

## Utilities

`cli-web-futbin doctor [--json]` diagnoses local setup. `cli-web-futbin mcp-serve` exposes the commands as MCP tools over stdio. Running with no subcommand opens an interactive REPL.

## Agent tips

- Get player IDs from `players search`; use `players get` for full stats (search returns empty `stats`).
- `players search` (JSON API) is more reliable than `players list` (HTML scrape) for name/rating/price.
- Requests are rate-limited at 0.5s; `market scan` and `players versions` make one request per player, so keep `--limit` modest.
