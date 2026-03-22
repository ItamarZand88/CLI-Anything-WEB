# Agent Session Learnings

Automatic reflections captured at the end of each Claude Code session.
Each entry records what the agent learned, what worked, and what it would do differently next time.

---

## 2026-03-22 — CLI-Anything-Web (Major Bug Fix Session)

**Task**: Fix NotebookLM CLI — auth, sources, chat, artifacts were all broken. Create presentation about Claude Code.

**Approach**: Compared cli-web-notebooklm implementation against notebooklm-py reference. Found 15+ bugs across auth, RPC methods, param structures, response parsing, and download handling. Fixed systematically.

**What worked well**:
- Reading the reference implementation (notebooklm-py) side-by-side was the fastest way to find bugs
- Testing each fix immediately with `--json` output caught regressions
- Fixing one layer at a time (auth → sources → chat → artifacts → download) prevented confusion

**What you'd do differently**:
1. **Never trust RPC IDs from initial traffic analysis** — always cross-reference with a known-working implementation before coding. VfAZjd/hPTbtc/izAoDd confusion caused 3 of the biggest bugs.
2. **Test `--json` output after every command implementation** — raw RPC data in chat output went unnoticed because nobody ran `chat ask --json` during initial dev.
3. **Verify param structures match captured traffic exactly** — wrong `GET_NOTEBOOK` params (`[notebook_id]` vs `[notebook_id, None, [2], None, 0]`) caused invisible failures.
4. **Use Python `sync_playwright()` for auth, not npx** — the npx approach has fundamental interactive input issues on Windows.
5. **Domain-aware cookies for downloads** — flat cookie dicts lose domain info needed for cross-domain Google downloads (usercontent.google.com).

**Key bugs found and fixed**:
| # | Bug | Root Cause | Lesson |
|---|-----|-----------|--------|
| 1 | Auth login fails | npx playwright-cli has interactive input race | Use Python sync_playwright() |
| 2 | Auth crashes on redirect | accounts.google.com auto-redirects | Wrap navigation in try/except |
| 3 | Sources add-url broken | Wrong RPC ID (VfAZjd = SUMMARIZE) | Always cross-reference RPC IDs |
| 4 | Sources add-text broken | Wrong RPC ID (hPTbtc = GET_CONVERSATION_ID) | One RPC can serve multiple ops |
| 5 | Sources list empty | Incomplete GET_NOTEBOOK params | Verify full param structure |
| 6 | Chat returns raw RPC | Parser used wrong heuristics | Parse wrb.fr → json.loads(item[2]) → inner[0][0] |
| 7 | Chat body encoding wrong | urllib.parse.urlencode double-encodes | Use quote(safe='') per part |
| 8 | Chat params incomplete | Missing notebook_id in request | Copy full param array from reference |
| 9 | Artifacts return id="" | Missing type-specific config blocks | Each type needs unique param structure |
| 10 | Mind map wrong RPC | Used R7cb6c instead of yyryJe | Mind maps are NOT artifacts |
| 11 | Video wrong params | Config at wrong array position | Count Nones carefully |
| 12 | Downloads 403 | Flat cookie dict loses domain info | Use domain-aware httpx.Cookies |
| 13 | Data table raw output | Didn't parse nested cell structure | Use recursive text extractor |
| 14 | Quiz empty | Wrong params ([None, id] vs [id]) | Check reference exactly |

**Key insight**: The #1 source of bugs in batchexecute CLIs is wrong RPC method IDs and wrong param structures. Every single RPC call must be verified against captured traffic or a known-working implementation. "Close enough" params cause silent failures.

---
