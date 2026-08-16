# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.14.3](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.14.2...v0.14.3) (2026-08-16)


### Bug Fixes

* **docs:** sync public installs and registry site ([#52](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/52)) ([23e17d9](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/23e17d942c6934ec7d9576f620cc476d3ed12686))

## [0.14.2](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.14.1...v0.14.2) (2026-08-16)


### Bug Fixes

* harden fleet maintenance and live read commands ([#50](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/50)) ([dd1107a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/dd1107a07de11809befae8ecbb975f06022d13f9))

## [Unreleased]

### Fixed

* enforce structured JSON envelopes, parse errors, and canonical auth exit codes across the fleet
* verify browser payloads in `doctor` instead of reporting false-green GAI, Unsplash, and FUTBIN setups
* restore live FUTBIN and World Cup reads with browser-compatible transports
* bound and complete NotebookLM, Reddit, and Stitch authentication refresh flows
* expose captured Hacker News, Pexels, Stitch, Unsplash, and World Cup read endpoints
* repair LinkedIn company routing and Pexels search-to-detail slug round trips
* improve Product Hunt post extraction and remove its non-functional period option
* prevent GAI from returning successful empty answers and classify CAPTCHA blocks explicitly
* bootstrap and cache Camoufox before the Unsplash live canary
* add browser-aware canaries, strict fleet validation, subprocess E2E checks, and an enforced coverage floor
* register the fleet's `unit` pytest marker and refresh maintenance tooling
* correct the plugin repository metadata and publishing instructions

### Security

* pin third-party GitHub Actions to reviewed immutable revisions
* add Dependabot coverage for Actions, pre-commit, and every Python package
* add weekly CodeQL analysis using the security-extended query suite

## [0.14.1](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.14.0...v0.14.1) (2026-06-21)


### Bug Fixes

* **reddit:** route reads through OAuth API and clarify auth-required error ([#45](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/45)) ([03b9c86](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/03b9c868fcc8b4b5f2be1a33cc70e6e0928f5c09))

## [0.14.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.13.1...v0.14.0) (2026-06-20)


### Features

* add capitoltrades CLI to monorepo ([473c8af](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/473c8af6b9f000f08c506294ad0658652367cd09))
* add cli-web-airbnb, cli-web-amazon, cli-web-tripadvisor (17 CLIs total) ([736da77](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/736da77bf7c6b3db86090c07a71be62e914b90f4))
* add cli-web-capitoltrades (US congressional stock trades) ([d1b2e18](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/d1b2e181014185e2c1ec6be668b86ec75b040275))
* add cli-web-hackernews — browse, search, and interact with Hacker News ([7dcd17a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/7dcd17aa8625d2dec503ac604d64e87d177cd07d))
* add cli-web-worldcup — FIFA World Cup 2026 CLI (ESPN + Odds API) ([fe488b2](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/fe488b29b3bad0c6201ec15efd02564be663eae5))
* add cli-web-worldcup — FIFA World Cup 2026 CLI (ESPN + Odds API) ([cf3b38d](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/cf3b38da0bd8a75bcfb84f3e4579c0d9c22aa0ea))
* add cli-web-youtube — search, video details, trending, channels ([9ee1f63](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/9ee1f637d10451074b363ca1af1aeb6781af1851))
* add mitmproxy-based traffic capture (opt-in --mitmproxy flag) ([3867e02](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3867e02524de5c1b877a5520d7690d9e900a79a6))
* add mitmproxy-based traffic capture and enhanced traffic analysis ([9857f99](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/9857f996702db448dd76ce78834a1d27f25a4ae7))
* add pipeline automation scripts and boilerplate templates ([e0e4cc4](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/e0e4cc44811392fae358f901e93e445d69e06a2f))
* add pipeline automation scripts and boilerplate templates ([a7ca2ae](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/a7ca2aeaa8fc8e0b056b12fbad719c8ad32cb2b6))
* add plugin agents, skills, and reddit newline fix ([32e024f](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/32e024f0d9d24dc02af179321d142a20ddf92f9c))
* **capture:** harden Phase 1 with output validation + anti-bot ladder ([00c457f](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/00c457fbabaab6e06dd6279844ac47ba7ec6ec29))
* **chatgpt:** add cli-web-chatgpt — 14th CLI ([5f4b626](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5f4b626a65f48e96689e47035facf45634bb5832))
* **chatgpt:** add cli-web-chatgpt — 14th CLI for ChatGPT ([2d4a353](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/2d4a353985b521c6458b7f2d4bae2141e93949e0))
* **codewiki:** add CLI for Google Code Wiki with Gemini chat ([bab05a9](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/bab05a9935e886f6d482d491522cd7149d04a55b))
* **codewiki:** add CLI for Google Code Wiki with Gemini chat ([66a291a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/66a291add8024b046b48b85cb98c15afe6f1da7f))
* **devkit:** keep the GitHub About CLI count in sync with the fleet ([ded200a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ded200af9dcba23dbd4dc9cce1e22a608bf52fc9))
* **devkit:** keep the GitHub About CLI count in sync with the fleet ([b9d8352](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b9d8352fdd97026526fe08c536fd862017152141))
* fleet-wide doctor command (self-diagnosis) via vendored core module ([5c2f403](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5c2f4032b1da6d4d12f8aeb04899c373e953c363))
* **futbin:** add market analysis, arbitrage, scan, versions commands + trading knowledge base ([45aba74](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/45aba749a8054e7b5c8f34bf05cd962750d7a735))
* **futbin:** market trading commands, price history, and fix player scraping ([#8](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/8)) ([5e547ba](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5e547ba1dcd725da179f8bfcf6b4f20906610dea))
* **gh-trending:** show the repo URL as a Link column in repos list ([e8db02c](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/e8db02c108c2ee4e6cfa939d34918d85862bfe47))
* **linkedin:** add cli-web-linkedin with 24 commands (pre-review baseline) ([4f81e16](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/4f81e16ca4495298c114d2a3cab701bd2c08a248))
* **linkedin:** fix all gap analysis issues + rewrite docs ([21ae754](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/21ae754a010c6a419bd683972d1aed0d31b94709))
* numeric exit-code contract and --jsonl output for generated CLIs ([3663bda](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3663bda4be0115c9fac7db61c5ea114d78d12254))
* Phase 1+2 — quality gates, cli-web-devkit, cli-web-core, fleet sync ([bbb6a88](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/bbb6a88276cdd1095665b56e900cb061bb529b35))
* Phases 3-5 — generation v2, fleet ops, api-spec IR, MCP serve fleet-wide ([61caad1](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/61caad16cb7915c440967cfee367f9ca99b64557))
* **plugin:** add 3 review agents, replace review-agents.md reference ([c1466bd](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/c1466bd4a23174e9f7de7f6edd1a89eb0052b11e))
* **plugin:** add boilerplate generator skill for core/ scaffolding ([d9851a8](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/d9851a8eec05c1327c8467a740e2a0198793263e))
* **plugin:** add cross-CLI consistency checker agent ([ab20302](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ab20302cd5f4c6b5d311d40c63bba1dd7963f11e))
* **plugin:** add gap analyzer skill for structured refine workflow ([2b7b6e3](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/2b7b6e39b63fdb1c9356a7116a4fe6f4e5fcba1b))
* **plugin:** add review agents, boilerplate skill, consistency checker, gap analyzer + fix reddit newline escape ([ed665b9](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ed665b929196f9551e0623b9c067915648b3379c))
* publish the CLI fleet to PyPI (per-CLI + umbrella) ([59ca9f6](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/59ca9f67ac99829370a6f679385fd1cf2186740c))
* refactor all 26 skills to Anthropic skill-authoring best practices ([7294199](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/729419967e8fd6e180b9d3e17a665da5340e782b))
* refactor pipeline skill content to authoring/prompting best practices ([6170131](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/6170131dca335753d286d37761f2776467ece43f))
* shared runtime (cli-web-core), fleet devkit, and repo-wide quality gates ([2932dc2](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/2932dc23bbb58cc1f36982c1abb9f8fc1de147be))
* **youtube:** add transcript fetching (timestamped, multi-language, translatable) ([#40](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/40)) ([95d0381](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/95d0381513661cae3999fea202de73517928a09c))


### Bug Fixes

* add youtube + hackernews to CI test matrix, add CI step to Phase 4 ([59ddc63](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/59ddc6398f4e7c867ec4a734096d614c54bd6088))
* address code review findings on PR [#21](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/21) ([f78ed53](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/f78ed5300121df3c006fc19adfa04dc8661561f7))
* address code-review findings in shared runtime, pipeline, and quality gate ([06988a0](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/06988a0266db671c58077379834febdccf65205d))
* **airbnb,tripadvisor:** apply {success,data} envelope to all commands ([ce4352b](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ce4352becb946dea421b6a0f66098309b6d95c39))
* **airbnb,tripadvisor:** wrap --json output in the {success,data} envelope ([b2c157c](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b2c157c81cdc6337acd1263b425b962be5d4b236))
* **amazon:** use curl_cffi to bypass the 503 bot block ([ba68f29](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ba68f290099280ccaccde01558850190f4c29caf))
* **canary:** classify anti-bot blocks vs real breakage; relax envelope check ([e75893b](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/e75893b6749e05136390bc17320b69db49b954e7))
* **chatgpt:** add --json flag to all subcommands for consistency ([824c48d](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/824c48def26068d44647dd08e0d011e3a6a6115f))
* **ci:** give publish-backfill access to the PyPI token ([63b1fb0](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/63b1fb0060d440c377a6f7e5eb82651f5225f049))
* **ci:** install jinja2/click for plugin job, run core tests, decouple doctor tests ([3bb1177](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3bb1177c348a1b8fbb8771dee01e624ab0738c04))
* **ci:** stop Release Please tests from checking out deleted branch ([383779c](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/383779c95f99941582020242e2bcd4aa64736fc4))
* **devkit:** parametrize CompletedProcess[str] in about.py for mypy ([80a0c83](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/80a0c835195008063932d40de67dd3ae07e3e68b))
* eliminate all remaining fleet and tooling bugs from the review ([b70aa65](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b70aa65007292655ac65b4797145302029c09181))
* **linkedin:** address all code review findings + sync all docs ([813c5e0](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/813c5e066c2038d05ad65738156ec6c8129f6741))
* **linkedin:** anti-bot hardening and code review fixes ([3b0015c](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3b0015cae91f22e1f56e10217129a1b5907c99ba))
* **linkedin:** anti-bot hardening from security audit ([96aa037](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/96aa037ff499be5d49d7201d55fa8bff54f784cb))
* **linkedin:** fix profile display + add REPL inter-command delay ([b04cde8](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b04cde840ff7c085ea72cfbd27984ef17473b580))
* **linkedin:** resolve empty data and wire up dead code ([3479da1](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3479da127b91b7fa8fa82220cf30e49365a219b1))
* **linkedin:** resolve REST.li pointers and fix search queryId ([6e8e5da](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/6e8e5da12624f711732ddbbe0429c6f25f1a4190))
* make setup.sh executable and add context manager + auth retry to hackernews client ([6c00a4b](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/6c00a4b2e22dcdf6e0224036919eefc81f2e3376))
* **plugin:** address review findings across new agents and skills ([614fe4c](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/614fe4c135511a3373d713b07742b75235c3e7a9))
* **plugin:** address review findings from 3-agent review ([4fd14b3](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/4fd14b3d05b9a81c4cfbc178af484b1738626bf9))
* **plugin:** revert curl_cffi except narrowing — keep broad catch ([a8d0adc](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/a8d0adcf4f609ce505b01ca9662d0863484be78b))
* **producthunt:** parse posts from the Next.js RSC flight stream ([b5170da](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b5170da1df25af9db847b0d4b08dac4129e82ebd))
* **reddit:** auto-refresh token_v2 on expiry + fix 403 misreported as AUTH_EXPIRED ([e56c3ea](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/e56c3ead10e4684486a860c096f86083216a9ea6))
* **reddit:** fetch deeply nested comments ([0a4a207](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/0a4a20751f2890dcb6aaa97b4f2ee0c9bd8acd58))
* **reddit:** fetch deeply nested comments that were silently dropped ([aa47181](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/aa47181176f8ff953ec61d91cc90a48d9b9a25e7))
* **reddit:** improve comment tree display with box-drawing indent characters ([bddecc4](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/bddecc4fae66b29eaed0c5dd78d6cafb1a090ca6))
* **reddit:** post get works with just ID, t3_ prefix, and includes parent_id ([#7](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/7)) ([4fdc8b9](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/4fdc8b9c5844190d602ccd4800b77c59dc252b9b))
* **registry:** update CLI count from 12 to 13 ([5b060e5](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5b060e59f4405d54cabf26a257b6829747f0d56e))
* **scaffold:** wire _refresh_tokens into batchexecute client on 401/403 ([8dd2673](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/8dd2673349b548c8f96dda07304baf96f1aca411))
* **unsplash:** bypass Anubis PoW via camoufox browser transport ([7d1d7f4](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/7d1d7f491d827b9b09b3042fbf69fdd2af78e686))
* wire new scripts into commands and verify-plugin.sh ([b3a3e7f](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b3a3e7f34b5ad73b5ff2e7777af374d44cff2975))
* **worldcup:** populate match venue and drop empty-provider odds colon ([b7df51f](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b7df51fc563b9a2882f98da9cd5954b184c20b39))
* **worldcup:** populate match venue and drop empty-provider odds colon ([64344cd](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/64344cdeb69c8fc3534aa2b47756f06e96791036))
* **youtube:** make transcript fetching actually work (ANDROID client + json3) ([40c6b6d](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/40c6b6d26a7660604fbc8a1dfa2d78c2dd5eb318))


### Documentation

* add auth login instructions to CLIs that require or support it ([a04624f](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/a04624f7ede347adee4d0707ac9d8521d87be3c6))
* add camoufox to tech stack, update plugin pipeline ([843d0e6](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/843d0e6c2a1126ab0e1890dc48ff448e540844e3))
* add CHANGELOG.md following Keep a Changelog format ([aa345a8](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/aa345a89600c519c93c9e6df62a40ca0b00b12a5))
* add cli-web-linkedin to main README (18 CLIs) ([9c1c0d0](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/9c1c0d046fbe1754dd449573b82f520d4ca10c2f))
* add codewiki CLI to README examples table and badges ([db47842](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/db47842842063e83f5e55f6cca9938323c9e5c28))
* add codewiki to registry HTML page ([5e6baeb](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5e6baeb8da61368aed02fa26c74ddb7fe63917bb))
* add deep-research refactoring plan for plugin, fleet, and infrastructure ([be2f198](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/be2f1984a9be1b91fda243b0d7d20253ae6a127d))
* add pipeline automation scripts to HARNESS.md and CLAUDE.md ([15c844a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/15c844abb653c2a141c7e0444450a53c766692f5))
* **chatgpt:** sync all docs to reflect --json at subcommand level ([75265be](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/75265be0a758d9e9c569f2bb427d00048e73bc00))
* improve README examples section ([37c2e65](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/37c2e65491832e291e58d01c3563480a5622090f))
* integrate mitmproxy capture as opt-in --mitmproxy flag ([f1225e4](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/f1225e4461b52b1b2f36001c71103bd71376faef))
* mark roadmap Phase 5 complete (doctor shipped) ([5fd0a69](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5fd0a69de10e60a45deb6eacc06a1e58d176deca))
* **readme:** add codewiki to project structure tree ([d7ecd3a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/d7ecd3a1cc5ff98024c8efc84758e80eb5ff8610))
* regenerate hackernews TEST.md via generate-test-docs.py ([9487776](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/9487776afd3c125be45388f07d603b8f99296161))
* separate each CLI into its own code block in examples section ([3f7b76d](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3f7b76d83cac4661d6edc8b90f4620b658bd6c8b))
* sync skills/docs with the new unsplash/producthunt/amazon transports ([3de348a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3de348a7f853e0ef6b20264581007a2526a1c09d))
* update README, CHANGELOG, registry for 12 CLIs (Hacker News added) ([c695cf9](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/c695cf9cb4f1467905401eec18219e649a5f2276))
* update README, CLAUDE.md, registry for 11 CLIs (YouTube added) ([a0fdb28](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/a0fdb285288b01d2664a1f77e143222c3b1d973f))

## [0.13.1](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.13.0...v0.13.1) (2026-06-15)


### Bug Fixes

* **ci:** give publish-backfill access to the PyPI token ([63b1fb0](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/63b1fb0060d440c377a6f7e5eb82651f5225f049))

## [0.13.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.12.1...v0.13.0) (2026-06-14)


### Features

* **gh-trending:** show the repo URL as a Link column in repos list ([e8db02c](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/e8db02c108c2ee4e6cfa939d34918d85862bfe47))

## [0.12.1](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.12.0...v0.12.1) (2026-06-14)


### Bug Fixes

* **airbnb,tripadvisor:** apply {success,data} envelope to all commands ([ce4352b](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ce4352becb946dea421b6a0f66098309b6d95c39))
* **airbnb,tripadvisor:** wrap --json output in the {success,data} envelope ([b2c157c](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b2c157c81cdc6337acd1263b425b962be5d4b236))
* **amazon:** use curl_cffi to bypass the 503 bot block ([ba68f29](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ba68f290099280ccaccde01558850190f4c29caf))
* **producthunt:** parse posts from the Next.js RSC flight stream ([b5170da](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b5170da1df25af9db847b0d4b08dac4129e82ebd))
* **unsplash:** bypass Anubis PoW via camoufox browser transport ([7d1d7f4](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/7d1d7f491d827b9b09b3042fbf69fdd2af78e686))


### Documentation

* sync skills/docs with the new unsplash/producthunt/amazon transports ([3de348a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3de348a7f853e0ef6b20264581007a2526a1c09d))

## [0.12.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.11.0...v0.12.0) (2026-06-14)


### Features

* add cli-web-worldcup — FIFA World Cup 2026 CLI (ESPN + Odds API) ([fe488b2](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/fe488b29b3bad0c6201ec15efd02564be663eae5))
* add cli-web-worldcup — FIFA World Cup 2026 CLI (ESPN + Odds API) ([cf3b38d](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/cf3b38da0bd8a75bcfb84f3e4579c0d9c22aa0ea))
* **devkit:** keep the GitHub About CLI count in sync with the fleet ([ded200a](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/ded200af9dcba23dbd4dc9cce1e22a608bf52fc9))
* **devkit:** keep the GitHub About CLI count in sync with the fleet ([b9d8352](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b9d8352fdd97026526fe08c536fd862017152141))
* publish the CLI fleet to PyPI (per-CLI + umbrella) ([59ca9f6](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/59ca9f67ac99829370a6f679385fd1cf2186740c))


### Bug Fixes

* **devkit:** parametrize CompletedProcess[str] in about.py for mypy ([80a0c83](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/80a0c835195008063932d40de67dd3ae07e3e68b))
* **worldcup:** populate match venue and drop empty-provider odds colon ([b7df51f](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b7df51fc563b9a2882f98da9cd5954b184c20b39))
* **worldcup:** populate match venue and drop empty-provider odds colon ([64344cd](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/64344cdeb69c8fc3534aa2b47756f06e96791036))

## [0.11.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.10.0...v0.11.0) (2026-06-10)


### Features

* fleet-wide doctor command (self-diagnosis) via vendored core module ([5c2f403](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5c2f4032b1da6d4d12f8aeb04899c373e953c363))
* numeric exit-code contract and --jsonl output for generated CLIs ([3663bda](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3663bda4be0115c9fac7db61c5ea114d78d12254))
* Phase 1+2 — quality gates, cli-web-devkit, cli-web-core, fleet sync ([bbb6a88](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/bbb6a88276cdd1095665b56e900cb061bb529b35))
* Phases 3-5 — generation v2, fleet ops, api-spec IR, MCP serve fleet-wide ([61caad1](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/61caad16cb7915c440967cfee367f9ca99b64557))
* refactor all 26 skills to Anthropic skill-authoring best practices ([7294199](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/729419967e8fd6e180b9d3e17a665da5340e782b))
* refactor pipeline skill content to authoring/prompting best practices ([6170131](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/6170131dca335753d286d37761f2776467ece43f))
* shared runtime (cli-web-core), fleet devkit, and repo-wide quality gates ([2932dc2](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/2932dc23bbb58cc1f36982c1abb9f8fc1de147be))


### Bug Fixes

* address code-review findings in shared runtime, pipeline, and quality gate ([06988a0](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/06988a0266db671c58077379834febdccf65205d))
* **ci:** install jinja2/click for plugin job, run core tests, decouple doctor tests ([3bb1177](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3bb1177c348a1b8fbb8771dee01e624ab0738c04))
* eliminate all remaining fleet and tooling bugs from the review ([b70aa65](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b70aa65007292655ac65b4797145302029c09181))


### Documentation

* add deep-research refactoring plan for plugin, fleet, and infrastructure ([be2f198](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/be2f1984a9be1b91fda243b0d7d20253ae6a127d))
* mark roadmap Phase 5 complete (doctor shipped) ([5fd0a69](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/5fd0a69de10e60a45deb6eacc06a1e58d176deca))

## [0.10.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.9.0...v0.10.0) (2026-04-24)


### Features

* add capitoltrades CLI to monorepo ([473c8af](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/473c8af6b9f000f08c506294ad0658652367cd09))


### Bug Fixes

* **ci:** stop Release Please tests from checking out deleted branch ([383779c](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/383779c95f99941582020242e2bcd4aa64736fc4))

## [0.9.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.8.0...v0.9.0) (2026-04-24)


### Features

* add cli-web-capitoltrades (US congressional stock trades) ([d1b2e18](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/d1b2e181014185e2c1ec6be668b86ec75b040275))
* **linkedin:** add cli-web-linkedin with 24 commands (pre-review baseline) ([4f81e16](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/4f81e16ca4495298c114d2a3cab701bd2c08a248))
* **linkedin:** fix all gap analysis issues + rewrite docs ([21ae754](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/21ae754a010c6a419bd683972d1aed0d31b94709))


### Bug Fixes

* **linkedin:** address all code review findings + sync all docs ([813c5e0](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/813c5e066c2038d05ad65738156ec6c8129f6741))
* **linkedin:** anti-bot hardening and code review fixes ([3b0015c](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3b0015cae91f22e1f56e10217129a1b5907c99ba))
* **linkedin:** anti-bot hardening from security audit ([96aa037](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/96aa037ff499be5d49d7201d55fa8bff54f784cb))
* **linkedin:** fix profile display + add REPL inter-command delay ([b04cde8](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b04cde840ff7c085ea72cfbd27984ef17473b580))
* **linkedin:** resolve empty data and wire up dead code ([3479da1](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/3479da127b91b7fa8fa82220cf30e49365a219b1))
* **linkedin:** resolve REST.li pointers and fix search queryId ([6e8e5da](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/6e8e5da12624f711732ddbbe0429c6f25f1a4190))

## [Unreleased]

### Added

- **cli-web-capitoltrades**: US Congressional stock trades CLI for capitoltrades.com (by 2iQ Research). Covers ~35K STOCK Act disclosures, 200+ politicians, 3K+ issuers. Commands: `trades list/get/by-ticker/stats`, `politicians list/top/get`, `issuers list/get/search`, `articles/buzz/press list/get`. No auth required. CloudFront bypass via curl_cffi Chrome136 impersonation. Rich issuer data including 1-year price history from BFF JSON API.

## [0.8.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.7.0...v0.8.0) (2026-04-06)


### Features

* add pipeline automation scripts and boilerplate templates ([e0e4cc4](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/e0e4cc44811392fae358f901e93e445d69e06a2f))
* add pipeline automation scripts and boilerplate templates ([a7ca2ae](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/a7ca2aeaa8fc8e0b056b12fbad719c8ad32cb2b6))


### Bug Fixes

* address code review findings on PR [#21](https://github.com/ItamarZand88/CLI-Anything-WEB/issues/21) ([f78ed53](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/f78ed5300121df3c006fc19adfa04dc8661561f7))
* make setup.sh executable and add context manager + auth retry to hackernews client ([6c00a4b](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/6c00a4b2e22dcdf6e0224036919eefc81f2e3376))
* **reddit:** auto-refresh token_v2 on expiry + fix 403 misreported as AUTH_EXPIRED ([e56c3ea](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/e56c3ead10e4684486a860c096f86083216a9ea6))
* wire new scripts into commands and verify-plugin.sh ([b3a3e7f](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/b3a3e7f34b5ad73b5ff2e7777af374d44cff2975))

## [0.7.0](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.6.2...v0.7.0) (2026-04-05)


### Features

* add cli-web-airbnb, cli-web-amazon, cli-web-tripadvisor (17 CLIs total) ([736da77](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/736da77bf7c6b3db86090c07a71be62e914b90f4))

## [0.7.0] — 2026-04-05

### Added

- **cli-web-airbnb**: Airbnb stays search, listing details, guest reviews, availability calendars, and location autocomplete (no-auth, SSR HTML + niobeClientData, curl_cffi Akamai/DataDome bypass)
- **cli-web-amazon**: Amazon product search, bestsellers, suggest, and product detail (SSR HTML + REST JSON, no auth required — public endpoints only)
- **cli-web-tripadvisor**: TripAdvisor location search, hotels, restaurants, and attractions search + detail (no-auth, SSR HTML + JSON-LD, DataDome bypass via curl_cffi)

### Removed

- **cli-web-amazon**: Removed auth system (login/status/logout commands, cookie management, auth retry) — all implemented commands use public Amazon endpoints that require no authentication

## [0.6.2](https://github.com/ItamarZand88/CLI-Anything-WEB/compare/v0.6.1...v0.6.2) (2026-04-01)


### Bug Fixes

* **chatgpt:** add --json flag to all subcommands for consistency ([824c48d](https://github.com/ItamarZand88/CLI-Anything-WEB/commit/824c48def26068d44647dd08e0d011e3a6a6115f))

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
- **cli-web-tripadvisor** — Search TripAdvisor locations, hotels, restaurants, and attractions. No auth required. Bypasses DataDome bot protection via curl_cffi Safari iOS impersonation. Extracts data from SSR HTML JSON-LD (schema.org).
- **cli-web-airbnb** — 15th CLI. Search Airbnb stays by location, dates, guests, and filters; get full listing details (rating, host, amenities, description); autocomplete location names. No auth required. Bypasses Akamai/DataDome bot protection via curl_cffi Chrome impersonation. Extracts data from SSR HTML niobeClientData (inline GraphQL). 71 tests (51 unit + 20 E2E).
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
