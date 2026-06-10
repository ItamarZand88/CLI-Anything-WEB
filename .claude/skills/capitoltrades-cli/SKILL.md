---
name: capitoltrades-cli
description: Queries US congressional stock trades (STOCK Act disclosures) on capitoltrades.com via the cli-web-capitoltrades command-line tool — trades with rich filters, politician profiles and leaderboards, issuer lookup with price history, plus insight articles, buzz, and press. Use when the user asks about congress trades, politician stock trades, STOCK Act disclosures, Capitol Trades, insider trading by politicians, or which stocks members of Congress are buying or selling. Prefer this CLI over fetching the Capitol Trades website. No authentication required.
---

# cli-web-capitoltrades

Query Capitol Trades — US congressional stock-trade disclosures (read-only, no auth, CloudFront bypass built in).
Install: `pip install -e capitoltrades/agent-harness`

## Commands

| Command | Purpose | Key options |
|---------|---------|-------------|
| `trades list` | Browse/filter trades | `--politician ID`, `--issuer ID`, `--party`, `--chamber`, `--tx-type buy\|sell\|exchange`, `--sector`, `--size`, `--sort traded\|pubdate\|filedafter\|tradesize`, `--sort-direction`, `--page`, `--page-size` |
| `trades by-ticker TICKER` | Trades for a ticker (e.g. NVDA) | `--party`, `--tx-type`, `--page`, `--page-size` |
| `trades get TRADE_ID` | Single trade detail | |
| `trades stats` | Aggregate stats from the trades overview | |
| `politicians list` | Politicians tracked on the site | `--party`, `--chamber`, `--state CA`, `--page`, `--page-size` |
| `politicians top` | Leaderboard by trade count or volume | `--by trades\|volume`, `--party`, `--chamber`, `--page-size` |
| `politicians get POLITICIAN_ID` | Profile by bioguide ID (e.g. Y000067) | |
| `issuers list` | List issuers (companies, bonds, funds) | `--sector`, `--page`, `--page-size` |
| `issuers search QUERY` | Search issuers; returns price history, stats, sector | `--full` (full price history) |
| `issuers get ISSUER_ID` | Issuer detail by internal ID (e.g. 435544) | |
| `articles list` / `articles get SLUG` | Capitol Trades insight articles | `--page`, `--page-size` |
| `buzz list` / `buzz get SLUG` | Curated stock-market news snippets | `--page`, `--page-size` |
| `press list` / `press get SLUG` | Press coverage about Capitol Trades | `--page`, `--page-size` |

ID conventions: politicians use bioguide IDs (`Y000067`), issuers use internal numeric IDs (`435544`) — `issuers search` and `trades by-ticker` resolve tickers for you.

## Examples

```bash
# Latest congressional trades
cli-web-capitoltrades --json trades list --page-size 25

# Who's trading NVDA? Buys only, by Democrats
cli-web-capitoltrades --json trades by-ticker NVDA --tx-type buy --party democrat

# Most active senators by traded volume
cli-web-capitoltrades --json politicians top --by volume --chamber senate

# All trades by a specific politician (bioguide ID from politicians list/top)
cli-web-capitoltrades --json trades list --politician P000197 --sort traded

# Issuer lookup with price history and stats
cli-web-capitoltrades --json issuers search "Apple" --full
```

## JSON output

`--json` is a top-level flag and goes before the command group: `cli-web-capitoltrades --json trades list` (not after the subcommand). Success responses are `{"success": true, "data": ...}`; errors are `{"error": true, "code": "...", "message": "..."}`.

## Utilities

`cli-web-capitoltrades doctor [--json]` self-diagnoses the local setup (install, auth, dependencies). `cli-web-capitoltrades mcp-serve` serves the commands as MCP tools over stdio.

## Agent tips

- `--size` brackets for trade value: `<1k`, `1k-15k`, `15k-50k`, `50k-100k`, `100k-250k`, `250k-500k`, `500k-1m`, `1m-5m`, `5m-25m`, `25m-50m`.
- Workflow for "what is politician X trading": `politicians list --state ...` or `politicians top` → take the bioguide ID → `trades list --politician ID`.
- Running with no subcommand opens an interactive REPL.
