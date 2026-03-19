# PRODUCTHUNT.md — Software-Specific SOP

## API Overview

- **Protocol**: GraphQL
- **Endpoint**: `https://api.producthunt.com/v2/api/graphql`
- **Auth**: OAuth client credentials → Bearer token
- **Token endpoint**: `https://api.producthunt.com/v2/oauth/token`
- **Site profile**: API-key auth, read-only for client tokens
- **Website**: Cloudflare-protected (cannot scrape HTML)

## Auth Flow

1. User registers app at https://www.producthunt.com/v2/oauth/applications
2. Gets `client_id` + `client_secret` (or a developer token from API dashboard)
3. CLI stores credentials at `~/.config/cli-web-producthunt/auth.json`

**Client credentials flow:**
```
POST /v2/oauth/token
{"client_id": "...", "client_secret": "...", "grant_type": "client_credentials"}
→ {"access_token": "...", "token_type": "Bearer", "scope": "public"}
```

**Developer token (simpler):**
Non-expiring token from API dashboard. Stored directly.

## Data Model

| Entity | Key Fields | ID Format |
|--------|-----------|-----------|
| Post | id, name, tagline, description, votesCount, commentsCount, url, createdAt | numeric |
| Topic | id, name, slug, description, postsCount | numeric |
| Collection | id, name, description, postsCount, user | numeric |
| User | id, name, username, headline, profileImage, websiteUrl | numeric |
| Comment | id, body, votesCount, createdAt, user | numeric |

## GraphQL Queries → CLI Commands

| Query | CLI Command | Args |
|-------|------------|------|
| `posts(first, topic, order)` | `posts list` | `--topic`, `--sort`, `--limit` |
| `post(slug)` | `posts get <slug>` | positional slug |
| `topics(first, order)` | `topics list` | `--sort`, `--limit` |
| `topic(slug)` | `topics get <slug>` | positional slug |
| `collections(first)` | `collections list` | `--limit` |
| `collection(slug)` | `collections get <slug>` | positional slug |
| `user(username)` | `users get <username>` | positional username |

## Rate Limits

- No documented rate limit numbers
- Fair-use policy — implement exponential backoff on 429

## CLI Command Structure

```
cli-web-producthunt
├── auth
│   ├── login --developer-token <TOKEN>
│   ├── login --client-id <ID> --client-secret <SECRET>
│   ├── status
│   └── logout
├── posts
│   ├── list [--topic <slug>] [--sort newest|votes] [--limit N]
│   └── get <slug>
├── topics
│   ├── list [--sort newest|name] [--limit N]
│   └── get <slug>
├── collections
│   ├── list [--limit N]
│   └── get <slug>
├── users
│   └── get <username>
└── search <query> [--type posts|users] [--limit N]
```
