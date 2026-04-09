# LINKEDIN.md — API Map for cli-web-linkedin

> Traffic source: raw-traffic.json captured 2026-04-07 via playwright-cli
> Site: https://www.linkedin.com
> Protocol: Hybrid — Voyager REST API + GraphQL
> Auth: Cookie-based (li_at + JSESSIONID CSRF), browser login via Playwright

## Site Profile

- **Type**: Auth + CRUD
- **Framework**: Custom SPA (React/Como, Voyager web platform)
- **Protection**: PerimeterX (HUMAN Security) + reCAPTCHA enterprise
- **HTTP Client**: curl_cffi with Chrome impersonation (TLS/UA match)

## API Bases

- **GraphQL**: `GET https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(...)`
- **REST**: `GET/POST/PUT/DELETE https://www.linkedin.com/voyager/api/<service>`
- **Messaging GraphQL**: `GET https://www.linkedin.com/voyager/api/voyagerMessagingGraphQL/graphql`

### Required Headers

- `csrf-token`: derived from JSESSIONID cookie (format: `ajax:<value>`)
- `x-restli-protocol-version`: `2.0.0`
- `x-li-track`: JSON client version payload
- `x-li-lang`: `en_US`
- `accept-language`: `en-US,en;q=0.9`
- `Accept`: `application/vnd.linkedin.normalized+json+2.1` (per-request)

### Auth

- Cookies: `li_at` (session), `JSESSIONID` (CSRF source)
- Stored at `~/.config/cli-web-linkedin/auth.json`
- Env var: `CLI_WEB_LINKEDIN_AUTH_JSON`
- Browser login via Python `sync_playwright()` with persistent context

### REST.li Pointer Pattern

LinkedIn responses use REST.li pointer format: `*field` keys reference objects
in the `included` array by `entityUrn`. All response parsers must resolve these
pointers to get display data.

## Endpoint Inventory

### Feed (GraphQL)

- **queryId**: `voyagerFeedDashMainFeed.923020905727c01516495a0ac90bb475`
- **variables**: `(start:N,count:N,sortOrder:MEMBER_SETTING)`
- **Response**: `data.data.feedDashMainFeedByMainFeed.*elements[]` → resolve from `included`
- **Social counts**: In `included` array, keyed by `urn:li:activity:*` (the `urn` field, not `entityUrn`)

### Profile (REST)

- **Endpoint**: `GET /voyager/api/identity/dash/profiles`
- **Params**: `q=memberIdentity`, `memberIdentity=<username>`, `decorationId=...FullProfileWithEntities-93`
- **Response**: Profile data in `included[0]` (firstName, lastName, headline, etc.)

### Profile Me (REST)

- **Endpoint**: `GET /voyager/api/me`
- **Response**: `included[0]` contains miniProfile (firstName, lastName, occupation, publicIdentifier)

### Search — People, Companies (GraphQL)

- **queryId**: `voyagerSearchDashClusters.b0928897b71bd00a5a7291755dcd64f0`
- **variables**: `(start:N,origin:GLOBAL_SEARCH_HEADER,query:(keywords:<q>,flagshipSearchIntent:SEARCH_SRP,queryParameters:List((key:resultType,value:List(PEOPLE|COMPANIES))),includeFiltersInResponse:false))`
- **Response**: `data.data.searchDashClustersByAll.elements[].items[].item.*entityResult` → resolve EntityResultViewModel from `included` (has title.text, primarySubtitle.text, secondarySubtitle.text)

### Jobs Search (REST)

- **Endpoint**: `GET /voyager/api/voyagerJobsDashJobCards`
- **Params**: `decorationId=...JobSearchCardsCollection-220`, `q=jobSearch`, `query=(keywords:<q>)`
- **Response**: `data.elements[].jobCardUnion.*jobPostingCard` → resolve from `included`

### Job Detail (REST)

- **Endpoint**: `GET /voyager/api/voyagerJobsDashJobPostings/{urn:li:fsd_jobPosting:ID}`
- **Response**: `data.title`, `data.description`, `data.formattedLocation` (flat, no pointer resolution needed)

### Company (via Search)

- Uses the search endpoint with `COMPANIES` vertical and `count=1`
- Returns name, industry, follower count from EntityResultViewModel

### Write Operations (REST)

- **React**: `POST /voyager/api/reactions` — body: `{reactionType, entityUrn}`
- **Unreact**: `DELETE /voyager/api/reactions/{entityUrn}`
- **Post create**: `POST /voyager/api/feed/dash/posts` — body: commentaryV2 + origin
- **Post edit**: `PUT /voyager/api/feed/dash/posts/{postUrn}`
- **Post delete**: `DELETE /voyager/api/feed/dash/posts/{postUrn}`
- **Comment create**: `POST /voyager/api/feed/dash/comments` — body: threadUrn + commentaryV2
- **Comment edit**: `PUT /voyager/api/feed/dash/comments/{commentUrn}`
- **Comment delete**: `DELETE /voyager/api/feed/dash/comments/{commentUrn}`
- **Follow**: `POST /voyager/api/feed/follows` — body: `{followee: companyUrn}`
- **Unfollow**: `DELETE /voyager/api/feed/follows/{companyUrn}`

### Notifications (REST)

- **Endpoint**: `GET /voyager/api/voyagerIdentityDashNotificationCards`
- **Params**: `decorationId=...CardsCollectionWithInjectionsNoPills-24`, `count=N`, `start=N`, `q=filterVanityName`

### Network — Connections (REST)

- **List**: `GET /voyager/api/relationships/dash/connections` — params: `decorationId=...ConnectionListWithProfile-5`, `count`, `start`, `q=search`, `sortType=RECENTLY_ADDED`
- **Response**: Profile objects in `included` array (firstName, lastName, headline)
- **Count**: `GET /voyager/api/relationships/connectionsSummary` — returns `{numConnections}`

### Network — Invitations (REST)

- **List**: `GET /voyager/api/relationships/invitationViews` — params: `includeInsights=true`, `q=receivedInvitation`, `start`, `count`
- **Accept**: `POST /voyager/api/relationships/invitations/{invitationUrn}?action=accept`
- **Decline**: `POST /voyager/api/relationships/invitations/{invitationUrn}?action=decline`

### Network — Connect (REST)

- **Endpoint**: `POST /voyager/api/relationships/invitations`
- **Body**: `{inviteeProfileUrn, message?}`

### Messaging — Conversations (Messaging GraphQL)

- **Endpoint**: `GET /voyager/api/voyagerMessagingGraphQL/graphql`
- **queryId**: `messengerConversations.0d5e6781bbee71c3e51c8843c6519f48`
- **variables**: `(mailboxUrn:{profileUrn})` — URN colons must be percent-encoded

### Messaging — Messages (Messaging GraphQL)

- **queryId**: `messengerMessages.5846eeb71c981f11e0134cb6626cc314`
- **variables**: `(conversationUrn:{conversationUrn})`

### Messaging — Send (REST)

- **Endpoint**: `POST /voyager/api/voyagerMessagingDashMessengerMessages?action=createMessage`
- **Body**: `{body, mailboxUrn, conversationUrn|recipientProfileUrns[]}`

## CLI Command Structure (26 commands, 10 groups)

```
cli-web-linkedin
├── auth login/status/logout       # Browser login, cookie management
├── feed [--count N]               # View feed posts with likes/comments
├── profile get <username>         # View user profile
├── profile me                     # View own profile
├── company <name>                 # View company page (via search)
├── company follow <urn>           # Follow a company
├── company unfollow <urn>         # Unfollow a company
├── jobs search <query>            # Search jobs (REST)
├── jobs get <id>                  # View full job details + description
├── search all <query>             # General search (unfiltered)
├── search people <query>          # Search people (GraphQL)
├── search companies <query>       # Search companies (GraphQL)
├── search jobs <query>            # Search jobs (GraphQL)
├── post create <text>             # Publish a post
├── post edit <urn> <text>         # Edit a post
├── post delete <urn>              # Delete a post
├── post react <urn> [--type]      # React to a post
├── post unreact <urn>             # Remove reaction
├── post comment <urn> <text>      # Comment on a post
├── post edit-comment <urn> <text> # Edit a comment
├── post delete-comment <urn>      # Delete a comment
├── notifications [--limit N]      # View notifications
├── network connections            # List connections with names
├── network invitations            # View pending invitations
├── network accept <urn>           # Accept invitation
├── network decline <urn>          # Decline invitation
├── network connect <urn> [-m]     # Send connection request
├── messaging list                 # List conversations
├── messaging read <urn>           # Read messages in conversation
└── messaging send <urn> <text>    # Send a message
```

## Notes

- GraphQL queryId hashes may rotate — search hash `b0928897b71bd00a5a7291755dcd64f0` stable as of 2026-04-09
- LinkedIn variables use custom serialization `(key:value)`, NOT JSON
- URL params must NOT be URL-encoded (parentheses must be literal)
- All search uses GraphQL `voyagerSearchDashClusters` endpoint (no browser needed)
- PerimeterX protection bypassed via curl_cffi Chrome TLS impersonation
- Do NOT set a custom User-Agent — curl_cffi injects a matching Chrome UA via impersonation
- Gaussian random delay (mean 1.5s) between API calls to avoid bot detection
