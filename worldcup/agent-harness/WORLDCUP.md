# cli-web-worldcup — API Map

FIFA World Cup 2026 data from two read-only upstreams. No betting actions
are performed anywhere; everything is read-only data retrieval.

## ESPN (no auth)

Base: `https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world`
(`fifa.world` is the men's FIFA World Cup league slug; season 2026 is live.)

| Purpose | Method | Endpoint | Notes |
|---------|--------|----------|-------|
| Fixtures | GET | `/scoreboard?dates=YYYYMMDD-YYYYMMDD` | `dates` defaults to one day; pass a range for the full tournament (`20260611-20260719`). Returns `events[]` → `competitions[0]` → `competitors[]` (home/away, team, score), `status.type.description`, `venue`, `notes` (group/round), `odds[]` (embedded single-provider line, may be `[null]` for knockout placeholders). |
| Match detail | GET | `/summary?event=<id>` | Lineups, multi-provider `pickcenter` odds, head-to-head. |
| Teams | GET | `/teams` | `sports[0].leagues[0].teams[]` → 48 nations (`id`, `displayName`, `abbreviation`, `logos`, `color`). |
| Team | GET | `/teams/<id>` | Single nation detail. |
| Roster | GET | `/teams/<id>/roster` | `athletes[]` (flat list) → `fullName`, `jersey`, `position.abbreviation`, `age`, `citizenship`; plus `coach`. |

Group standings: `https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings`
→ `children[]` (12 groups A–L) → `standings.entries[]` → `team` + `stats[]`
(by name: `gamesPlayed`, `wins`, `ties`, `losses`, `pointsFor`,
`pointsAgainst`, `pointDifferential`, `points`, `rank`).

All ESPN endpoints are plain JSON, no auth, no anti-bot — a normal
User-Agent is sufficient.

## The Odds API (free API key)

Base: `https://api.the-odds-api.com/v4` · key site: <https://the-odds-api.com>

| Purpose | Method | Endpoint | Notes |
|---------|--------|----------|-------|
| Odds | GET | `/sports/soccer_fifa_world_cup/odds?apiKey=KEY&regions=us&markets=h2h&oddsFormat=decimal` | Array of events → `home_team`, `away_team`, `commence_time`, `bookmakers[]` → `markets[]` (`h2h`) → `outcomes[]` (`name`, `price`). |

The key is a query parameter, not a login/session — so this CLI is
**no-auth** at the core; only `odds` needs a key (env
`CLI_WEB_WORLDCUP_ODDS_API_KEY` or `--api-key`). A 401 `INVALID_KEY` maps to
`AuthError` (exit 3); a missing key raises the same before any request.

## Exit codes

`0` ok · `2` usage · `3` auth (missing/invalid odds key) · `4` not-found
(unknown team/match) · `5` rate-limit · `6` server · `7` network.
