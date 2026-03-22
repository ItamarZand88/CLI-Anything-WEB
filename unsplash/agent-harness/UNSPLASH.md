# UNSPLASH.md — Software-Specific SOP

## Site Profile

- **URL**: https://unsplash.com/
- **Type**: No-auth + read-only
- **Framework**: React SPA (custom, not Next.js/Nuxt)
- **Protocol**: REST JSON via internal `/napi/` endpoints
- **Auth**: None required for read operations (downloads require login)
- **Protections**: Anti-bot challenge (added ~March 2026) — requires `curl_cffi` with Chrome TLS impersonation
- **Rate Limits**: Headers present (`x-ratelimit-limit: 99999999`) — generous limits
- **HTTP Client**: `curl_cffi` with `impersonate="chrome131"` — plain httpx gets 401 "Making sure you're not a bot!"

## API Base

```
Base URL: https://unsplash.com
Internal API prefix: /napi/
Autocomplete prefix: /nautocomplete/
Image CDN: images.unsplash.com
```

All endpoints return JSON. Uses `curl_cffi` with Chrome TLS fingerprint impersonation
to bypass anti-bot protection. Plain `httpx` or `requests` will receive a 401 challenge page.

## Data Model

### Photo
- `id` (string) — short alphanumeric ID (e.g., "SyfvrXRy28Y")
- `slug` (string) — SEO slug with ID suffix (e.g., "a-mountain-range-...-SyfvrXRy28Y")
- `width`, `height` (int) — original dimensions
- `color` (string) — dominant color hex
- `description`, `alt_description` (string|null)
- `likes` (int), `views` (int), `downloads` (int)
- `created_at`, `updated_at` (ISO datetime)
- `urls` — `{raw, full, regular, small, thumb, small_s3}`
- `user` — nested User object
- `exif` — camera metadata `{make, model, exposure_time, aperture, focal_length, iso}`
- `location` — `{name, city, country, position: {latitude, longitude}}`
- `tags` — list of `{title, type}`
- `topics` — list of topic objects
- `premium` (bool), `plus` (bool) — Unsplash+ indicators

### User
- `id` (string)
- `username` (string) — unique handle
- `name` (string) — display name
- `bio` (string|null)
- `location` (string|null)
- `portfolio_url` (string|null)
- `total_photos`, `total_likes`, `total_collections` (int)
- `profile_image` — `{small, medium, large}`

### Collection
- `id` (int)
- `title` (string)
- `description` (string|null)
- `total_photos` (int)
- `cover_photo` — nested Photo object
- `user` — nested User object

### Topic
- `id` (string)
- `slug` (string)
- `title` (string)
- `description` (string|null)
- `total_photos` (int)
- `featured` (bool)

## API Endpoints

### Search
| Method | Endpoint | Description | Params |
|--------|----------|-------------|--------|
| GET | `/napi/search/photos` | Search photos | `query`, `page`, `per_page`, `orientation`, `color`, `order_by` |
| GET | `/napi/search/collections` | Search collections | `query`, `page`, `per_page` |
| GET | `/napi/search/users` | Search users | `query`, `page`, `per_page` |
| GET | `/nautocomplete/{query}` | Autocomplete suggestions | — |

### Photos
| Method | Endpoint | Description | Params |
|--------|----------|-------------|--------|
| GET | `/napi/photos/{id_or_slug}` | Photo details | — |
| GET | `/napi/photos/{id}/related` | Related photos | — |
| GET | `/napi/photos/{id}/statistics` | Photo stats (views, downloads) | — |
| GET | `/napi/photos/random` | Random photo(s) | `count`, `query`, `topics`, `orientation` |

### Topics
| Method | Endpoint | Description | Params |
|--------|----------|-------------|--------|
| GET | `/napi/topics` | List topics | `page`, `per_page`, `order_by` |
| GET | `/napi/topics/{slug}` | Topic details | — |
| GET | `/napi/topics/{slug}/photos` | Photos in topic | `page`, `per_page`, `order_by` |

### Collections
| Method | Endpoint | Description | Params |
|--------|----------|-------------|--------|
| GET | `/napi/collections/{id}` | Collection details | — |
| GET | `/napi/collections/{id}/photos` | Photos in collection | `page`, `per_page` |

### Users
| Method | Endpoint | Description | Params |
|--------|----------|-------------|--------|
| GET | `/napi/users/{username}` | User profile | — |
| GET | `/napi/users/{username}/photos` | User's photos | `page`, `per_page`, `order_by` |
| GET | `/napi/users/{username}/collections` | User's collections | `page`, `per_page` |

## CLI Command Structure

```
cli-web-unsplash
├── photos
│   ├── search <query>     [--orientation] [--color] [--order-by] [--page] [--per-page]
│   ├── get <photo_id>
│   ├── random              [--query] [--orientation] [--count]
│   ├── download <photo_id> [--size raw|full|regular|small|thumb] [-o path]
│   └── stats <photo_id>
├── topics
│   ├── list                [--page] [--per-page]
│   ├── get <slug>
│   └── photos <slug>       [--page] [--per-page] [--order-by]
├── collections
│   ├── search <query>      [--page] [--per-page]
│   ├── get <collection_id>
│   └── photos <collection_id> [--page] [--per-page]
└── users
    ├── search <query>       [--page] [--per-page]
    ├── get <username>
    ├── photos <username>    [--page] [--per-page] [--order-by]
    └── collections <username> [--page] [--per-page]
```

Note: read-only site — no create/update/delete commands.
Download uses public image CDN URLs (no auth required).
No auth module — all endpoints are public.
