# cli-web-futbin

Agent-native CLI for [FUTBIN](https://www.futbin.com/) — EA FC Ultimate Team player database.

Search players, check prices, browse Squad Building Challenges (SBCs), and explore
Player Evolutions — all from the command line or via agent automation.

## Features

- **Player search** — find players by name, filter by price, sort by any field
- **Player prices** — PS and XBOX market prices
- **Market index** — EA FC market price tracker
- **SBCs** — list all Squad Building Challenges with costs and expiry
- **Evolutions** — browse player evolution paths
- **JSON output** — every command supports `--json` for agent consumption
- **REPL mode** — interactive shell (run `cli-web-futbin` with no args)

## Installation

```bash
cd futbin/agent-harness
pip install -e .
```

No authentication required — FUTBIN is a public site.

## Usage

### Player Search

```bash
# Search by name
cli-web-futbin players search --name "Mbappe"

# JSON output for agents
cli-web-futbin players search --name "Mbappe" --json

# Include evolution cards
cli-web-futbin players search --name "Salah" --evolutions

# Older year
cli-web-futbin players search --name "Ronaldo" --year 25
```

### Player Detail

```bash
# Get player by ID (from search results)
cli-web-futbin players get --id 40

# JSON output
cli-web-futbin players get --id 40 --json
```

### Players List (with filters)

```bash
# List top players by price
cli-web-futbin players list --sort ps_price --order desc

# Filter by name
cli-web-futbin players list --name "Vinicius"

# Filter by price range (coins)
cli-web-futbin players list --min-price 50000 --max-price 200000
```

### Market Index

```bash
cli-web-futbin market index
cli-web-futbin market index --json
```

### Squad Building Challenges

```bash
# List all SBCs
cli-web-futbin sbc list

# Filter by category
cli-web-futbin sbc list --category Players

# Get SBC detail
cli-web-futbin sbc get --id 665
```

### Evolutions

```bash
# List all active evolutions
cli-web-futbin evolutions list

# Show only expiring soon
cli-web-futbin evolutions list --expiring

# Get evolution detail
cli-web-futbin evolutions get --id 666
```

### Auth (Optional)

FUTBIN is a public site — auth is not required for any commands.
Optional login enables personal features (My Evolutions, Saved Squads).

```bash
cli-web-futbin auth status
cli-web-futbin auth login    # optional
```

### REPL Mode

```bash
cli-web-futbin
# Enters interactive REPL
# > players search --name Mbappe
# > market index
# > quit
```

## Agent Usage

All commands support `--json` for structured output:

```bash
# Agent: find Mbappe's current price
cli-web-futbin players search --name "Mbappe" --json | jq '.[0] | {name, rating, ps_price, xbox_price}'

# Agent: check market index
cli-web-futbin market index --json

# Agent: list SBCs with costs
cli-web-futbin sbc list --json | jq '.[] | select(.cost_ps != null) | {name, cost_ps}'
```

## Notes

- Prices are in EA FC coins
- Year 26 = EA FC 26 (current), 25 = EA FC 25, etc.
- Rate limiting: 0.5s delay between requests
- HTML scraping is used for most endpoints (SSR site)
- The `/players/search` endpoint returns JSON directly
