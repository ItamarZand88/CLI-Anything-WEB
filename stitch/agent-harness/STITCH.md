# STITCH.md — Google Stitch CLI API Map

**Target:** https://stitch.withgoogle.com/
**Protocol:** Google batchexecute (service name: Nemo)
**Auth:** Google SSO cookie-based (OSID, __Secure-3PSID, etc.)
**Endpoint:** `https://stitch.withgoogle.com/_/Nemo/data/batchexecute`
**Download:** `https://contribution.usercontent.google.com/download`

## Site Profile

Auth + CRUD Google app using the batchexecute RPC protocol.
Google Stitch is an AI-native UI design canvas by Google Labs that transforms
natural language prompts into fully editable UI designs and production-ready
HTML code. Uses Gemini models for generation.

## RPC Method IDs

| RPC ID   | Operation          | Description |
|----------|--------------------|-------------|
| `o30O0e` | GET_USER_INFO      | Get current user profile (name, avatar) |
| `A7f2qf` | LIST_PROJECTS      | List all projects owned by user |
| `N5xENe` | GET_APP_CONFIG     | Get app config and feature limits |
| `eW2RYb` | GET_PROJECT        | Get project details (metadata, theme, screens) |
| `f6CJY`  | GET_PROJECT_STATE  | Get/refresh current project state |
| `UiiVCf` | GET_DESIGN_ASSETS  | Get design system assets (colors, typography) |
| `ErneX`  | LIST_SCREENS       | List all screens in a project |
| `dNS8Mc` | LIST_SESSIONS      | List generation sessions (prompt history) |
| `cabgj`  | CREATE_PROJECT     | Create new empty project. Params: `[[null,null,null,null,null,4]]` |
| `IEkn6e` | SEND_PROMPT        | Send AI prompt. Params: `[resource_name, [null,null,null,[prompt,null,1,null,[],null,null,1,[],platform_id],null,null,1]]` |
| `uYEY6`  | POLL_SESSION       | Poll generation session for progress |
| `yxssG`  | EXPORT_PROJECT     | Trigger project export as ZIP |
| `vW3whd` | DUPLICATE_PROJECT   | Duplicate project. Params: `[resource_name]`. Response: `[null, "projects/<new_id>"]` |
| `hxYVdb` | DELETE_PROJECT      | Delete a project |

## Data Model

### Project
- `resource_name`: `"projects/<id>"` (numeric ID)
- `title`: string (null for newly created)
- `type`: 2 (standard project)
- `created_at`: `[seconds, nanoseconds]`
- `modified_at`: `[seconds, nanoseconds]`
- `status`: 4 = ready
- `thumbnail`: `[file_resource, null, image_url]`
- `owner_flag`: 1 = owned by me
- `theme_mode`: 1 = light, 2 = dark
- `theme_config`: design system with Material color tokens

### Screen
- `thumbnail`: `[file_resource, null, thumbnail_url]`
- `html_file`: `[file_resource, null, download_url, null, null, "text/html"]`
- `screen_id`: string
- `agent_name`: string (e.g., "figaro_agent", "HatterAgent")
- `width`: int
- `height`: int
- `name`: string (e.g., "Insights", "Notes Gallery")
- `description`: string
- `resource_name`: string

### Session (Generation)
- `resource_name`: `"projects/<pid>/sessions/<sid>"`
- `status`: null=pending, 1=started, 2=in-progress, 3=completed
- `prompt`: text
- `results`: screens array with AI explanation text
- `timestamp`: seconds

## Auth Scheme

Google SSO cookies. Same pattern as NotebookLM:
- Cookie names: OSID, __Secure-3PSID, __Secure-3PAPISID, etc.
- Tokens extracted from homepage HTML: SNlM0e (CSRF), FdrFJe (session ID), cfb2h (build label)
- `.google.com` cookies take priority over regional domains
- Auth login via Python sync_playwright() with persistent context

**Note:** Stitch uses an iframe on `app-companion-430619.appspot.com` but the
batchexecute requests go to `stitch.withgoogle.com/_/Nemo/data/batchexecute`.
CSRF/session tokens must be extracted from the main `stitch.withgoogle.com` page.

## CLI Command Structure

```
cli-web-stitch
├── auth login          # Browser login
├── auth status         # Check auth status
├── auth import <file>  # Import cookies from file
├── use <project-id>    # Set active project context
├── status              # Show current context
├── projects
│   ├── list            # List all projects
│   ├── get <id>        # Get project details
│   ├── create <prompt> # Create + generate new project
│   ├── rename <id> <name> # Rename project
│   ├── duplicate <id>  # Clone/duplicate project
│   ├── delete <id> [-y]# Delete project (with confirmation)
│   └── download <id>   # Export/download as ZIP
├── screens
│   ├── list            # List screens in active project
│   ├── get <id>        # Get screen details + download HTML
│   └── download <id>   # Download specific screen HTML
└── design
    ├── generate <prompt>  # Send prompt to modify design (+ poll)
    │   --model flash|pro|redesign   # AI model selection
    │   --device mobile|web|tablet|agnostic  # Device type
    ├── theme              # Show design system (colors, typography)
    └── history            # List generation sessions
```

## Operation Flows

**Create project**: `cabgj` (params: `[[null,null,null,null,null,4]]`) → `IEkn6e` (prompt) → `uYEY6` × N (poll) → done
**Modify design**: `IEkn6e` (prompt) → `uYEY6` × N (poll) → done
**Download**: `yxssG` (trigger) → GET `contribution.usercontent.google.com/download`
**List projects**: `A7f2qf`
**Get design system**: `eW2RYb` (GET_PROJECT) → result[9] contains theme config
**Rename project**: `f6CJY` with `[[resource_name, new_title, 2, ...], [["title"]]]`
**Delete project**: `hxYVdb`

## Dependencies

- click, httpx, rich>=13.0, playwright (auth only)
