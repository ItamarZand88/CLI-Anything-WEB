# cli-web-capitoltrades

Agent-native CLI for [capitoltrades.com](https://www.capitoltrades.com/) — browse
US congressional stock trades, politicians, issuers, and articles from the terminal.

## Install

```bash
cd agent-harness
pip install -e .
```

Binary: `cli-web-capitoltrades`

## Quickstart

```bash
# Latest 12 trades
cli-web-capitoltrades trades list

# As JSON (agent-friendly)
cli-web-capitoltrades --json trades list --page-size 50

# Filter: Republican buys only
cli-web-capitoltrades trades list --party republican --tx-type buy

# Trade detail
cli-web-capitoltrades trades get 20003797393

# Overview stats
cli-web-capitoltrades trades stats

# Politicians
cli-web-capitoltrades politicians list
cli-web-capitoltrades politicians get Y000067

# Issuers
cli-web-capitoltrades issuers list
cli-web-capitoltrades issuers get 435544
cli-web-capitoltrades issuers search amgen

# Articles / insights
cli-web-capitoltrades articles list
cli-web-capitoltrades articles get a-foreign-affairs-committee-member-just-bought-defense-stocks-2026-04-23

# Interactive REPL
cli-web-capitoltrades
```

## Commands

| Group | Command | Purpose |
|-------|---------|---------|
| `trades` | `list` | List trades, paginated, filterable by politician, issuer, party, tx-type, sector |
| `trades` | `get <trade_id>` | Get single trade by ID |
| `trades` | `stats` | Overview stats (total trades, volume, politician count, etc.) |
| `politicians` | `list` | List politicians with filters |
| `politicians` | `get <bioguide_id>` | Single politician (e.g. `Y000067`) + recent trades |
| `issuers` | `list` | List issuers |
| `issuers` | `get <issuer_id>` | Single issuer (e.g. `435544`) + recent trades |
| `issuers` | `search <query>` | Search issuers via BFF JSON (returns rich data: prices, sector, stats) |
| `articles` | `list` | List insight articles |
| `articles` | `get <slug>` | Full article body |
| `buzz` | `list` | List curated third-party news snippets |
| `buzz` | `get <slug>` | Full buzz item (Twitter, external articles) |
| `press` | `list` | List press coverage about Capitol Trades |
| `press` | `get <slug>` | Full press article |
| `trades` | `by-ticker <SYM>` | Trades for a ticker — resolves via BFF (e.g. `NVDA`, `AMGN`) |
| `politicians` | `top [--by trades\|volume]` | Politician leaderboard by activity |

## Flags

- `--json` — output structured JSON on every command (agent-native)
- `--help` — show help for any subcommand

## Design

- **No authentication** required — capitoltrades.com is a public read-only site
- **curl_cffi with `impersonate='chrome136'`** bypasses AWS CloudFront bot protection
- **SSR HTML scraping** (BeautifulSoup) for list/detail pages
- **BFF JSON API** (`bff.capitoltrades.com/issuers?search=...`) for rich issuer data including 1-year price history

See `CAPITOLTRADES.md` (in `agent-harness/`) for the full API map.

## Exit codes

- `0` — success
- `1` — user-level error (not found, invalid arg)
- `2` — system error (server 5xx, network)
- `130` — user interrupt (Ctrl-C)

## License

MIT
