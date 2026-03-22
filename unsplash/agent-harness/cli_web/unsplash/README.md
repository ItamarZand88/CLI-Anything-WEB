# cli-web-unsplash

CLI for searching and discovering photos on [Unsplash](https://unsplash.com/).
No API key or authentication required.

## Installation

```bash
cd unsplash/agent-harness
pip install -e .
```

Verify:
```bash
cli-web-unsplash --version
```

## Usage

### Search Photos

```bash
# Basic search
cli-web-unsplash photos search "mountains"

# With filters
cli-web-unsplash photos search "ocean" --orientation landscape --color blue --per-page 10

# JSON output for scripts
cli-web-unsplash photos search "sunset" --json
```

### Photo Details

```bash
# Get full details (EXIF, location, tags)
cli-web-unsplash photos get SyfvrXRy28Y

# Random photos
cli-web-unsplash photos random --query "nature" --count 3

# Photo statistics
cli-web-unsplash photos stats SyfvrXRy28Y
```

### Download Photos

```bash
# Download full resolution
cli-web-unsplash photos download Bkci_8qcdvQ --size full

# Download web-quality to specific path
cli-web-unsplash photos download Bkci_8qcdvQ --size regular -o mountain.jpg

# Available sizes: raw, full, regular, small, thumb
```

### Topics

```bash
cli-web-unsplash topics list
cli-web-unsplash topics get nature
cli-web-unsplash topics photos nature --per-page 10
```

### Collections

```bash
cli-web-unsplash collections search "wallpapers"
cli-web-unsplash collections get 1065976
cli-web-unsplash collections photos 1065976
```

### Users

```bash
cli-web-unsplash users search "landscape"
cli-web-unsplash users get unsplash
cli-web-unsplash users photos unsplash --order-by popular
cli-web-unsplash users collections unsplash
```

### REPL Mode

Run without arguments for interactive mode:

```bash
cli-web-unsplash
```

### JSON Output

All commands support `--json` for structured output:

```bash
cli-web-unsplash photos search "cats" --json | python -c "import json,sys; print(json.load(sys.stdin)['total'])"
```

## Testing

```bash
cd unsplash/agent-harness
python -m pytest cli_web/unsplash/tests/ -v
```

## Dependencies

- Python >= 3.10
- click >= 8.0
- curl_cffi (Chrome TLS impersonation for anti-bot bypass)
- rich >= 13.0
