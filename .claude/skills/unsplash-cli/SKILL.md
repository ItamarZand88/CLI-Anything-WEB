---
name: unsplash-cli
description: Use cli-web-unsplash to answer questions about Unsplash photos, search for free images by keyword, download photos, browse photo topics and collections, view photographer profiles, get photo details (EXIF, location, tags), and discover random photos. Invoke this skill whenever the user asks about Unsplash, free stock photos, searching for images, downloading images, photo topics, photographer profiles, photo collections, or wants to find or download images by keyword, orientation, or color. Always prefer cli-web-unsplash over manually fetching the Unsplash website.
---

# cli-web-unsplash

CLI for searching and discovering photos on Unsplash. Installed at: `cli-web-unsplash`.

## Quick Start

```bash
# Search for photos
cli-web-unsplash photos search "mountains" --json

# Get photo details
cli-web-unsplash photos get SyfvrXRy28Y --json

# Browse topics
cli-web-unsplash topics list --json
```

Always use `--json` when parsing output programmatically.

---

## Commands

### `photos search <query>`
Search photos by keyword with optional filters.

```bash
cli-web-unsplash photos search "sunset" --orientation landscape --color orange --per-page 10 --json
```

**Key options:** `--orientation` (landscape/portrait/squarish), `--color`, `--order-by` (relevant/latest), `--page`, `--per-page`
**Output fields:** `total`, `total_pages`, `results[]` with `id`, `description`, `width`, `height`, `likes`, `color`, `author`, `url`, `link`, `premium`

### `photos get <photo_id>`
Get full photo details including EXIF, location, and tags.

```bash
cli-web-unsplash photos get SyfvrXRy28Y --json
```

**Output fields:** `id`, `slug`, `description`, `width`, `height`, `color`, `likes`, `views`, `downloads`, `created_at`, `author` ({username, name}), `urls`, `exif` (camera, aperture, exposure, focal_length, iso), `location` (name, city, country, latitude, longitude), `tags[]`, `premium`, `link`

### `photos random`
Get random photo(s), optionally filtered.

```bash
cli-web-unsplash photos random --query "nature" --count 3 --orientation landscape --json
```

### `photos download <photo_id>`
Download a photo to disk.

```bash
cli-web-unsplash photos download Bkci_8qcdvQ --size full -o mountain.jpg --json
```

**Key options:** `--size` (raw/full/regular/small/thumb, default: full), `--output` / `-o` (file path)
**Output fields (JSON):** `photo_id`, `size`, `file`, `bytes`, `description`

### `photos stats <photo_id>`
Get photo view and download statistics.

```bash
cli-web-unsplash photos stats SyfvrXRy28Y --json
```

### `topics list`
List available photo topics.

```bash
cli-web-unsplash topics list --json
```

### `topics get <slug>`
Get topic details.

```bash
cli-web-unsplash topics get nature --json
```

### `topics photos <slug>`
List photos in a topic.

```bash
cli-web-unsplash topics photos nature --per-page 10 --order-by popular --json
```

### `collections search <query>`
Search photo collections.

```bash
cli-web-unsplash collections search "wallpapers" --json
```

### `collections get <id>`
Get collection details.

```bash
cli-web-unsplash collections get 1065976 --json
```

### `collections photos <id>`
List photos in a collection.

```bash
cli-web-unsplash collections photos 1065976 --per-page 10 --json
```

### `users search <query>`
Search users by name.

```bash
cli-web-unsplash users search "landscape" --json
```

### `users get <username>`
Get user profile.

```bash
cli-web-unsplash users get unsplash --json
```

### `users photos <username>`
List photos by a user.

```bash
cli-web-unsplash users photos unsplash --order-by popular --json
```

### `users collections <username>`
List collections by a user.

```bash
cli-web-unsplash users collections unsplash --json
```

---

## Agent Patterns

```bash
# Find landscape photos of mountains and get the first result's details
cli-web-unsplash photos search "mountains" --orientation landscape --per-page 1 --json | python -c "import json,sys; d=json.load(sys.stdin); print(d['results'][0]['url'])"

# Get a random nature photo URL
cli-web-unsplash photos random --query "nature" --json | python -c "import json,sys; d=json.load(sys.stdin); print(d[0]['url'])"

# Find a photographer's top photos
cli-web-unsplash users photos unsplash --order-by popular --per-page 5 --json

# Search and download the first result
ID=$(cli-web-unsplash photos search "sunset beach" --per-page 1 --json | python -c "import json,sys; print(json.load(sys.stdin)['results'][0]['id'])")
cli-web-unsplash photos download "$ID" --size regular -o sunset.jpg
```

---

## Notes

- Auth: Not required — all endpoints are public
- Rate limiting: Generous limits (x-ratelimit-limit: 99999999)
- Premium photos: Some results have `premium: true` (Unsplash+ only)
- Image URLs: Use `urls.regular` for web-quality, `urls.raw` for full resolution
