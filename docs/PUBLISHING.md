# Publishing `cli-web-core` and `cli-web-devkit` to PyPI

Releases are fully automated once the one-time setup below is done:

1. **release-please** (manifest mode — see `release-please-config.json`)
   versions the two packages independently and opens a release PR whenever
   conventional commits touch `cli-web-core/` or `devkit/`. Merging the PR
   creates tags `cli-web-core-vX.Y.Z` / `cli-web-devkit-vX.Y.Z` and GitHub
   releases.
2. **`.github/workflows/publish.yml`** triggers on those releases, builds the
   package with `python -m build`, and publishes via **PyPI trusted
   publishing** (GitHub OIDC — no API tokens stored in the repo).

## One-time setup (repo owner)

1. Create the projects on PyPI (`cli-web-core`, `cli-web-devkit`) — or use
   the "pending publisher" flow to claim the names directly from step 2.
2. On PyPI, for each project: *Manage → Publishing → Add a new publisher*:
   - Owner: `ItamarZand88`
   - Repository: `CLI-Anything-WEB`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
3. In the GitHub repo settings, create an environment named `pypi`
   (optionally with required reviewers for release protection).

## Publishing generated CLIs (future)

Generated CLIs (`cli-web-<app>`) are currently distributed from the monorepo
(`pip install -e <app>/agent-harness`). To publish a CLI to PyPI, add it as a
release-please package in `release-please-config.json` and extend the tag
match in `publish.yml` — the build step is identical.
