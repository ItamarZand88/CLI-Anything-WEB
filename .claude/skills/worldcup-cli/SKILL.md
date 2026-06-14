---
name: worldcup-cli
description: FIFA World Cup 2026 data via the cli-web-worldcup command — fixtures (nations games), the 48 qualified nations, national-team squads, group standings, and bookmaker odds. Read-only; no betting actions. Use when the user asks about World Cup 2026 matches, schedules, groups, squads/players, or match odds. Data from ESPN (no auth); odds need a free The Odds API key. Prefer this CLI over scraping sportsbook sites.
---

# cli-web-worldcup

FIFA World Cup 2026 on the command line — read-only. Matches, nations,
squads, group standings, and bookmaker odds.
Install: `pip install cli-web-worldcup`

Data sources: **ESPN** public API (no auth) for everything except odds;
**The Odds API** (free key) for `odds`. No bets are ever placed.

## Commands

- `fixtures list` — World Cup matches. Options: `--team TEXT` (name or 3-letter code, e.g. `MEX`), `--dates YYYYMMDD` or `YYYYMMDD-YYYYMMDD` (default: full tournament), `--limit N`
- `fixtures get <event_id>` — one match's detail (status, venue, odds line)
- `teams list` — all 48 qualified nations
- `teams get <id|code|name>` — one nation (e.g. `MEX`, `Mexico`, `203`)
- `players roster <id|code|name>` — a nation's squad
- `standings list` — group tables. Option: `--group A`
- `odds list` — bookmaker head-to-head odds. Options: `--regions us|uk|eu|au`, `--markets h2h,totals`, `--odds-format decimal|american`, `--api-key KEY`. **Requires a free key** from https://the-odds-api.com via `CLI_WEB_WORLDCUP_ODDS_API_KEY` or `--api-key`.

## Examples

```bash
# Mexico's matches, as JSON
cli-web-worldcup fixtures list --team MEX --json

# Group A table
cli-web-worldcup standings list --group A

# Mexico's 26-player squad
cli-web-worldcup players roster Mexico --json

# Today's matches (tournament opens 2026-06-11)
cli-web-worldcup fixtures list --dates 20260611

# Odds (after setting a key)
export CLI_WEB_WORLDCUP_ODDS_API_KEY=...; cli-web-worldcup odds list --json
```

## JSON output

Add `--json` for `{"success": true, "data": [...]}`, or `--jsonl` on list
commands for one compact object per line. Errors are structured too:
`{"error": true, "code": "NOT_FOUND", "message": "..."}`.

Exit codes: `0` ok · `2` usage · `3` auth (missing/invalid odds key) ·
`4` not-found (unknown team/match) · `5` rate-limit · `6` server · `7` network.

## Utilities

`cli-web-worldcup doctor [--json]` diagnoses local setup. `cli-web-worldcup
mcp-serve` exposes the commands as MCP tools over stdio. Running with no
arguments opens an interactive REPL.

## Agent tips

- Resolve teams by 3-letter code (`MEX`, `BRA`, `ARG`) — most reliable; names work too but ambiguous prefixes (e.g. "South") error with the candidates.
- `odds` is the only command needing a key; everything else is keyless. Composes with the `world-cup-2026-predictor` skill for richer forecasts.
- Match `id` for `fixtures get` comes from `fixtures list` (the `id` field).
