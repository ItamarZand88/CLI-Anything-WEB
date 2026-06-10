# CLI-Anything-Web — Deep Research & Refactoring Plan

**Date:** 2026-06-09
**Scope:** Full repository — the plugin (skills, commands, agents, scripts, templates), all 19 generated CLIs, and repo-level infrastructure.
**Goal:** Elevate the project several levels — to top-tier industry standard for a code-generation platform and CLI fleet.

---

## 0. Executive Summary

The repository today is a **working product with platform-shaped debt**. The 4-phase pipeline (capture → methodology → testing → standards) is sound, the security posture is excellent, and the generated CLIs are functional and consistent in spirit. But the project has grown from "a plugin that generates a CLI" into "a platform that maintains a fleet of 19 CLIs" — and the architecture has not made that jump.

The research surfaced six systemic findings:

| # | Finding | Evidence |
|---|---------|----------|
| 1 | **No shared runtime** — every CLI carries copy-pasted framework code | `repl_skin.py` ×7 copies (~2,190 lines, 1 already diverged); `_resolve_cli()`/test fixtures ×19 (~950 lines); retry/auth/error skeletons re-rendered into every CLI |
| 2 | **No fleet maintenance mechanism** — a fix to a shared pattern cannot propagate | 0 template-version metadata in generated files; older CLIs (hackernews) demonstrably out of sync with newer templates (capitoltrades) |
| 3 | **Plugin scripts are loose files, not a package** — ~6,300 LOC with sys.path hacks, dash-named un-importable modules, no shared data model for traffic entries, two parallel state systems, string-replace templating | `analyze-traffic.py` (1,221 lines), `validate-checklist.py` (658), `scaffold-cli.py` (514); every script repeats the same `sys.path.insert` boilerplate |
| 4 | **Instruction system shows scaling strain** — 3,800 lines of markdown with duplication, one real contradiction, an orphaned skill, and missing failure-recovery paths | Auth retry defined 3× with conflicting semantics ("retries once" vs "3-attempt"); `boilerplate/SKILL.md` is an 826-line template dump; `gap-analyzer` documented but never invoked |
| 5 | **No quality gates** — zero lint/format/typecheck anywhere in a 53,700-LOC Python monorepo | No `pyproject.toml`, no ruff/mypy/pre-commit, CI runs unit tests only, hardcoded 19-entry CI matrix, stale `scripts/test-all.sh` (covers 10 of 19 CLIs) |
| 6 | **Metadata drift** — registries, versions, and docs disagree | `registry.json` missing 2 CLIs; plugin.json `0.1.0` vs release `0.10.0`; CONTRIBUTING/QUICKSTART say "10 CLIs"; unused Handlebars templates (`README.md.template`, `SKILL.md.template`) are dead code |

The plan below is organized into **six pillars**, ordered by leverage. Pillars 1–2 are the architectural core ("the platform"); 3–4 harden the generation pipeline; 5 brings repo infrastructure to industry standard; 6 contains the product-level leaps that put this *several levels above* where it is now.

---

## Pillar 1 — `cli-web-core`: A Shared Runtime Library for the Fleet

**The single highest-leverage change in the repo.** Today every generated CLI vendors its own copy of framework code. The fix-once-fix-everywhere property does not exist.

### 1.1 Create the package

New top-level package, published like any CLI, installed as a dependency by every generated CLI:

```
cli-web-core/
├── pyproject.toml                 # name="cli-web-core", semver, py.typed
└── cli_web_core/
    ├── exceptions.py              # AppError base + AuthError/RateLimitError/NetworkError/
    │                              #   ServerError/NotFoundError/RPCError + to_dict() +
    │                              #   raise_for_status() + error-code mapping
    ├── client/
    │   ├── base.py                # BaseClient: 3-attempt auth retry, rate-limit backoff,
    │   │                          #   Retry-After handling, request hooks
    │   ├── rest_httpx.py          # httpx transport
    │   ├── rest_curl.py           # curl_cffi transport (impersonation)
    │   └── batchexecute.py        # Google RPC codec (encoder/decoder/anti-XSSI/chunks)
    ├── auth/
    │   ├── store.py               # auth.json load/save, chmod 600, env-var fallback,
    │   │                          #   list-vs-dict cookie format normalization
    │   ├── browser_login.py       # sync_playwright persistent-context login,
    │   │                          #   Windows event-loop fix, anti-automation args
    │   └── google_sso.py          # regional cookie priority (.google.com > ccTLD)
    ├── output.py                  # json_success/json_error, table rendering, Rich helpers
    ├── repl.py                    # the one true repl_skin (banner, dispatch, shlex,
    │                              #   --json propagation, TTY detection, help registry)
    ├── polling.py                 # poll_until_complete, exponential backoff
    ├── context.py                 # use <id> / status persistent-context helpers
    └── testing/
        ├── fixtures.py            # _resolve_cli, _run, _parse_json, CLI_WEB_FORCE_INSTALLED
        └── contract.py            # reusable contract assertions (see Pillar 4)
```

Generated CLIs collapse to **only domain code**: `client.py` (endpoint methods subclassing `BaseClient`), `models.py`, `commands/`, app-specific auth filtering, tests. A typical client goes from ~100 lines of vendored skeleton + endpoints to a 20-line subclass + endpoints.

### 1.2 Solve the REPL help-sync problem structurally

The current `_print_repl_help()` is hand-written per CLI and goes stale (documented as "REPL Bug #3"). In `cli_web_core.repl`, derive REPL help **from the Click command tree at runtime** (walk `cli.commands`, render names/params/help). The bug class disappears; delete the rule from three markdown files.

### 1.3 Migration strategy (low risk)

1. Ship `cli-web-core` 1.0 extracted from the **newest** CLI (capitoltrades — it matches current templates).
2. Update templates to import from core instead of vendoring.
3. Migrate CLIs in 3 waves (no-auth/read-only → cookie-auth → Google SSO/RPC), gated by each CLI's existing test suite plus the new contract tests.
4. Allow a documented local override (`cli_web/<app>/utils/repl_skin.py` shadowing) for any CLI with a justified divergence, recorded in its manifest (1.4).

### 1.4 Provenance manifest per CLI

`scaffold-cli.py` writes `.manifest.json` into every `agent-harness/`:

```json
{
  "generator": {"plugin_version": "0.10.0", "template_version": "1.0.0", "generated_at": "..."},
  "profile": {"protocol": "rest", "http_client": "curl_cffi", "auth": "cookie"},
  "core_version": ">=1.0,<2.0",
  "overrides": []
}
```

This is the key that unlocks fleet tooling: drift detection, batch re-sync, "which CLIs predate fix X".

---

## Pillar 2 — Promote Plugin Scripts to a Real Python Package (`cli_web_devkit`)

The ~6,300 LOC under `cli-anything-web-plugin/scripts/` is the deterministic brain of the pipeline. It deserves engineering parity with the code it generates.

### 2.1 Package structure & single entry point

```
cli-anything-web-plugin/devkit/
├── pyproject.toml                  # name="cli-web-devkit"; deps: pydantic, jinja2, click
└── cli_web_devkit/
    ├── __init__.py
    ├── cli.py                      # ONE entry point: `cli-web-devkit <subcommand>`
    ├── models/
    │   ├── traffic.py              # TrafficEntry, Capture (pydantic) — THE schema
    │   ├── analysis.py             # ProtocolInfo, AuthInfo, EndpointInfo
    │   ├── state.py                # PipelineState, Phase enum, CaptureCheckpoint
    │   └── manifest.py             # CLIManifest (Pillar 1.4) + registry entry schema
    ├── capture/                    # parse_trace, mitmproxy, validate_capture, fingerprint
    ├── analyze/                    # detectors/ (strategy classes: REST, GraphQL,
    │                               #   batchexecute, SSR, gRPC-Web…), auth, protections
    ├── scaffold/                   # Jinja2 engine + profile resolution
    ├── validate/                   # checklist registry, smoke test, gap analyzer
    ├── state/                      # pipeline + checkpoint persistence (one system)
    └── filters.yaml                # noise patterns / tracking cookies (config, not code)
```

Keep thin `scripts/*.py` shims for backward compatibility with skill instructions during transition, each just invoking the packaged CLI.

What this kills, concretely:
- **sys.path hacks** in every script (un-importable dash-named files → proper modules).
- **4 reinventions of the traffic-entry shape** (`parse-trace.py`, `analyze-traffic.py`, `validate-capture.py`, `mitmproxy-capture.py`) → one pydantic `TrafficEntry` with versioned schema; adding a field becomes a one-file change with validation.
- **Two unconnected state systems** (`phase-state.json` + `.capture-state.json`, no schema, no cross-references) → one `PipelineState` model with enums, validation, and migration support.
- **God functions**: `detect_protocol()` (270 lines, 11 protocols in one function) → registry of detector strategies, each independently unit-testable; `validate-checklist.py`'s monolithic Validator → declarative check registry (see 4.2).

### 2.2 Engineering standards inside the devkit

- Full type hints, `mypy --strict` clean; `py.typed` marker.
- `logging` with `--verbose`/`DEBUG=1` instead of bare stderr prints.
- Every JSON artifact the pipeline produces (`raw-traffic.json`, `traffic-analysis.json`, `phase-state.json`, `.manifest.json`, `registry.json`) gets a **published JSON Schema** under `devkit/schemas/`, validated on read *and* in CI. The pipeline's contracts become explicit instead of implicit dict shapes.
- Tests move from `importlib` file-loading hacks to normal imports; add `[tool.pytest.ini_options]`; target ≥85% coverage on the devkit (it's deterministic code — this is cheap).

### 2.3 Replace string-replace templating with Jinja2

Current `${name}`.replace() templating forces: two parallel auth templates, brittle anchor-based method injection (`anchor = "    def close(self):"`), four casing variables, and protocol logic living in Python instead of templates.

- Migrate `templates/*.tpl` → `templates/*.py.j2` with conditionals (`{% if auth_type == "google_sso" %}`), includes/inheritance for shared blocks, and filters for casing (`{{ app | pascal }}`).
- Merge `auth.py.tpl` + `auth_google_sso.py.tpl` into one template (or drop both — most of their bodies move into `cli-web-core` per Pillar 1, leaving a thin app-specific shim).
- Replace anchor-injection of `_graphql()`/`_parse_html()` with template blocks. Adding a new variant (e.g., camoufox hybrid) becomes a template, not surgery on `scaffold-cli.py`.
- **Delete or wire up the dead Handlebars templates** (`README.md.template`, `SKILL.md.template` are never invoked). Recommended: convert to Jinja2 and have scaffold actually generate README/SKILL skeletons — docs-from-day-one instead of hand-written.
- Add **command-module and test-file scaffolds** (`commands/resource.py.j2`, `test_e2e.py.j2` with the standard subprocess fixtures) — currently 0% templated, yet they follow a clear repeated pattern.

---

## Pillar 3 — Instruction System: Single Source of Truth + Machine-Checkable Gates

3,800 lines of markdown drive the agents. The architecture is right; the content needs consolidation and the deterministic parts need to move into the devkit.

### 3.1 One conventions spec, referenced everywhere

Create `skills/shared/CONVENTIONS.md` as the **only** place rules are *defined* (auth retry semantics, JSON error format, REPL rules, exception hierarchy, UTF-8 fix, shlex, naming). HARNESS.md, skills, and agents *link* to it. Immediately fixes the live contradiction: HARNESS says 3-attempt auth refresh, `boilerplate/SKILL.md:121` says "retries once", root CLAUDE.md says "retries once… never more". Pick the 3-attempt spec (it's what templates implement) and correct the other two.

### 3.2 Shrink the boilerplate skill from 826 → ~150 lines

It currently in-lines every template (a second, drift-prone copy of `templates/`). Rewrite as a procedural guide: "render `templates/X.py.j2` with these variables." Its 800-line "manual fallback" path is unrealistic for an agent anyway; the fallback should point to the newest generated CLI as a reference implementation.

### 3.3 Failure-recovery decision trees

Add explicit recovery paths for every hard gate (the audits found these missing): `tracing-stop` failure → retry budget → restart trace; `validate-capture` failure → map each validator gap to a targeted remediation ("<15 entries → capture more pages", "no WRITE op → perform a create/delete"); phase-state `failed` → retryable vs fatal handling. House them in `skills/shared/RECOVERY.md`.

### 3.4 Tier the 75-check checklist & fix the counts

Split into **Tier 1 Critical** (~30 checks; any failure blocks publish) and **Tier 2 Comprehensive**. Encode tiers in the devkit check registry (severity: critical/warning/info) so `validate-checklist` can fail-fast. Fix the "~65 of 75" vs "75-check" wording drift across HARNESS/standards.

### 3.5 De-overlap the review agents & resolve gap-analyzer

- Give the 3 Phase-4 reviewer agents explicit, non-overlapping scopes (JSON output is currently checked by two of them); state each agent's scope boundary in its frontmatter.
- `gap-analyzer` is a documented skill that nothing invokes (standards.md references it but doesn't dispatch it). Decide: integrate it as the automated entry step of `/refine` **and** implement its deterministic diff (captured endpoints vs implemented client methods vs documented commands) as `cli-web-devkit gaps` — its 4 manual checks are exactly the kind of prose-described logic that belongs in a script.

### 3.6 Progressive disclosure in references

Large references (`auth-strategies.md`, `playwright-cli-commands.md`) should be section-addressed ("read §Cookie domain priority") rather than "read the whole file" — lower context cost, higher instruction fidelity.

---

## Pillar 4 — A Real Quality System for Generated Code

### 4.1 Golden-file + generation tests for the scaffold

In devkit tests: scaffold a synthetic CLI for **every profile combination** (protocol × http_client × auth) and assert: all files `compile()`, exceptions expose `to_dict()`, setup metadata correct, no unresolved placeholders, output matches checked-in golden files. Any template change that alters output shows up as a reviewable golden diff. Run in CI on every PR touching `templates/` or `scaffold/`.

### 4.2 Fleet contract test suite

One parametrized suite at repo root, driven by `registry.json`, runs against every installed CLI:

- `--help` and `--version` exit 0
- every command accepts `--json`; output parses as JSON matching `{"success": true,...}` or `{"error": true, "code", "message"}` envelope (validated against a JSON Schema)
- errors in `--json` mode are JSON (not stderr text); exit codes mapped from exception types
- no protocol leaks (`wrb.fr`, `af.httprm`, bare `[]`/nulls)
- REPL launches and `help`/`exit` work under a pty

This converts the "Mandatory Smoke Check" prose into an executable gate and gives the fleet a regression net that doesn't require live-site auth.

### 4.3 Record/replay (VCR) tests to decouple CI from live sites

E2E tests currently hit live sites and hard-fail without auth — correct for local verification, but it means CI can never run them. Adopt the cassette pattern the testing skill already sketches: record sanitized fixtures during Phase 3 (the pipeline has real traffic on hand — capture doubles as cassette source), commit scrubbed cassettes, and run replay tests in CI. Keep live E2E as an explicitly-gated `-m live` tier.

### 4.4 Fleet drift detection & re-sync

- `cli-web-devkit drift` — compares every CLI's `.manifest.json` + framework-file hashes against current core/templates; reports out-of-date CLIs (would have caught hackernews's diverged repl_skin and pre-standardization exceptions.py automatically).
- `cli-web-devkit resync <app>` — re-renders framework-owned files for one CLI, preserving the domain layer; opens a reviewable diff. This, plus Pillar 1, is the answer to "how does a fix reach all 19 CLIs."
- Weekly scheduled CI job runs drift detection and the contract suite; opens an issue on regressions.

---

## Pillar 5 — Repo Infrastructure to Industry Standard

### 5.1 Tooling & quality gates (currently zero)

- Root `pyproject.toml`: `[tool.ruff]` (lint + format), `[tool.mypy]`, `[tool.pytest.ini_options]`, shared across the monorepo.
- `.pre-commit-config.yaml`: ruff check/format, mypy (start permissive, ratchet), end-of-file/trailing-whitespace, `check-json`/schema validation for `registry.json` and manifests.
- CI: add a lint/typecheck job that gates merge. New code strict; existing CLIs grandfathered with per-package ignores burned down over time.

### 5.2 Workspace & task runner

Adopt **uv workspaces** (members: `cli-web-core`, `devkit`, every `*/agent-harness`) so `uv sync` builds the whole fleet, with one lockfile for dev. Add a `justfile`/`Makefile`: `test-all`, `test <app>`, `lint`, `contract`, `drift`, `scaffold-smoke`. Delete the stale `scripts/test-all.sh` (it covers 10 of 19 CLIs).

### 5.3 CI/CD correctness

- **Dynamic test matrix** generated from `registry.json` (today it's a hand-maintained 19-entry list that must be edited per new CLI).
- Devkit test job (the plugin's own tests currently don't run in CI).
- Match CI Python versions to `python_requires` (test 3.10 *and* 3.12, or raise the floor — currently CLIs claim ≥3.10 but CI only proves 3.12).
- Coverage reporting (pytest-cov + Codecov badge).
- **PyPI trusted publishing**: on release-please tag, build and publish `cli-web-core` + changed CLIs. `pip install cli-web-hackernews` becoming real is a product-level upgrade (today the only install path is cloning the monorepo).
- Per-package release-please config (monorepo mode) → per-CLI versioning and changelogs; sync `.claude-plugin/plugin.json` version from the release manifest (currently 0.1.0 vs 0.10.0).

### 5.4 Metadata & docs as generated artifacts

- Make `registry.json` schema-validated and **the** source of truth; CI fails if a `*/agent-harness` exists without a registry entry (catches today's missing hackernews/youtube) or vice-versa.
- Generate the README CLI table, install commands, and counts from `registry.json` (`cli-web-devkit docs` + a CI freshness check). Fixes the "10 CLIs" staleness in CONTRIBUTING/QUICKSTART permanently instead of once.
- Move the 33 MB `assets/` (18 MB demo.gif) to Git LFS or a GitHub release/CDN; keep the repo clone light.
- Slim root `CLAUDE.md`: the per-CLI table and lessons-learned belong in `registry.json`/reference docs; CLAUDE.md should stay a compact, stable instruction set.

---

## Pillar 6 — Product-Level Leaps (what makes this "few levels above")

These build on Pillars 1–5 and change what the project *is*, not just how clean it is.

### 6.1 `api-spec.yaml` — a typed intermediate representation per CLI

Today the pipeline goes traffic → prose (`<APP>.md`) → hand-written code, and fidelity is enforced by a reviewer agent reading both sides. Introduce a machine-readable spec as the Phase-2 artifact:

```yaml
app: hackernews
protocol: rest
auth: {type: cookie, required_cookies: [user]}
endpoints:
  - id: search_stories
    method: GET
    url: https://hn.algolia.com/api/v1/search
    params: {query: {type: str}, tags: {type: str, optional: true}}
    response_model: SearchResult
    evidence: raw-traffic.json#entry-42      # provenance link to capture
commands:
  - name: search
    group: stories
    endpoint: search_stories
```

Payoffs compound: client method *stubs*, command skeletons, `<APP>.md`, REPL help, contract tests, and the gap analyzer all derive from the spec; traffic-fidelity review becomes a deterministic spec-vs-traffic diff; RPC-ID verification (the batchexecute foot-gun called out in CLAUDE.md) becomes a validation rule with provenance links instead of a warning paragraph. This is the single change that most increases generation correctness.

### 6.2 Fleet canary monitoring (self-healing CLIs)

Target sites change under you — the repo already documents "sites can add protection at any time." Add a scheduled CI canary: for each CLI, run 1–2 read-only commands (no-auth CLIs in CI directly; auth CLIs optionally via repo secrets), validate JSON envelopes, and auto-open a labeled issue (`site-breakage/<app>`) with the failure signature on regression. Combined with `/refine`, this closes the loop: the platform *detects* breakage instead of waiting for users. This is the difference between "generated 19 CLIs" and "operates 19 CLIs."

### 6.3 MCP server generation alongside each CLI

The CLIs are explicitly agent-native (`--json` everywhere). Generate, from the same `api-spec.yaml`, an optional MCP server entry point per app (`cli-web-<app> mcp-serve`) exposing each command as an MCP tool with a JSON schema derived from Click params. Near-zero marginal cost once 6.1 exists, and it makes every generated artifact consumable by *any* MCP client, not just shell-capable agents — a genuine category upgrade for the project.

### 6.4 Capture quality scoring & profile-aware pipeline

Extend `validate-capture` from pass/fail gates to a scored report (endpoint diversity, WRITE coverage, auth-flow completeness, body truncation rate) that the methodology skill uses to *plan* implementation scope — and that `/refine` uses to target re-capture. Wire site-profile detection (auth×CRUD matrix already in CLAUDE.md) into scaffold flags so profile decisions are data, not agent judgment.

### 6.5 Generated-CLI UX polish to flagship-CLI standard

Once core exists, these land fleet-wide in one place: shell completion (Click's native completion, advertised in README), `--output table|json|jsonl` (jsonl for piping into `jq`/agents), consistent exit-code contract (documented: 0 ok, 2 usage, 3 auth, 4 not-found, 5 rate-limit, 6 server), `NO_COLOR`/`CLICOLOR` respect, and a `doctor` command per CLI (checks auth file, connectivity, dependency versions) to cut support burden.

---

## Roadmap & Sequencing

| Phase | Status | Contents | Exit criteria |
|-------|--------|----------|---------------|
| **0 — Hygiene** | ✅ DONE | Fix auth-retry contradiction; sync registry.json (+ hackernews/youtube); plugin.json version sync (+ release-please extra-files); fix doc counts; make test-all.sh dynamic; assets → LFS (deferred — needs LFS quota decision) | All metadata mutually consistent; CI green |
| **1 — Foundations** | ✅ DONE | Root pyproject + ruff/mypy/pre-commit + CI gates; devkit packaging (registry/matrix/models); dynamic CI matrix; coverage | Devkit importable & typed; lint gate on; `TrafficEntry`/`PipelineState` schemas published |
| **2 — Core runtime** | ✅ DONE | `cli-web-core` 1.0; **vendoring-with-provenance** (not import-based — keeps `pip install -e <dir>` standalone until PyPI publishing is activated); repl_skin v2 canon synced to ALL 19 CLIs (not just 3); `.manifest.json` fleet-wide; contract test suite | Whole fleet on canon; contract suite green fleet-wide |
| **3 — Generation v2** | ✅ DONE | Jinja2 migration (`${}` delimiters, StrictUndefined); unified auth.py.tpl; command/e2e/README/SKILL scaffolds; 21-profile golden tests; boilerplate skill 829→106; CONVENTIONS.md + RECOVERY.md; tiered checklist (38 T1) in validate-checklist; gap-analyzer integrated into /refine | Scaffold any profile end-to-end on v2; golden tests in CI |
| **4 — Fleet ops** | ✅ DONE | drift/resync tooling; daily canary workflow (12 CLIs, auto-files `site-breakage` issues); contract+drift CI workflow; release-please manifest mode (core+devkit packages, per-package changelogs); PyPI trusted-publishing workflow (needs one-time PyPI setup — docs/PUBLISHING.md); VCR cassettes deferred to per-CLI regeneration | Drift zero; canary live; publish pipeline ready |
| **5 — Product leaps** | ✅ DONE | `api-spec.json` IR (validator + evidence-required schema, wired into methodology + gap analysis); **MCP serve fleet-wide** (every CLI is an MCP server; contract-tested ×19); **doctor fleet-wide** (self-diagnosis, contract-tested ×19); capture quality scoring in validate-capture; numeric exit-code contract + `--jsonl` list output (core API + templates v2.1 — new CLIs adopt automatically; existing fleet keeps historical exit codes until a coordinated major, per CONVENTIONS.md §Exit Codes) | Spec validator shipping; MCP + doctor live on all 19 |

**Implementation notes (deviations from the original plan):**
- **Vendoring instead of import-dependency (Pillar 1):** making 19 CLIs depend on an unpublished `cli-web-core` would break `pip install -e <dir>` for users. Until PyPI publishing is activated, core is the canonical *source* and `cli-web-devkit resync` keeps byte-identical vendored copies with sha256 provenance in each CLI's `.manifest.json`. Fix-once-propagate-everywhere holds either way.
- **`api-spec.json` not `.yaml`:** devkit is intentionally zero-dependency (runs in pre-commit/CI bare); JSON keeps it stdlib-parseable and the file is machine-written anyway.
- **Handlebars templates were not dead:** they were referenced by standards/SKILL.md as manual starting points; they are now real Jinja2 templates (`README.md.tpl`, `SKILL.md.tpl`) rendered by scaffold v2.

---

## Appendix A — Defect/Drift Inventory (fix-list)

1. `boilerplate/SKILL.md:121` "retries once" vs HARNESS.md 3-attempt spec vs root CLAUDE.md "never more" — contradiction.
2. `registry.json` missing `cli-web-hackernews`, `cli-web-youtube` (17/19).
3. `.claude-plugin/plugin.json` version 0.1.0 vs release 0.10.0.
4. `templates/README.md.template`, `templates/SKILL.md.template` — never invoked by `scaffold-cli.py` (Handlebars syntax, incompatible with its `${}` renderer); referenced only as manual starting points in `standards/SKILL.md:287,294`. Keep until Pillar 2.3 converts them to Jinja2 and wires them into scaffold.
5. `scripts/test-all.sh` (repo root) — covers 10 of 19 CLIs.
6. CONTRIBUTING.md:20 / QUICKSTART.md — "10 CLIs" (actual: 19).
7. `hackernews` repl_skin.py diverged from the other 6 identical copies; its exceptions.py predates template standardization (no `raise_for_status`, generic `AppError` base).
8. HARNESS.md:192 "~65 of the 75" vs standards "75-check" — wording drift; encode tiers instead.
9. `gap-analyzer` skill referenced in standards.md but never dispatched.
10. 3 CLIs lack per-CLI `skills/SKILL.md` (16/19 present).
11. `setup.py` deps unpinned upper bounds (`curl_cffi` fully unpinned) — supply-chain/breakage risk ×19.
12. CI Python 3.12-only vs `python_requires=">=3.10"`; `mitmproxy-capture.py` requires 3.12+ undeclared.
13. RPC decoder template public-function naming vs generated private naming (codewiki) — pick one convention.
14. `config.py` location inconsistent across CLIs (`utils/` vs `core/`).
15. 33 MB `assets/` committed directly (18 MB GIF) — LFS/CDN candidate.

## Appendix B — Quantitative Baseline (for measuring the refactor)

- 19 generated CLIs; ~53,700 LOC Python in CLIs; ~6,300 LOC in plugin scripts; ~3,800 lines instruction markdown; 1,636 LOC templates.
- True duplication: ~2,190 LOC (repl_skin ×7) + ~950 LOC (test fixtures ×19) + framework skeletons re-rendered per CLI.
- Expected reduction from Pillars 1–2: ~4,000–5,000 LOC removed; more importantly, framework changes go from **O(19) manual edits → O(1) release**.
- Targets post-refactor: devkit coverage ≥85%; contract suite green fleet-wide in CI; drift report empty; zero hand-maintained CLI lists anywhere (matrix, docs, registry all derived).
