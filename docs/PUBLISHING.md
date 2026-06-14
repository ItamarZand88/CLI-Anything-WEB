# Publishing the fleet to PyPI

Every Python package in this monorepo is published to PyPI automatically once
the one-time setup below is done. Users then install any CLI individually, or
the whole fleet at once:

```bash
pip install cli-anything-web        # the umbrella — installs all CLIs
pip install cli-web-gh-trending     # or just one, by name
uvx cli-web-futbin --help           # or run one without installing
```

## What's published

| PyPI project | Source dir | release tag |
|--------------|-----------|-------------|
| `cli-web-core` | `cli-web-core/` | `cli-web-core-vX.Y.Z` |
| `cli-web-devkit` | `devkit/` | `cli-web-devkit-vX.Y.Z` |
| `cli-web-<app>` (×20) | `<app>/agent-harness/` | `cli-web-<app>-vX.Y.Z` |
| `cli-anything-web` (umbrella) | `meta/` | `cli-anything-web-meta-vX.Y.Z` |

That's **23 PyPI projects**. The Claude Code plugin itself (the `.` package,
tag `vX.Y.Z`) is *not* published to PyPI — only the Python packages are.

## How it works

1. **release-please** (manifest mode — `release-please-config.json` +
   `.release-please-manifest.json`) versions each package independently and
   opens a release PR whenever conventional commits touch that package's
   directory. Merging the PR creates the per-package tag and a GitHub release.
2. **`.github/workflows/publish.yml`** triggers on each release, resolves the
   package directory generically from `release-please-config.json` (component →
   path — so adding a new CLI needs no workflow change), builds it with
   `python -m build`, and uploads it with a single account-scoped **PyPI API
   token** (the `PYPI_API_TOKEN` secret on the `pypi` environment). One secret
   covers every package.

## One-time setup (repo owner)

1. **Create the GitHub environment.** In repo *Settings → Environments*, create
   one named `pypi` (optionally with required reviewers for release protection).

2. **Create a PyPI API token and store it as a secret.**
   - On PyPI: *Account settings → API tokens → Add API token*, scope **"Entire
     account"** (project-scoped tokens can't be created until the projects
     exist), and copy it.
   - On GitHub: *Settings → Environments → `pypi` → Add secret* (or a repo
     secret), named **`PYPI_API_TOKEN`**, with the token as the value.

   Once the packages are published you can, if you prefer, swap the account
   token for per-project tokens — or migrate to
   [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC, no
   stored secret) and delete the token.

3. **Add a release token so new releases auto-publish.** release-please runs
   under the default `GITHUB_TOKEN`, and releases it creates do **not** trigger
   `publish.yml` — GitHub deliberately blocks the `GITHUB_TOKEN` from triggering
   other workflows. Create a fine-grained PAT scoped to this repo (*Contents:*
   read/write, *Pull requests:* read/write) and store it as the
   `RELEASE_PLEASE_TOKEN` secret. `release-please.yml` runs under it, so each new
   release fires the publish workflow automatically.

   Without this token, publishing still works — just trigger `publish.yml`
   manually (Actions → Publish to PyPI → Run workflow → enter the release tag)
   for each package after a release.

## First release

The manifest is seeded at each package's current version (`0.1.0` for the CLIs
and the umbrella), so the **next** conventional commit touching a package cuts
its first published release. To publish a package immediately without waiting
for a change, use release-please's
[`release-as`](https://github.com/googleapis/release-please/blob/main/docs/customizing.md#how-do-i-change-the-version-number).

## The umbrella package

`cli-anything-web` (in `meta/`) is a metapackage: no code of its own, it just
depends on all `cli-web-<app>` CLIs. Its dependencies are **unpinned**, so it
rarely needs republishing — a fresh `pip install cli-anything-web` always pulls
the latest published version of each CLI. Add the new dependency line whenever a
new CLI joins the fleet.
