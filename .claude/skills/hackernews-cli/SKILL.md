---
name: hackernews-cli
description: Use cli-web-hackernews to browse and interact with Hacker News — top stories, newest, best, Ask HN, Show HN, jobs, search stories/comments, view story details with comments, user profiles, and (with auth) upvote, submit stories, post comments, favorite, hide, view favorites, submissions, and comment threads. Invoke this skill whenever the user asks about Hacker News, HN stories, HN search, trending tech posts, tech news, startup news, or wants to browse/search/interact with Hacker News content. Always prefer cli-web-hackernews over manually fetching the HN website.
user_invocable: true
---

# cli-web-hackernews — Hacker News CLI

## When to use
- User asks about Hacker News, HN, tech news, startup news
- User wants to browse top/new/best stories, Ask HN, Show HN, or jobs
- User wants to search HN for specific topics
- User wants to view a specific story with comments
- User wants to look up an HN user profile
- User wants to upvote, submit, comment, favorite, or hide on HN

## Browse Commands (no auth)

```bash
# Browse stories
cli-web-hackernews stories top -n 10 --json       # Front page
cli-web-hackernews stories new -n 10 --json        # Newest
cli-web-hackernews stories best -n 10 --json       # Best (all time)
cli-web-hackernews stories ask -n 10 --json        # Ask HN
cli-web-hackernews stories show -n 10 --json       # Show HN
cli-web-hackernews stories jobs -n 10 --json       # Jobs

# View story + comments
cli-web-hackernews stories view 47530330 --json
cli-web-hackernews stories view 47530330 -n 5 --json   # limit comments

# Search
cli-web-hackernews search stories "query" -n 10 --json
cli-web-hackernews search comments "query" --sort-date -n 5 --json

# User profiles
cli-web-hackernews user view dang --json
```

## Auth Commands (requires login)

```bash
# Authentication
cli-web-hackernews auth login                      # Username/password prompt
cli-web-hackernews auth status --json              # Check login status
cli-web-hackernews auth logout                     # Remove credentials

# Actions
cli-web-hackernews upvote 47530330 --json          # Upvote story/comment
cli-web-hackernews submit -t "Title" -u "URL" --json  # Submit link
cli-web-hackernews submit -t "Ask HN: Q?" --text "Details" --json  # Ask HN
cli-web-hackernews comment 47530330 "Great!" --json    # Post comment
cli-web-hackernews favorite 47530330 --json        # Save to favorites
cli-web-hackernews hide 47530330 --json            # Hide from feed

# Activity
cli-web-hackernews user favorites --json           # Your favorites
cli-web-hackernews user submissions --json         # Your submissions
cli-web-hackernews user threads --json             # Replies to your comments
cli-web-hackernews user submissions dang --json    # Others' submissions
```

## Always use --json when calling programmatically

All commands support `--json` for structured output. Always use it when processing results.

## Key fields in JSON output

### Story
- `id`, `title`, `url`, `score`, `by`, `descendants` (comment count), `age`, `domain`

### Search Result
- `objectID` (story ID), `title`, `url`, `author`, `points`, `num_comments`

### User
- `id`, `karma`, `member_since`, `about_plain`, `total_submissions`

### Action Result
- `success`, `item_id`, `action` (upvoted/favorited/hidden)
