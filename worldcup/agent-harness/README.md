# cli-web-worldcup

FIFA World Cup 2026 from the command line — fixtures, nations, squads, group
standings, and bookmaker odds. Read-only; no betting actions. Data comes from
ESPN's public soccer API (no auth) and, for odds, The Odds API (free key).

## Installation

```bash
pip install cli-web-worldcup
```

## Usage

```bash
cli-web-worldcup fixtures list --team MEX          # matches involving Mexico
cli-web-worldcup fixtures list --dates 20260611    # a single day
cli-web-worldcup fixtures get <event_id>           # one match's detail
cli-web-worldcup teams list                        # all 48 nations
cli-web-worldcup teams get MEX                      # one nation (id, code, or name)
cli-web-worldcup players roster Mexico             # a nation's squad
cli-web-worldcup standings list --group A          # group table
cli-web-worldcup odds list --regions us            # bookmaker odds (needs key)
```

## Odds (optional API key)

`odds` uses [The Odds API](https://the-odds-api.com) (free tier). Set the key
once, then odds work like any other command:

```bash
export CLI_WEB_WORLDCUP_ODDS_API_KEY=your_key   # or: odds list --api-key your_key
cli-web-worldcup odds list --json
```

Without a key, `odds` exits `3` with a structured `AUTH_EXPIRED` error. Every
other command works with no key.

## JSON Output

Every command supports `--json` (structured) and list commands also offer
`--jsonl` (one object per line, for `jq`/agents):

```bash
cli-web-worldcup teams list --json
cli-web-worldcup fixtures list --jsonl | jq -r '.name'
```

Errors in `--json` mode are structured too:
`{"error": true, "code": "NOT_FOUND", "message": "..."}`. Exit codes:
`0` ok · `2` usage · `3` auth · `4` not-found · `5` rate-limit · `6` server ·
`7` network.

## REPL Mode

Run without arguments for interactive mode:

```bash
cli-web-worldcup
```

## Testing

```bash
cd worldcup/agent-harness
pip install -e .
CLI_WEB_FORCE_INSTALLED=1 python -m pytest cli_web/worldcup/tests/ -v
```

## Protocol

- **Website:** <https://www.espn.com/soccer/> (FIFA World Cup) + The Odds API
- **Protocol:** REST (JSON)
- **Auth:** none for ESPN data; optional API key for odds
