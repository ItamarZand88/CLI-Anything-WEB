# PRODUCTHUNT.md — Software-Specific SOP

## API Overview

- **Protocol**: Next.js App Router — feed data embedded in the RSC flight stream (`self.__next_f`)
- **HTTP client**: curl_cffi with Chrome TLS impersonation
- **Auth**: None required — public pages
- **Site profile**: No-auth, read-only

## Data Model

| Entity | Key Fields | ID Format |
|--------|-----------|-----------|
| Post | id, name, tagline, slug, url, votes_count, comments_count, topics, thumbnail_url | numeric string |
| User | username, name, headline, links, topics | string (username) |

## HTML Pages → CLI Commands

| Page | CLI Command | Selector Pattern |
|------|------------|-----------------|
| Homepage (`/`) | `posts list` | `.styles_item` cards |
| Leaderboard (`/leaderboard/...`) | `posts leaderboard` | `.styles_item` cards |
| Product page (`/products/<slug>`) | `posts get <slug>` | Meta tags + `.styles_htmlText` |
| User page (`/@<username>`) | `users get <username>` | Profile header + meta |

## CLI Command Structure

```
cli-web-producthunt
├── posts
│   ├── list [--json]                              Today's homepage posts
│   ├── get <slug> [--json]                        Product details by slug
│   └── leaderboard [--period daily|weekly|monthly] [--json]
└── users
    └── get <username> [--json]                    User profile
```

## Notes

- No auth needed — all data is publicly accessible
- curl_cffi impersonates Chrome for transport
- Posts are parsed from the embedded Next.js RSC flight stream (`self.__next_f`), not DOM cards
- Leaderboard supports daily/weekly/monthly periods
