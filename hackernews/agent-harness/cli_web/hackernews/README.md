# cli-web-hackernews

CLI for browsing and interacting with Hacker News — top stories, search, comments, user profiles, plus auth-enabled actions (upvote, submit, comment, favorite).

## Installation

```bash
cd hackernews/agent-harness
pip install -e .
```

## Usage

### Browse (no auth required)

```bash
# Browse stories
cli-web-hackernews stories top              # Front page (top 30)
cli-web-hackernews stories new -n 10        # Newest 10 stories
cli-web-hackernews stories best             # Best stories (all time)
cli-web-hackernews stories ask              # Ask HN
cli-web-hackernews stories show             # Show HN
cli-web-hackernews stories jobs             # Job listings

# View a story with comments
cli-web-hackernews stories view 47530330
cli-web-hackernews stories view 47530330 -n 5 --json

# Search
cli-web-hackernews search stories "claude code"
cli-web-hackernews search comments "react hooks" --sort-date -n 5

# User profiles
cli-web-hackernews user view dang
cli-web-hackernews user view pg --json
```

### Auth-Enabled Actions

```bash
# Login
cli-web-hackernews auth login               # Username/password prompt
cli-web-hackernews auth login-browser       # Login via browser window
cli-web-hackernews auth status              # Check login status
cli-web-hackernews auth logout              # Remove credentials

# Interact (requires login)
cli-web-hackernews upvote 47530330          # Upvote a story
cli-web-hackernews submit -t "My Title" -u "https://example.com"  # Submit link
cli-web-hackernews submit -t "Ask HN: Question?" --text "Details" # Ask HN
cli-web-hackernews comment 47530330 "Great article!"              # Comment
cli-web-hackernews favorite 47530330        # Save to favorites
cli-web-hackernews hide 47530330            # Hide from feed

# View your activity
cli-web-hackernews user favorites           # Your favorites
cli-web-hackernews user submissions         # Your submissions
cli-web-hackernews user threads             # Replies to your comments
cli-web-hackernews user submissions dang    # Someone else's submissions
```

### JSON output

Every command supports `--json` for structured output:

```bash
cli-web-hackernews stories top -n 5 --json
cli-web-hackernews upvote 47530330 --json
cli-web-hackernews --json  # Propagates to all commands in REPL mode
```

### REPL mode

Run without arguments to enter interactive mode:

```bash
cli-web-hackernews
```

## API Sources

- **Firebase API**: `hacker-news.firebaseio.com/v0/` — stories, items, users (public)
- **Algolia API**: `hn.algolia.com/api/v1/` — full-text search (public)
- **HN Web**: `news.ycombinator.com` — auth actions (upvote, submit, comment, favorite, hide)

## Testing

```bash
cd hackernews/agent-harness
python -m pytest cli_web/hackernews/tests/ -v -s
```
