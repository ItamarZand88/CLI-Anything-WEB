# Changelog

## [0.3.2](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/cli-web-devkit-v0.3.1...cli-web-devkit-v0.3.2) (2026-08-16)


### Bug Fixes

* harden fleet maintenance and live read commands ([#50](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/50)) ([dd1107a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/dd1107a07de11809befae8ecbb975f06022d13f9))

## [0.3.1](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/cli-web-devkit-v0.3.0...cli-web-devkit-v0.3.1) (2026-06-20)


### Bug Fixes

* **canary:** classify anti-bot blocks vs real breakage; relax envelope check ([e75893b](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/e75893b6749e05136390bc17320b69db49b954e7))

## [0.3.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/cli-web-devkit-v0.2.0...cli-web-devkit-v0.3.0) (2026-06-14)


### Features

* **devkit:** keep the GitHub About CLI count in sync with the fleet ([ded200a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ded200af9dcba23dbd4dc9cce1e22a608bf52fc9))
* **devkit:** keep the GitHub About CLI count in sync with the fleet ([b9d8352](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b9d8352fdd97026526fe08c536fd862017152141))
* publish the CLI fleet to PyPI (per-CLI + umbrella) ([59ca9f6](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/59ca9f67ac99829370a6f679385fd1cf2186740c))


### Bug Fixes

* **devkit:** parametrize CompletedProcess[str] in about.py for mypy ([80a0c83](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/80a0c835195008063932d40de67dd3ae07e3e68b))

## [0.2.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/cli-web-devkit-v0.1.0...cli-web-devkit-v0.2.0) (2026-06-10)


### Features

* fleet-wide doctor command (self-diagnosis) via vendored core module ([5c2f403](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5c2f4032b1da6d4d12f8aeb04899c373e953c363))
* Phase 1+2 — quality gates, cli-web-devkit, cli-web-core, fleet sync ([bbb6a88](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/bbb6a88276cdd1095665b56e900cb061bb529b35))
* Phases 3-5 — generation v2, fleet ops, api-spec IR, MCP serve fleet-wide ([61caad1](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/61caad16cb7915c440967cfee367f9ca99b64557))
* refactor pipeline skill content to authoring/prompting best practices ([6170131](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/6170131dca335753d286d37761f2776467ece43f))
* shared runtime (cli-web-core), fleet devkit, and repo-wide quality gates ([2932dc2](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/2932dc23bbb58cc1f36982c1abb9f8fc1de147be))


### Bug Fixes

* address code-review findings in shared runtime, pipeline, and quality gate ([06988a0](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/06988a0266db671c58077379834febdccf65205d))
* eliminate all remaining fleet and tooling bugs from the review ([b70aa65](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b70aa65007292655ac65b4797145302029c09181))
