# cli-anything-web

Umbrella package that installs the **entire CLI-Anything-Web fleet** — every
agent-native CLI in one shot.

```bash
pipx install cli-anything-web      # or: uv tool install cli-anything-web
```

This pulls in all `cli-web-*` commands (`cli-web-futbin`, `cli-web-gh-trending`,
`cli-web-reddit`, …). To install just one CLI instead, install it directly:

```bash
uvx cli-web-gh-trending repos list      # zero-install, runs immediately
pipx install cli-web-futbin             # or install a single CLI persistently
```

See the [monorepo README](https://github.com/ItamarZand88/CLI-Anything-WEB) for
the full list of CLIs and usage.
