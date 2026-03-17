# SUNO.md — Software-Specific SOP

## Overview

Suno is an AI music generation platform. Users create songs from text prompts (lyrics + style tags),
manage their library of generated clips, organize them into projects, and explore trending content.

---

## API Surface

**Base URL:** `https://studio-api.prod.suno.com`
**Auth:** Clerk JWT via `auth.suno.com` — Bearer token in `Authorization` header
**Additional headers required:**
- `browser-token`: JSON object `{"token":"eyJ..."}` (base64-encoded timestamp)
- `device-id`: UUID (persistent per device)
- `origin`: `https://suno.com`

### Auth Flow (Clerk)

1. Clerk client at `auth.suno.com/v1/client` returns session with JWT
2. JWT is short-lived (~1h), auto-refreshed by Clerk JS SDK
3. For CLI: extract cookies from Chrome debug profile via CDP, then call Clerk's
   `/v1/client` endpoint with `__session` cookie to get JWT
4. JWT claims include `suno.com/claims/user_id` and `suno.com/claims/email`

### Endpoints

#### Session & User
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/session/` | Full session: user info, models, roles, flags, configs |
| GET | `/api/user/get_user_session_id/` | Get session ID |
| GET | `/api/user/tos_acceptance` | TOS acceptance status |
| POST | `/api/user/user_config/` | Update user config |
| GET | `/api/profiles/{handle}/info` | Profile info |
| GET | `/api/profiles/pinned-clips` | User's pinned clips |

**Session response structure:**
```json
{
  "user": {"email", "username", "id", "clerk_id", "display_name", "handle", "avatar_image_url"},
  "models": [{"name", "external_key", "major_version", "capabilities", "features", "can_use"}],
  "roles": {"sub": bool, "pro": bool},
  "flags": {"v5-web-ui": bool, "studio": bool, ...},
  "configs": {"gen-endpoint": {"endpoint": "/api/generate/v2-web/"}}
}
```

#### Song Generation
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/generate/v2-web/` | Generate songs from prompt |
| GET | `/api/generate/concurrent-status` | Check running/max concurrent jobs |

**Generate request body (inferred from UI):**
```json
{
  "gpt_description_prompt": "a happy pop song about summer",
  "prompt": "[verse]\nLyrics here...",
  "tags": "pop, happy, summer",
  "negative_tags": "",
  "title": "Summer Vibes",
  "make_instrumental": false,
  "model": "chirp-auk-turbo",
  "project_id": "default"
}
```

**Generate response:** Array of clip objects with status "submitted" → poll until "complete"

#### Songs / Clips (Feed)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/feed/v3` | List user's songs (paginated, filtered) |
| POST | `/api/unified/homepage` | Homepage feed with trending content |
| GET | `/api/playlist/{id}?page=0` | Get playlist |

**Feed v3 request:**
```json
{
  "cursor": null,
  "limit": 20,
  "filters": {
    "disliked": "False",
    "trashed": "False",
    "fromStudioProject": {"presence": "False"},
    "stem": {"presence": "False"},
    "workspace": {"presence": "True", "workspaceId": "default"}
  }
}
```

**Clip object structure:**
```json
{
  "id": "uuid",
  "status": "complete",
  "title": "Song Title",
  "play_count": 5,
  "upvote_count": 1,
  "audio_url": "https://cdn1.suno.ai/{id}.mp3",
  "image_url": "https://cdn2.suno.ai/image_{id}.jpeg",
  "video_url": "",
  "major_model_version": "v4.5-all",
  "model_name": "chirp-auk",
  "metadata": {
    "tags": "genre/style tags",
    "prompt": "lyrics with [verse]/[chorus] markers",
    "gpt_description_prompt": "original text prompt",
    "duration": 64.92,
    "has_vocal": true,
    "task": "generate|cover|extend"
  },
  "is_liked": false,
  "is_trashed": false,
  "is_public": false,
  "created_at": "2026-03-09T13:19:42.432Z",
  "user_id": "uuid",
  "display_name": "User Name",
  "handle": "username"
}
```

#### Projects
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/project/me?page=1&sort=...&show_trashed=false` | List user's projects |
| GET | `/api/project/default` | Default project with clips |
| GET | `/api/project/{id}/pinned-clips` | Pinned clips in project |

**Project object:**
```json
{
  "id": "default",
  "name": "My Workspace",
  "description": "Workspace for unassigned clips",
  "clip_count": 353
}
```

#### Prompts & Tags
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/prompts/` | List saved prompts |
| GET | `/api/prompts/?page=0&per_page=100&filter_prompt_type=lyrics` | Lyrics prompts |
| GET | `/api/prompts/?page=0&per_page=100&filter_prompt_type=tags` | Tag prompts |
| GET | `/api/prompts/suggestions` | Prompt suggestions |
| POST | `/api/tags/recommend` | Get recommended tags |

**Tags recommend request:** `{"tags": []}` or `{"tags": ["pop"]}`
**Tags recommend response:** `{"tags": [], "recommended_tags": ["folk", "dark wave", ...]}`

#### Billing
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/billing/info/` | Credits, plans, subscription status |
| GET | `/api/billing/usage-plans` | Available plans |
| GET | `/api/billing/usage-plan-descriptions/` | Plan descriptions |
| GET | `/api/billing/eligible-discounts` | Eligible discounts |
| GET | `/api/billing/default-currency` | Default currency |

**Billing info response:**
```json
{
  "is_active": false,
  "credits": 70,
  "total_credits_left": 120,
  "subscription_type": false,
  "monthly_usage": 0,
  "monthly_limit": 50,
  "plans": [{"name": "Free Plan"}, {"name": "Pro Plan"}, {"name": "Premier Plan"}]
}
```

#### Notifications
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notification/v2` | List notifications |
| GET | `/api/notification/v2/badge-count` | Unread count |

#### Other
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/contests/` | Active contests |
| GET | `/api/challenge/progress` | Challenge progress |
| GET/POST | `/api/music_player/playbar_state` | Player state |
| POST | `/api/video_gen/pending_batches` | Video generation status |
| GET | `/api/share/stats?content_type=song` | Share statistics |

---

## Data Model

### Entities
- **User** — id (UUID), clerk_id, email, handle, display_name, avatar
- **Clip/Song** — id (UUID), title, status, audio_url, image_url, metadata (tags, prompt, duration)
- **Project** — id (UUID or "default"), name, description, clip_count
- **Prompt** — saved lyrics/tag presets
- **Playlist** — id (UUID), collection of clips

### Relationships
- User has many Clips
- User has many Projects
- Project has many Clips
- User has many Prompts
- Clip belongs to Project (workspace)

---

## CLI Architecture

### Command Groups

```
cli-web-suno
├── auth          # Authentication management
│   ├── login     # Login (Playwright / --from-browser / --cookies-json)
│   ├── status    # Show auth status & credits
│   └── refresh   # Refresh JWT token
├── songs         # Song/clip management
│   ├── list      # List user's songs (feed)
│   ├── get       # Get single song details
│   ├── generate  # Generate new song from prompt
│   ├── status    # Check generation queue status
│   └── download  # Download song audio
├── projects      # Project management
│   ├── list      # List user projects
│   └── get       # Get project with clips
├── explore       # Discover content
│   ├── feed      # Homepage/trending feed
│   └── tags      # Get recommended tags
├── billing       # Billing & credits
│   ├── info      # Show credits, plan, limits
│   └── plans     # List available plans
└── prompts       # Prompt management
    ├── list      # List saved prompts
    └── suggestions # Get prompt suggestions
```

### Auth Strategy
- Primary: Playwright browser login → extract Clerk session cookie → get JWT
- Dev/pipeline: CDP extraction from Chrome debug profile (port 9222)
- Manual: `--cookies-json` import
- Token refresh: Call Clerk `/v1/client` with `__session` cookie to get fresh JWT
- Store: `~/.config/cli-web-suno/auth.json` (chmod 600)

### Required Headers
Every API call needs:
1. `Authorization: Bearer <jwt>`
2. `browser-token: {"token":"<base64_timestamp>"}`
3. `device-id: <uuid>` (generate once, persist in config)
4. `origin: https://suno.com`
5. `user-agent: Mozilla/5.0 ...` (Chrome UA)
