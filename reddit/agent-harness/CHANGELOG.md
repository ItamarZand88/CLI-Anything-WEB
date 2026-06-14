# Changelog

## 0.1.0 (2026-06-14)


### Features

* add plugin agents, skills, and reddit newline fix ([32e024f](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/32e024f0d9d24dc02af179321d142a20ddf92f9c))
* fleet-wide doctor command (self-diagnosis) via vendored core module ([5c2f403](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5c2f4032b1da6d4d12f8aeb04899c373e953c363))
* Phase 1+2 — quality gates, cli-web-devkit, cli-web-core, fleet sync ([bbb6a88](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/bbb6a88276cdd1095665b56e900cb061bb529b35))
* Phases 3-5 — generation v2, fleet ops, api-spec IR, MCP serve fleet-wide ([61caad1](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/61caad16cb7915c440967cfee367f9ca99b64557))
* **plugin:** add review agents, boilerplate skill, consistency checker, gap analyzer + fix reddit newline escape ([ed665b9](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ed665b929196f9551e0623b9c067915648b3379c))
* publish the CLI fleet to PyPI (per-CLI + umbrella) ([59ca9f6](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/59ca9f67ac99829370a6f679385fd1cf2186740c))
* refactor pipeline skill content to authoring/prompting best practices ([6170131](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/6170131dca335753d286d37761f2776467ece43f))
* shared runtime (cli-web-core), fleet devkit, and repo-wide quality gates ([2932dc2](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/2932dc23bbb58cc1f36982c1abb9f8fc1de147be))


### Bug Fixes

* address code-review findings in shared runtime, pipeline, and quality gate ([06988a0](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/06988a0266db671c58077379834febdccf65205d))
* **reddit:** auto-refresh token_v2 on expiry + fix 403 misreported as AUTH_EXPIRED ([e56c3ea](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/e56c3ead10e4684486a860c096f86083216a9ea6))
* **reddit:** fetch deeply nested comments ([0a4a207](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/0a4a20751f2890dcb6aaa97b4f2ee0c9bd8acd58))
* **reddit:** fetch deeply nested comments that were silently dropped ([aa47181](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/aa47181176f8ff953ec61d91cc90a48d9b9a25e7))
* **reddit:** improve comment tree display with box-drawing indent characters ([bddecc4](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/bddecc4fae66b29eaed0c5dd78d6cafb1a090ca6))
* **reddit:** post get works with just ID, t3_ prefix, and includes parent_id ([#7](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/7)) ([4fdc8b9](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/4fdc8b9c5844190d602ccd4800b77c59dc252b9b))
