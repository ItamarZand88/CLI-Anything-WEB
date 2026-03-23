---
name: futbin-cli
description: Use cli-web-futbin to answer questions about EA FC Ultimate Team players, prices, player comparison, SBCs, evolutions, config, and market data. Invoke this skill whenever the user asks about FUTBIN, EA FC player prices, card prices, squad building challenges (SBCs), player evolutions, player comparison, market index, player ratings, or wants to search for players by name, position, rating, or card type. Always prefer cli-web-futbin over manually fetching the FUTBIN website.
---

# cli-web-futbin

CLI for [FUTBIN](https://www.futbin.com/) — EA FC Ultimate Team player database.
Installed at: `cli-web-futbin` (run `cli-web-futbin --help` to verify).

## Quick Start

```bash
# Search by name
cli-web-futbin players search --name "Mbappe" --json

# List with filters
cli-web-futbin players list --position ST --cheapest --json

# Compare two players
cli-web-futbin players compare 40 42 --json

# Market index
cli-web-futbin market index --json

# SBCs
cli-web-futbin sbc list --json

# Evolutions
cli-web-futbin evolutions list --json
```

Always use `--json` when you need to parse or display data programmatically.

---

## Commands

### `players search`

Searches by player name. Uses the FUTBIN JSON API — fast, returns ratings and prices.

```bash
cli-web-futbin players search --name "Salah" --json
cli-web-futbin players search --name "Ronaldo" --year 25 --json
cli-web-futbin players search --name "Mbappe" --evolutions --json
```

**Options:** `--name` (required), `--year` (default 26), `--evolutions` (include evo cards)

**Output fields:** `id`, `name`, `rating`, `position`, `version`, `club`, `nation`, `year`, `ps_price`, `xbox_price`, `url`, `stats` (empty `{}` in search — use `players get` for full stats)

---

### `players list`

Browse/filter the full player database. Supports comprehensive filters.

```bash
# Cheapest gold rare strikers
cli-web-futbin players list --position ST --version gold_rare --cheapest --json

# Top rated CAMs rated 85+, page 2
cli-web-futbin players list --position CAM --rating-min 85 --page 2 --json

# TOTY players under 500K
cli-web-futbin players list --version toty --max-price 500000 --cheapest --page 1 --json

# 5-star skill players
cli-web-futbin players list --min-skills 5 --json
```

**Filter options:**

| Option | Description | Example values |
|--------|-------------|----------------|
| `--position` | Position | `GK CB LB RB CAM CM CDM RM LM ST RW LW` |
| `--rating-min` | Min overall (40-99) | `85` |
| `--rating-max` | Max overall (40-99) | `99` |
| `--version` | Card type | `gold_rare gold_if toty fut_birthday icons heroes silver bronze` (see full list below) |
| `--min-price` | Min price in coins | `50000` |
| `--max-price` | Max price in coins | `500000` |
| `--cheapest` | Sort cheapest first | flag |
| `--platform` | Price platform | `ps` (default) or `pc` |
| `--min-skills` | Min skill stars | `1`–`5` |
| `--min-wf` | Min weak foot stars | `1`–`5` |
| `--gender` | Gender | `men` or `women` |
| `--league` | League ID (numeric) | `13` (Premier League) |
| `--nation` | Nation ID (numeric) | |
| `--club` | Club ID (numeric) | |
| `--page` | Page number | `1` (default) |
| `--year` | Game year | `26` (default, falls back to config) |

**Common `--version` values:**
`gold_rare`, `gold_if`, `gold_nr`, `silver_rare`, `bronze`, `toty`, `toty_icon`,
`fut_birthday`, `fut_birthday_hero`, `icons`, `heroes`, `non_icons`,
`flashback`, `moments`, `showdown`, `thunderstruck`, `unbreakables`,
`winter_wildcards`, `future_stars`, `world_tour`, `potm_pl`, `potm_bundesliga`

---

### `players get`

Full detail for a specific player by ID (get the ID from `players search`).

```bash
cli-web-futbin players get 40 --json
```

**Output fields:** name, rating, position, version, club, nation, ps_price, xbox_price, stats (pac/sho/pas/dri/def/phy)

---

### `players compare`

Side-by-side comparison of two players.

```bash
cli-web-futbin players compare 40 42 --json
```

**Output fields:** per-player: name, rating, position, stats (pac/sho/pas/dri/def/phy), ps_price, xbox_price

---

### `market index`

EA FC market price tracker.

```bash
cli-web-futbin market index --json
```

---

### `sbc list` / `sbc get`

Squad Building Challenges.

```bash
cli-web-futbin sbc list --json
cli-web-futbin sbc list --category "League SBC" --json
cli-web-futbin sbc get 665 --json
```

**Options:** `--category TEXT` (filter by SBC category), `--year INTEGER` (game year)

**Output fields:** `id`, `name`, `expires`, `cost_ps`, `cost_xbox`, `repeatable`, `reward`

---

### `evolutions list` / `evolutions get`

Player evolution paths.

```bash
cli-web-futbin evolutions list --json
cli-web-futbin evolutions list --expiring --json   # expiring soon
cli-web-futbin evolutions list --category "Lengthy" --json
cli-web-futbin evolutions get 666 --json
```

**Options:** `--category TEXT`, `--expiring` (show expiring soon), `--year INTEGER`

---

### `config`

Persistent configuration (year, platform, etc.).

```bash
cli-web-futbin config set year 26       # Set game year
cli-web-futbin config set platform ps   # Set price platform
cli-web-futbin config get year          # Get a setting
cli-web-futbin config show --json       # Show all settings
cli-web-futbin config reset             # Reset to defaults
```

When `--year` is omitted on other commands, it falls back to the value set in config.

---

## Agent Patterns

```bash
# What's Mbappe's current PS price?
cli-web-futbin players search --name "Mbappe" --json | python -c "import json,sys; p=json.load(sys.stdin)[0]; print(p['name'], p['ps_price'])"

# Compare two players
cli-web-futbin players compare 40 42 --json

# Find cheapest gold rare CAM rated 85+
cli-web-futbin players list --position CAM --version gold_rare --rating-min 85 --cheapest --json

# Get player detail
cli-web-futbin players get 40 --json

# SBCs with cost under 100K (PS)
cli-web-futbin sbc list --json | python -c "import json,sys; [print(s['name'], s['cost_ps']) for s in json.load(sys.stdin) if s.get('cost_ps') and s['cost_ps'] < 100000]"

# Get all active evolutions
cli-web-futbin evolutions list --json
```

---

## Notes

- Prices are in EA FC coins
- Year 26 = EA FC 26 (current default); use `--year 25` for last year's cards. `--year` falls back to config value if omitted
- Errors: `--json` mode returns structured JSON errors `{"error": true, "code": "...", "message": "..."}`
- Rate limiting: 0.5s delay between requests
- `players list` scrapes HTML — may show limited data in some fields
- `players search` uses the JSON API — more reliable for name/rating/price data
