# cli-web-pexels

CLI for [Pexels](https://www.pexels.com/) — free stock photos and videos from the command line.

## Installation

```bash
pip install cli-web-pexels
```

## Usage

### Search Photos

```bash
cli-web-pexels photos search "nature"
cli-web-pexels photos search "sunset" --orientation landscape --size large --json
```

### Get Photo Details

```bash
cli-web-pexels photos get green-leaves-1072179
cli-web-pexels photos get green-leaves-1072179 --json
```

### Download Photos

```bash
cli-web-pexels photos download green-leaves-1072179
cli-web-pexels photos download green-leaves-1072179 --size large --output photo.jpg
```

### Search Videos

```bash
cli-web-pexels videos search "ocean"
cli-web-pexels videos search "nature" --orientation landscape --json
```

### Download Videos

```bash
cli-web-pexels videos download long-narrow-road-856479 --quality hd
```

### User Profiles

```bash
cli-web-pexels users get pixabay
cli-web-pexels users media pixabay --json
```

### Collections

```bash
cli-web-pexels collections discover
cli-web-pexels collections get spring-aesthetic-fvku5ng --json
```

### REPL Mode

```bash
cli-web-pexels        # enters interactive REPL
cli-web-pexels --json # REPL with JSON output
```

## Search Filters

| Filter | Options | Example |
|--------|---------|---------|
| `--orientation` | landscape, portrait, square | `--orientation landscape` |
| `--size` | large, medium, small | `--size large` |
| `--color` | hex or named color | `--color orange` |
| `--page` | page number (1-based) | `--page 2` |

## Running Tests

```bash
cd pexels/agent-harness
python -m pytest cli_web/pexels/tests/ -v
```
