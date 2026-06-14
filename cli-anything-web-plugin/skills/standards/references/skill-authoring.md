# Skill Authoring Guide (per-CLI skills)

## Contents
- Frontmatter rules
- Description writing
- Body rules
- Standard structure for per-CLI skills
- Anti-patterns
- Quality checklist

Distilled from Anthropic's official skill-authoring best practices and the
Claude Code skills reference. Applies to the per-CLI skills generated in
Phase 4 (`.claude/skills/<app>-cli/SKILL.md`) and to any skill in this repo.
Enforced mechanically by `scripts/tests/test_skill_quality.py`.

## Frontmatter rules

```yaml
---
name: <app>-cli            # lowercase letters/numbers/hyphens, ≤64 chars
description: >             # REQUIRED. Third person. ≤1024 chars. No XML tags.
  <What the skill does — key use case first.> Use when <triggers>.
when_to_use: >             # OPTIONAL. Extra trigger phrases / example requests.
  Trigger phrases: "...", "...". Not for <adjacent-but-different tasks>.
---
```

- Field names use **hyphens**: `user-invocable`, `disable-model-invocation`,
  `argument-hint`. Underscored variants are silently ignored (except
  `when_to_use`, which is the documented spelling).
- `description` + `when_to_use` combined are truncated at 1,536 chars in the
  skill listing — stay well under (target ≤800 combined).
- Write descriptions in third person ("Searches X, downloads Y"), never
  "I can..." or "You can use this to...".
- Include the words users actually say (site name, domain terms, task verbs)
  so the skill triggers reliably among 100+ skills.

## Description writing

Good (what + when, key use case first, third person):

```yaml
description: >
  Use cli-web-hackernews to browse Hacker News — top/new/best stories,
  search, story comments, user profiles, and (with auth) upvote, submit,
  and comment. Use whenever the user asks about Hacker News, HN stories,
  tech news discussions, or wants to interact with HN from the terminal.
```

Avoid: vague ("Helps with news"), first person, listing every flag, or
duplicating the body.

## Body rules

- **≤500 lines hard cap; target 60–150 for per-CLI skills.** Once loaded,
  every line is a recurring token cost across the conversation.
- Assume Claude already knows common concepts (JSON, HTTP, pip). Only add
  what it cannot know: this CLI's command surface, quirks, auth flow.
- **Every documented command must be real** — verified against
  `cli-web-<app> --help`. A stale example is worse than no example.
- 3–5 concrete examples beat exhaustive flag tables.
- Progressive disclosure: long reference material (strategy guides, large
  schemas) goes in a sibling file linked one level deep from SKILL.md, with
  a table of contents if >100 lines.
- Consistent terminology (one term per concept). No time-sensitive content.
- Prefer one default approach; offer alternatives only as an escape hatch.
- Reserve MUST/NEVER/CRITICAL/ALWAYS for genuinely critical rules — current
  models overtrigger on aggressive emphasis. "Use X when…" beats
  "CRITICAL: You MUST use X".
- Say what to do rather than what not to do, where possible.

## Standard structure for per-CLI skills

```markdown
# cli-web-<app>

<One-line purpose.> Install: `pip install cli-web-<app>`

## Commands
<real surface, grouped — verified against --help>

## Examples
<3–5 concrete invocations with expected-output notes>

## JSON output
<the --json envelope; --jsonl if the CLI has it>

## Auth                       # auth-bearing CLIs only
<login flow, CLI_WEB_<APP>_AUTH_JSON env var, `doctor` for diagnosis>

## Utilities
`cli-web-<app> doctor [--json]` — diagnose install/auth setup.
`cli-web-<app> mcp-serve` — serve every command as MCP tools over stdio.

## Agent tips                 # only if genuinely useful
```

## Anti-patterns

- Documenting commands or flags that don't exist (verify with `--help`)
- First-person or vague descriptions
- Bodies >500 lines or descriptions >1024 chars (hard limits)
- Underscored frontmatter field names (`user_invocable`)
- Nested reference chains (SKILL.md → a.md → b.md)
- Repeating the JSON envelope spec at length — one example suffices
- Windows-style paths

## Quality checklist

- [ ] Description: third person, what + when, key terms, ≤1024 chars
- [ ] Combined description + when_to_use ≤800 chars (1,536 hard cap)
- [ ] Body ≤500 lines (target ≤150)
- [ ] Every command/flag verified against the installed CLI's --help
- [ ] 3–5 concrete examples
- [ ] Auth section only when the CLI has auth
- [ ] doctor + mcp-serve mentioned under Utilities
- [ ] Reference files (if any) linked one level deep, with TOC if >100 lines
