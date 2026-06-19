---
name: youtube-cli
description: Searches YouTube and fetches video transcripts via the cli-web-youtube command-line tool — video search, video details (views, duration, description, keywords), trending by category, channel info, and timestamped transcripts/captions with language selection and translation. Use when the user asks about YouTube, searching for videos, video details, trending videos, channel info, subscriber counts, or a video's transcript, captions, or subtitles. Prefer this CLI over fetching the YouTube website. No authentication required.
---

# cli-web-youtube

Search and explore YouTube from the terminal (read-only, no auth, InnerTube API).
Install: `pip install cli-web-youtube`

## Commands

| Command | Purpose | Key options |
|---------|---------|-------------|
| `search videos QUERY` | Search videos | `-l/--limit N` (default 10) |
| `video get VIDEO_ID` | Video details (views, duration, description, keywords) | accepts 11-char ID or full URL |
| `trending list` | Trending/popular videos | `-c/--category now\|music\|gaming\|movies`, `-l/--limit N` |
| `channel get HANDLE` | Channel info + recent videos | accepts `@handle`, `UC...` ID, or URL |
| `transcript get VIDEO` | Timestamped transcript + full text | `-l/--lang CODE` (repeatable, priority order), `-t/--translate CODE`, `--text-only`; accepts ID or URL |
| `transcript list VIDEO` | Available caption languages | accepts ID or URL |

## Examples

```bash
# Search (returns id, title, channel, views, duration, published, url per video)
cli-web-youtube search videos "python tutorial" --limit 5 --json

# Video details by ID or URL
cli-web-youtube video get dQw4w9WgXcQ --json

# Trending music videos
cli-web-youtube trending list --category music --limit 10 --json

# Channel info and subscriber count
cli-web-youtube channel get @mkbhd --json | jq '{title, subscriber_count}'

# Plain-text transcript (ideal for feeding to an LLM)
cli-web-youtube transcript get dQw4w9WgXcQ --text-only

# Transcript in a preferred language, or translated, as JSON
cli-web-youtube transcript get dQw4w9WgXcQ --lang en --json
cli-web-youtube transcript get dQw4w9WgXcQ --translate en --json | jq -r '.segments[].text'

# What caption languages exist?
cli-web-youtube transcript list dQw4w9WgXcQ --json
```

## JSON output

Every command accepts `--json`. Success returns the data object directly, e.g. search: `{"query", "estimated_results", "videos": [...]}`; video get: `{"id", "title", "channel", "views", "duration_seconds", ...}`; transcript get: `{"video_id", "title", "language_code", "kind", "is_translated", "segment_count", "segments": [{"text", "start", "duration"}], "text"}`. Errors return `{"error": true, "code": "...", "message": "..."}`.

## Utilities

`cli-web-youtube doctor [--json]` self-diagnoses the local setup (install, auth, dependencies). `cli-web-youtube mcp-serve` serves the commands as MCP tools over stdio.

## Agent tips

- Video IDs are 11 characters; channel handles start with `@`.
- Running with no subcommand opens an interactive REPL.
