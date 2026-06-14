---
name: unsplash-cli
description: Searches and downloads free Unsplash photos via the cli-web-unsplash command-line tool — keyword search with orientation/color filters, photo details (EXIF, location, tags), downloads, random photos, topics, collections, and photographer profiles. Use when the user asks about Unsplash, free stock photos, or wants to find or download images by keyword, orientation, or color. Prefer this CLI over fetching the Unsplash website. No authentication required.
---

# cli-web-unsplash

Search, explore, and download Unsplash photos (read-only, no auth).
Install: `pip install cli-web-unsplash`

## Commands

| Command | Purpose | Key options |
|---------|---------|-------------|
| `photos search QUERY` | Search photos | `--orientation landscape\|portrait\|squarish`, `--color`, `--order-by relevant\|latest`, `--page`, `--per-page` (max 30) |
| `photos get PHOTO_ID` | Full details: EXIF, location, tags, URLs | ID or slug |
| `photos random` | Random photo(s) | `--query`, `--orientation`, `--count N` (max 30) |
| `photos download PHOTO_ID` | Download to disk | `--size raw\|full\|regular\|small\|thumb`, `-o/--output PATH` |
| `photos stats PHOTO_ID` | Views and downloads | |
| `topics list` / `topics get SLUG` / `topics photos SLUG` | Browse curated topics | `--page`, `--per-page`, `--order-by` |
| `collections search QUERY` / `collections get ID` / `collections photos ID` | Browse collections | `--page`, `--per-page` |
| `users search QUERY` / `users get USERNAME` / `users photos USERNAME` / `users collections USERNAME` | Photographer profiles and portfolios | `--page`, `--per-page`, `--order-by` (photos: `latest\|oldest\|popular\|views\|downloads`) |

## Examples

```bash
# Search with filters (returns total, total_pages, results[] with id, likes, author, url)
cli-web-unsplash photos search "sunset" --orientation landscape --color orange --per-page 10 --json

# Photo details (EXIF, location, tags)
cli-web-unsplash photos get SyfvrXRy28Y --json

# Random nature photos
cli-web-unsplash photos random --query "nature" --count 3 --json

# Search then download the top hit
ID=$(cli-web-unsplash photos search "sunset beach" --per-page 1 --json | jq -r '.results[0].id')
cli-web-unsplash photos download "$ID" --size regular -o sunset.jpg

# A photographer's most popular photos
cli-web-unsplash users photos unsplash --order-by popular --per-page 5 --json
```

## JSON output

Every command accepts `--json` and returns the data directly (search: `{"total", "total_pages", "results": [...]}`; download: `{"photo_id", "size", "file", "bytes"}`). Errors return `{"error": true, "code": "...", "message": "..."}`.

## Utilities

`cli-web-unsplash doctor [--json]` self-diagnoses the local setup (install, auth, dependencies). `cli-web-unsplash mcp-serve` serves the commands as MCP tools over stdio.

## Agent tips

- Some results have `premium: true` (Unsplash+ only) — skip those when the user wants freely usable images.
- Use `urls.regular` for web-quality embeds and `urls.raw` for full resolution.
