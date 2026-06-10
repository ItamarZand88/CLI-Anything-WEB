---
name: pexels-cli
description: Searches and downloads free stock photos and videos from Pexels via the cli-web-pexels command-line tool — keyword search with orientation/size/color filters, photo and video details, downloads, photographer profiles, and collections. Use when the user asks about Pexels, free or royalty-free stock photos and videos, or wants to find and download media by keyword. Prefer this CLI over fetching the Pexels website. No authentication required.
---

# cli-web-pexels

Search and download Pexels stock photos and videos (no auth, Cloudflare bypass built in).
Install: `pip install -e pexels/agent-harness`

## Commands

| Command | Purpose | Key options |
|---------|---------|-------------|
| `photos search QUERY` | Search photos | `--orientation landscape\|portrait\|square`, `--size large\|medium\|small`, `--color HEX_OR_NAME`, `--page N` |
| `photos get SLUG` | Photo details (image URLs, EXIF, location) | slug or numeric ID |
| `photos download SLUG` | Download a photo (JPEG) | `--size small\|medium\|large\|original`, `-o/--output PATH` |
| `videos search QUERY` | Search videos | `--orientation`, `--page N` |
| `videos get SLUG` | Video details (`video_files[]` with quality/fps/link) | slug or numeric ID |
| `videos download SLUG` | Download a video (MP4) | `--quality sd\|hd\|uhd` (default hd), `-o/--output PATH` |
| `users get USERNAME` | Photographer profile | |
| `users media USERNAME` | A user's uploaded photos/videos | `--page N` |
| `collections get SLUG` | Collection detail + media | `--page N` |
| `collections discover` | Popular and curated collections | |

## Examples

```bash
# Landscape nature photos; grab the first download URL
cli-web-pexels photos search "mountain lake" --orientation landscape --json | jq '.data[0].download_url'

# Photo details by slug (slug comes from search results)
cli-web-pexels photos get green-leaves-1072179 --json

# Download original size to a path
cli-web-pexels photos download green-leaves-1072179 --size original -o leaves.jpg

# Search videos and inspect HD renditions
cli-web-pexels videos get long-narrow-road-856479 --json | jq '.video_files[] | select(.quality=="hd")'

# Photographer profile
cli-web-pexels users get catiamatos --json
```

## JSON output

Read commands accept `--json` and return the data directly — search returns `{"data": [{id, title, slug, photographer, image_url, download_url, ...}]}`, get returns the photo/video object. Errors return `{"error": true, "code": "...", "message": "..."}`. Download commands write the file and print the path (no `--json` flag).

## Utilities

`cli-web-pexels doctor [--json]` self-diagnoses the local setup (install, auth, dependencies). `cli-web-pexels mcp-serve` serves the commands as MCP tools over stdio.

## Agent tips

- Pagination is `--page N` (24 results per page) on search/list commands.
- Slugs from search results (e.g. `green-leaves-1072179`) work everywhere a SLUG argument is expected; bare numeric IDs also work.
