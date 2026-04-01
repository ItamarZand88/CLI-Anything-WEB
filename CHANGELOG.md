# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.6.1](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.6.0...v0.6.1) (2026-03-30)


### Bug Fixes

* **reddit:** fetch deeply nested comments ([0a4a207](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/0a4a20751f2890dcb6aaa97b4f2ee0c9bd8acd58))
* **reddit:** fetch deeply nested comments that were silently dropped ([aa47181](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/aa47181176f8ff953ec61d91cc90a48d9b9a25e7))

## [0.6.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.5.0...v0.6.0) (2026-03-30)


### Features

* **chatgpt:** add cli-web-chatgpt — 14th CLI ([5f4b626](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5f4b626a65f48e96689e47035facf45634bb5832))
* **chatgpt:** add cli-web-chatgpt — 14th CLI for ChatGPT ([2d4a353](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/2d4a353985b521c6458b7f2d4bae2141e93949e0))

## [0.5.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.4.2...v0.5.0) (2026-03-30)


### Features

* **futbin:** add market analysis, arbitrage, scan, versions commands + trading knowledge base ([45aba74](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/45aba749a8054e7b5c8f34bf05cd962750d7a735))

## [0.4.2](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.4.1...v0.4.2) (2026-03-30)


### Bug Fixes

* **registry:** update CLI count from 12 to 13 ([5b060e5](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5b060e59f4405d54cabf26a257b6829747f0d56e))

## [0.4.1](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.4.0...v0.4.1) (2026-03-29)


### Bug Fixes

* **reddit:** improve comment tree display with box-drawing indent characters ([bddecc4](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/bddecc4fae66b29eaed0c5dd78d6cafb1a090ca6))

## [0.4.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.3.0...v0.4.0) (2026-03-29)


### Features

* **codewiki:** add CLI for Google Code Wiki with Gemini chat ([bab05a9](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/bab05a9935e886f6d482d491522cd7149d04a55b))
* **codewiki:** add CLI for Google Code Wiki with Gemini chat ([66a291a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/66a291add8024b046b48b85cb98c15afe6f1da7f))
* **futbin:** market trading commands, price history, and fix player scraping ([#8](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/8)) ([5e547ba](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5e547ba1dcd725da179f8bfcf6b4f20906610dea))

## [0.3.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.2.0...v0.3.0) (2026-03-29)


### Features

* add mitmproxy-based traffic capture (opt-in --mitmproxy flag) ([3867e02](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3867e02524de5c1b877a5520d7690d9e900a79a6))
* add mitmproxy-based traffic capture and enhanced traffic analysis ([9857f99](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/9857f996702db448dd76ce78834a1d27f25a4ae7))
* add plugin agents, skills, and reddit newline fix ([32e024f](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/32e024f0d9d24dc02af179321d142a20ddf92f9c))
* **plugin:** add 3 review agents, replace review-agents.md reference ([c1466bd](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/c1466bd4a23174e9f7de7f6edd1a89eb0052b11e))
* **plugin:** add boilerplate generator skill for core/ scaffolding ([d9851a8](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/d9851a8eec05c1327c8467a740e2a0198793263e))
* **plugin:** add cross-CLI consistency checker agent ([ab20302](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ab20302cd5f4c6b5d311d40c63bba1dd7963f11e))
* **plugin:** add gap analyzer skill for structured refine workflow ([2b7b6e3](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/2b7b6e39b63fdb1c9356a7116a4fe6f4e5fcba1b))
* **plugin:** add review agents, boilerplate skill, consistency checker, gap analyzer + fix reddit newline escape ([ed665b9](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ed665b929196f9551e0623b9c067915648b3379c))


### Bug Fixes

* add youtube + hackernews to CI test matrix, add CI step to Phase 4 ([59ddc63](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/59ddc6398f4e7c867ec4a734096d614c54bd6088))
* **plugin:** address review findings across new agents and skills ([614fe4c](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/614fe4c135511a3373d713b07742b75235c3e7a9))
* **plugin:** revert curl_cffi except narrowing — keep broad catch ([a8d0adc](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/a8d0adcf4f609ce505b01ca9662d0863484be78b))
* **reddit:** post get works with just ID, t3_ prefix, and includes parent_id ([#7](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/7)) ([4fdc8b9](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/4fdc8b9c5844190d602ccd4800b77c59dc252b9b))

## [0.2.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.1.0...v0.2.0) (2026-03-27)


### Features

* add cli-web-hackernews — browse, search, and interact with Hacker News ([7dcd17a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/7dcd17aa8625d2dec503ac604d64e87d177cd07d))
* add cli-web-youtube — search, video details, trending, channels ([9ee1f63](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/9ee1f637d10451074b363ca1af1aeb6781af1851))

## [Unreleased]

### Added
- **cli-web-chatgpt** — 14th CLI. Ask questions, generate/download images, list conversations, browse models. Hybrid architecture: curl_cffi for read-only API, Camoufox stealth Firefox for chat/image generation (fully headless, bypasses Cloudflare). OpenAI SSO auth via browser login. 53 tests (34 unit + 19 E2E).
- **cli-web-hackernews** — 12th CLI. Browse stories (top/new/best/ask/show/jobs), search via Algolia, view comments, user profiles. Auth-enabled: upvote, submit, comment, favorite, hide, view favorites/submissions/threads. Uses Firebase REST API + Algolia search + HN web forms. 61 tests (31 unit + 30 E2E).
- **cli-web-youtube** — 11th CLI. Search videos, get video details (views, duration, keywords), browse trending by category, explore channels. Uses YouTube's InnerTube REST API. No auth required.
- **Review step in Phase 4** — Standards skill now dispatches 3 parallel review agents (Traffic Fidelity, HARNESS Compliance, Output & UX) before the structural checklist and publish steps.
- **Flair support for cli-web-reddit** — `submit flairs <subreddit>` lists available flairs, `--flair ID` on `submit text`/`submit link`.

### Fixed
- **reddit**: Deep comments bug — `post get` now fetches all deeply nested comments by expanding Reddit's "more" objects via `/api/morechildren.json` and "continue this thread" chains via permalink `.json`. Previously comments deeper than ~10 levels were silently dropped.
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
