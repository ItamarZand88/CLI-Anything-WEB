# cli-web-futbin

CLI interface for [FUTBIN](https://www.futbin.com) — EA FC 26 Ultimate Team database.

Search players, check prices, browse SBCs, track market indices, and explore evolutions — all from the command line.

## Installation

```bash
pip install -e .
```

For browser-based login (optional):
```bash
pip install -e '.[browser]'
```

## Usage

### Player Search
```bash
cli-web-futbin players search --query "Messi"
cli-web-futbin --json players search --query "Mbappe"
```

### Player List (with filters)
```bash
cli-web-futbin players list --position ST --sort ps_price --order desc
cli-web-futbin --json players list --page 2 --rating-min 85 --rating-max 90
```

### Price History
```bash
cli-web-futbin players prices --id 21747 --platform ps
cli-web-futbin --json players prices --id 21747
```

### Market Index
```bash
cli-web-futbin market index
cli-web-futbin --json market index --rating 86
```

### SBCs
```bash
cli-web-futbin sbc list
cli-web-futbin sbc cheapest
cli-web-futbin --json sbc list --category Players
```

### Evolutions
```bash
cli-web-futbin evolutions list
cli-web-futbin --json evolutions list --expiring
```

### Popular & Latest
```bash
cli-web-futbin players popular
cli-web-futbin players latest
```

### REPL Mode
```bash
cli-web-futbin   # launches interactive REPL
```

## Auth (optional)

Most features work without login. Auth is only needed for comments, voting, and saved content.

```bash
cli-web-futbin auth login                    # Playwright browser login
cli-web-futbin auth login --from-chrome      # Extract from Chrome debug session
cli-web-futbin auth login --cookies-json cookies.json  # Import from file
cli-web-futbin auth status                   # Check auth status
cli-web-futbin auth logout                   # Clear stored cookies
```

## JSON Output

Add `--json` before any command for structured JSON output:
```bash
cli-web-futbin --json players search --query "Ronaldo"
```

## Testing

```bash
python -m pytest cli_web/futbin/tests/ -v
```
