# LINKEDIN.md — API Map for cli-web-linkedin

> Traffic source: raw-traffic.json captured 2026-04-07 via playwright-cli
> Site: https://www.linkedin.com
> Protocol: Hybrid — Voyager REST API + GraphQL
> Auth: Cookie-based (li_at + JSESSIONID CSRF), browser login via Playwright

## Site Profile

- **Type**: Auth + CRUD
- **Framework**: Custom SPA (React/Como, Voyager web platform)
- **Protection**: PerimeterX + reCAPTCHA enterprise
- **HTTP Client**: curl_cffi with Chrome impersonation

## API Bases

- **GraphQL**: `GET https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(...)`
- **REST**: `GET/POST https://www.linkedin.com/voyager/api/<service>`

### Required Headers
- `csrf-token`: derived from JSESSIONID cookie (format: `ajax:<value>`)
- `x-restli-protocol-version`: `2.0.0`
- `Accept`: `application/graphql` (for GraphQL endpoints)

### Auth
- Cookie: `li_at` (session), `JSESSIONID` (CSRF source)
- Stored at `~/.config/cli-web-linkedin/auth.json`
- Env var: `CLI_WEB_LINKEDIN_AUTH_JSON`

## Endpoint Inventory

### Feed (GraphQL)
- **queryId**: `voyagerFeedDashMainFeed.923020905727c01516495a0ac90bb475`
- **variables**: `(start:N,count:N,sortOrder:MEMBER_SETTING)`

### Profile (GraphQL)
- **queryId**: `voyagerIdentityDashProfiles.b5c27c04968c409fc0ed3546575b9b7a`
- **variables**: `(memberIdentity:<username>)`

### Profile Me (REST)
- **Endpoint**: `GET /voyager/api/me`

### Company (GraphQL)
- **queryId**: `voyagerOrganizationDashCompanies.148b1aebfadd0a455f32806df656c3c1`
- **variables**: `(universalName:<name>)`

### Jobs Search (REST)
- **Endpoint**: `GET /voyager/api/voyagerJobsDashJobCards`
- **Params**: `decorationId=...JobSearchCardsCollection-220`, `q=jobSearch`, `query=(keywords:<q>)`
- **Response**: `elements[].jobCardUnion.jobPostingCard` with title, company, location

### People/Company/Post Search (Headless Browser)
- LinkedIn moved search to RSC (React Server Components)
- Uses headless Playwright to render page and extract from DOM
- Injects cookies from auth.json into browser context

### Write Operations (REST)
- **React**: `POST /voyager/api/reactions` with entity URN + reaction type
- **Unreact**: `DELETE /voyager/api/reactions` with entity URN
- **Post create**: `POST /voyager/api/feed/dash/posts` with commentary text
- **Post edit**: `PUT /voyager/api/feed/dash/posts/{postUrn}` with updated commentary
- **Post delete**: `DELETE /voyager/api/feed/dash/posts/{postUrn}`
- **Comment create**: `POST /voyager/api/feed/dash/comments` with entity URN + text
- **Comment edit**: `PUT /voyager/api/feed/dash/comments/{commentUrn}` with updated text
- **Comment delete**: `DELETE /voyager/api/feed/dash/comments/{commentUrn}`
- **Follow**: `POST /voyager/api/feed/dash/followingStates` with entity URN
- **Unfollow**: `DELETE /voyager/api/feed/dash/followingStates` with entity URN

### Notifications (GraphQL)
- **queryId**: `voyagerNotificationsDashNotificationCard.*`
- **variables**: `(start:0,count:N)`

### Network — Connections (GraphQL)
- **queryId**: `voyagerRelationshipsDashConnections.*`
- **variables**: `(start:0,count:N)`

### Network — Invitations (REST)
- **Endpoint**: `GET /voyager/api/relationships/dash/invitations`
- **Params**: `q=received`

### Network — Connect (REST)
- **Endpoint**: `POST /voyager/api/relationships/dash/invitations`
- **Body**: profile URN + optional message

### Messaging — List Conversations (GraphQL)
- **queryId**: `voyagerMessagingDashConversations.*`
- **variables**: `(start:0,count:N)`

### Messaging — Send Message (REST)
- **Endpoint**: `POST /voyager/api/messaging/dash/createMessage`
- **Body**: conversation URN + message body text

## CLI Command Structure (24 commands, 10 groups)

```
cli-web-linkedin
├── auth login/status/logout     # Browser login, cookie management
├── feed [--count N]             # View feed posts
├── profile get <username>       # View user profile
├── profile me                   # View own profile
├── company <name>               # View company page
├── jobs search <query>          # Search jobs (REST)
├── jobs get <id>                # View job details
├── search all <query>           # Unified search
├── search people <query>        # Search people (headless browser)
├── search companies <query>     # Search companies (headless browser)
├── search posts <query>         # Search posts (headless browser)
├── post create <text>           # Publish a post
├── post edit <urn> <text>       # Edit a post
├── post delete <urn>            # Delete a post
├── post react <urn> [--type]    # React to a post
├── post unreact <urn>           # Remove reaction from a post
├── post comment <urn> <text>    # Comment on a post
├── post edit-comment <urn> <t>  # Edit a comment
├── post delete-comment <urn>    # Delete a comment
├── notifications [--limit N]    # View notifications
├── network connections          # List connections
├── network invitations          # View pending invitations
├── network connect <urn> [-m]   # Send connection request
├── messaging list               # List conversations
└── messaging send <urn> <text>  # Send a message
```

## Notes

- GraphQL queryId hashes may rotate — feed/profile/company stable as of 2026-04-07
- LinkedIn variables use custom serialization `(key:value)`, NOT JSON
- URL params must NOT be URL-encoded (parentheses must be literal)
- People/company/post search requires Playwright (headless browser rendering)
- PerimeterX protection requires curl_cffi Chrome TLS impersonation
