# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **cli-web-hackernews** — 12th CLI. Browse stories (top/new/best/ask/show/jobs), search via Algolia, view comments, user profiles. Auth-enabled: upvote, submit, comment, favorite, hide, view favorites/submissions/threads. Uses Firebase REST API + Algolia search + HN web forms. 61 tests (31 unit + 30 E2E).
- **cli-web-youtube** — 11th CLI. Search videos, get video details (views, duration, keywords), browse trending by category, explore channels. Uses YouTube's InnerTube REST API. No auth required.
- **Review step in Phase 4** — Standards skill now dispatches 3 parallel review agents (Traffic Fidelity, HARNESS Compliance, Output & UX) before the structural checklist and publish steps.
- **Flair support for cli-web-reddit** — `submit flairs <subreddit>` lists available flairs, `--flair ID` on `submit text`/`submit link`.

### Fixed
- **gh-trending**: Added missing UTF-8 stderr fix for Windows, `handle_errors()` context manager, correct error codes (AUTH_EXPIRED, RATE_LIMITED), `RateLimitError.to_dict()` includes retry_after, `ServerError` stores status_code, REPL banner shows "GitHub Trending" instead of "Gh Trending".
- **reddit**: Added auth retry on recoverable AuthError, `RedditError.to_dict()`, replaced `click.ClickException` with `SubmitError` in submit/comment commands, fixed stderr UTF-8, added `load_cookies()` plain dict handling, removed dead client methods.
- **pexels**: Replaced `click.ClickException` with `NotFoundError` in videos/photos download, added `to_dict()` to `PexelsError`, added retry_after to JSON errors, fixed stderr UTF-8, removed duplicate normalizers from client.py, removed dead `raise_for_status()`.
- **producthunt**: Removed dead `collections_cmd.py` and `topics.py` (would crash with AttributeError), removed unused `GraphQLError`, rewrote stale PRODUCTHUNT.md.
- **futbin**: Fixed `--category` type to int, removed dead `get_sbc()`/`get_evolution()`, fixed `SBCDetail.id`/`EvolutionDetail.id` types from str to int.

## [0.1.0] - 2026-03-26

### Added
- Initial open-source release with 10 reference CLIs
- CLI-Anything-Web Claude Code plugin with 4-phase pipeline (capture → methodology → testing → standards)
- 10 reference CLIs: Stitch, Reddit, Booking.com, Google AI Mode, NotebookLM, Pexels, Unsplash, Product Hunt, FUTBIN, GitHub Trending
- Plugin with 6 slash commands, 4 skills, 22 reference files, 9 scripts
- GitHub Pages registry at /docs/registry/
- GitHub Actions CI workflow
- CODE_OF_CONDUCT.md, CONTRIBUTING.md, SECURITY.md, issue templates

[Unreleased]: https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ItamarZand88/CLI-Anything-WEB/releases/tag/v0.1.0
