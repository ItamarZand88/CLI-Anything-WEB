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
   `python -m build`, and publishes via **PyPI trusted publishing** (GitHub
   OIDC — no API tokens stored in the repo).

## One-time setup (repo owner)

1. **Create the GitHub environment.** In repo *Settings → Environments*, create
   one named `pypi` (optionally with required reviewers for release protection).

2. **Add a Trusted Publisher for each of the 23 projects on PyPI.** Use the
   [pending publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
   flow to claim each name *before* its first publish (this also reserves the
   names so they can't be squatted). For every project — *Manage → Publishing →
   Add a new publisher* (or *Your projects → Publishing* for a pending one):
   - Owner: `ItamarZand88`
   - Repository: `CLI-Anything-WEB`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`

   The project names to register are the 22 in the table above:
   `cli-web-core`, `cli-web-devkit`, `cli-anything-web`, and `cli-web-<app>` for
   each app (`cli-web-futbin`, `cli-web-notebooklm`, … `cli-web-worldcup`).

## First release

The manifest is seeded at each package's current version (`0.1.0` for the CLIs
and the umbrella), so the **next** conventional commit touching a package cuts
its first published release. To publish a package immediately without waiting
for a change, use release-please's
[`release-as`](https://github.com/googleapis/release-please/blob/main/docs/customizing.md#how-do-i-change-the-version-number)
(e.g. a `chore: release` commit with `Release-As: 0.1.0`).

## The umbrella package

`cli-anything-web` (in `meta/`) is a metapackage: no code of its own, it just
depends on all `cli-web-<app>` CLIs. Its dependencies are **unpinned**, so it
rarely needs republishing — a fresh `pip install cli-anything-web` always pulls
the latest published version of each CLI. Add the new dependency line whenever a
new CLI joins the fleet.
