# Stitch Traffic Capture #2 — Edit Screen, Duplicate, Model Selector

Captured on 2026-03-22 from project `5729743076671706715` ("Remix of Dashboard").

## Feature 1: Edit a Specific Screen

### Flow
1. Click on a screen thumbnail in the canvas → toolbar appears with "Generate", "Modify", "Preview", "More"
2. The selected screen name appears as a chip in the prompt input area
3. Type edit prompt and press Enter → `IEkn6e` RPC fires
4. Polling begins with `uYEY6` (~1.3s interval) until generation completes
5. `f6CJY` fires to get updated project data (multiple times during generation)

### RPC: `IEkn6e` — EDIT_SCREEN (Submit prompt targeting specific screens)

**Request f.req structure:**
```
[[["IEkn6e", "<inner_json>", null, "generic"]]]
```

**Inner JSON params:**
```json
[
  "projects/<project_id>",          // [0] project resource name
  [                                  // [1] generation config
    null,                            // [1][0]
    null,                            // [1][1]
    null,                            // [1][2]
    [                                // [1][3] prompt + style config
      "<prompt_text>",               // [1][3][0] user prompt text
      [                              // [1][3][1] style/model config
        1,                           // device_type? (1=mobile)
        5,                           // ???
        3,                           // model_id? (3=Flash)
        null,
        "#98A68E",                   // primary color hex
        null, null, null, null,
        5,                           // ???
        8,                           // ???
        8,                           // ???
        [                            // Material Design color tokens array
          ["surface_variant", "#e1e3dc"],
          ["on_primary_fixed_variant", "#3e4a37"],
          ["on_primary_fixed", "#131e0e"],
          ["on_primary", "#ffffff"],
          // ... 40+ Material Design tokens
        ],
        "<design_system_markdown>"   // The full design system strategy doc
      ],
      // ... additional params for screen selection/targeting
    ]
  ]
]
```

**Response:**
```
[
  "projects/<project_id>/sessions/<session_id>",  // New session created
  null,
  1,                                               // Status indicator
  [<prompt_echo>, <style_config>]                  // Echoed prompt and config
]
```

Note: The `IEkn6e` RPC is the SAME RPC used for general prompts, but when a screen is selected,
the params include screen-specific targeting. The screen selection is done client-side via the chip UI.

### RPC: `uYEY6` — POLL_SESSION (Poll for generation progress)

**Request f.req:**
```json
[[["uYEY6", "[\"projects/<project_id>/sessions/<session_id>\"]", null, "generic"]]]
```

**Response (while in progress):** Contains partial generation state including the prompt, style config, and streaming text/code output.

**Response (completed):** Full generation result with screen HTML/code.

Polling interval: ~1.3 seconds

### RPC: `N5xENe` — GET_QUOTAS (Check usage limits)

**Request f.req:**
```json
[[["N5xENe", "[]", null, "generic"]]]
```

**Response:**
```json
[null,null,null,null,null,null,null,null,33,400,null,15,null,null,null,null,1,1,2]
```
- Position [8] = 33 (current usage count?)
- Position [9] = 400 (quota limit?)
- Position [11] = 15 (another limit?)

### RPC: `f6CJY` — GET_PROJECT (Fetch full project data)

Same RPC captured in traffic capture #1. Called multiple times during generation to refresh project state.

**Request params include:** project_id, project_name, version, thumbnail URL, style config, design system doc.

### RPC: `yxssG` — REPORT_USAGE (Analytics/billing event)

**Request f.req:**
```json
[[["yxssG", "[null,null,[\"projects/<project_id>\",\"projects/<project_id>/sessions/<session_id>\",41166,41166,42129,42129]]", null, "generic"]]]
```

Numbers likely represent token counts: input_tokens, input_tokens, output_tokens, output_tokens.

**Response:** `[]` (empty)


## Feature 2: Duplicate Project

### Flow
1. Click hamburger menu (top-left button)
2. Menu items appear: "לכל הפרויקטים", "שיתוף", "הורדת הפרויקט", **"שכפול הפרויקט"**, "עריכה", "עזרה", "Light mode", "הגדרות", "מחיקת הפרויקט", "תפריט הפקודות Ctrl+K", "שליחת משוב"
3. Click "שכפול הפרויקט" → confirmation dialog appears
4. Dialog: "הפעולה הזו תיצור פרויקט חדש עם כל המסכים והתוכן מהפרויקט הנוכחי. להמשיך?"
5. Click "שכפול" → `vW3whd` RPC fires
6. Response returns new project ID

### RPC: `vW3whd` — DUPLICATE_PROJECT

**Request f.req structure:**
```
[[["vW3whd", "<inner_json>", null, "generic"]]]
```

**Inner JSON params:**
```json
[
  "projects/<source_project_id>",    // [0] source project resource name
  [                                   // [1] full project data snapshot
    "projects/<source_project_id>",   // [1][0] project resource name
    "<project_name>",                 // [1][1] project display name (e.g., "Remix of Dashboard")
    2,                                // [1][2] project type? version?
    null,                             // [1][3]
    null,                             // [1][4]
    4,                                // [1][5] ???
    [                                 // [1][6] thumbnail info
      "projects/<id>/files/<file_id>",  // file resource name
      null,
      "https://lh3.googleusercontent.com/aida/..."  // thumbnail URL
    ],
    1,                                // [1][7] ???
    1,                                // [1][8] ???
    [                                 // [1][9] style config (same as IEkn6e)
      1, 5, 3, null, "#98A68E",
      null, null, null, null, 5, 8, 8,
      [/* 46 Material Design color tokens */],
      "<design_system_markdown>"       // Full design system doc
    ]
  ]
]
```

**Response:**
```json
[null, "projects/8462610593352154184"]
```
- `[0]` = null (no error)
- `[1]` = new project resource name with new ID

**New project ID created:** `8462610593352154184` (needs to be deleted later!)


## Feature 3: Model Selector

### Available Models (from dropdown UI)

| Display Name | Internal Description | Notes |
|---|---|---|
| **3 Flash** (3.0 Flash) | Gemini 3.0 Flash — design in high quality HTML, export to coding agents | Default, currently selected |
| **Thinking with 3.1 Pro** | Gemini 3.1 Pro — prioritizes quality and rational thinking over speed | Higher quality, slower |
| **Redesign** | Nano Banana Pro — redesign existing apps/websites, requires screenshot attachment | Specialized mode |

### Model Selection Mechanism
- The model selector is a **pure UI dropdown** — opening it does NOT trigger any batchexecute RPCs
- The selected model is passed as a parameter in the style config array sent with `IEkn6e` (edit/prompt)
- Specifically, position `[1][3][1][2]` in the IEkn6e params appears to be the model ID:
  - `3` = 3.0 Flash (observed in captured traffic)
  - Other values TBD (need to capture with Pro/Redesign selected)

### Key Finding: No Gemini Pro in the traditional sense
- There is no plain "Gemini Pro" option
- The Pro option is "**Thinking with 3.1 Pro**" which is Gemini 3.1 Pro with extended thinking
- The third option "**Redesign**" uses "**Nano Banana Pro**" (likely an internal model name)


## New RPC Summary

| RPC ID | Operation | Params | New? |
|--------|-----------|--------|------|
| `IEkn6e` | EDIT_SCREEN / SEND_PROMPT | project_id, prompt, style_config, model | Previously seen as SEND_PROMPT, now confirmed works for screen-specific edits |
| `uYEY6` | POLL_SESSION | session_id | Polling RPC |
| `N5xENe` | GET_QUOTAS | (none) | **NEW** — returns usage/quota counters |
| `yxssG` | REPORT_USAGE | project_id, session_id, token_counts | **NEW** — analytics/billing |
| `vW3whd` | DUPLICATE_PROJECT | source_project_id, full_project_snapshot | **NEW** — duplicates project, returns new project_id |
| `f6CJY` | GET_PROJECT | project_id, name, style, etc. | Previously captured |


## Cleanup Required
- Delete duplicated project: `projects/8462610593352154184`
