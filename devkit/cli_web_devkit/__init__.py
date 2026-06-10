"""Fleet tooling for the CLI-Anything-Web monorepo.

Subcommands (see ``cli_web_devkit.cli``):

- ``registry validate`` — schema + fleet cross-check for registry.json
- ``matrix``            — GitHub Actions test matrix derived from registry.json
- ``manifest``          — emit/backfill per-CLI provenance manifests
- ``drift``             — detect CLIs whose shared files diverged from canon
- ``resync``            — re-render canonical shared files into CLIs
"""

__version__ = "0.1.0"
