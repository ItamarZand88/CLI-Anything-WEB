# cli-web-worldcup — Test Plan & Results

## Part 1 — Plan

Two upstreams, both read-only: ESPN (no auth) and The Odds API (key-gated).

### Unit (`test_core.py`, marker `unit`, no network)
- **Model parsing** against trimmed real captures in `tests/fixtures/`
  (`scoreboard.json`, `teams.json`, `roster.json`, `standings.json`,
  `odds.json`): `Match`, `Team`, `Player`, `StandingRow`, `OddsMatch`.
- **`resolve_team`**: by id / code / name, plus not-found and ambiguous.
- **Odds key resolution**: explicit flag wins over env; missing key raises
  `AuthError` before any request.
- **HTTP status mapping** (mocked `httpx`): 401/403→Auth, 404→NotFound,
  429→RateLimit (+ Retry-After), 5xx→Server; success parses JSON.

### E2E live (`test_e2e.py::TestLiveAPI`, marker `live`, real ESPN)
- `teams` returns the nations list; `scoreboard` returns fixtures with
  competitors; `standings` has groups; `roster` returns players.
  These FAIL (not skip) if ESPN is unreachable or the feed changes shape.

### Subprocess (`test_e2e.py::TestCLISubprocess`)
- `_resolve_cli("cli-web-worldcup")` (installed binary or `python -m`
  fallback; honors `CLI_WEB_FORCE_INSTALLED=1`); `_run` sets no `cwd`.
- `--help` lists all five groups; `--version`; REPL `exit` → 0.
- Exit-code contract: unknown command → 2; `teams get Narnia` → 4
  (`NOT_FOUND`); `odds list` with no key → 3 (`AUTH_EXPIRED`).
- `--json`/`--jsonl` envelopes for `teams`, `fixtures`, `standings`.

Odds is not exercised live (no API key in CI); its success path is covered
by `OddsMatch` unit parsing of the real v4 shape, and its no-key error path
is covered end to end.

## Part 2 — Results

Run: `CLI_WEB_FORCE_INSTALLED=1 python -m pytest cli_web/worldcup/tests/ -v`

- **36 passed** (unit + live + subprocess), 0 failed.
- Live ESPN reads verified against the 2026 tournament (48 teams, 100
  fixtures, 12 groups, 26-player rosters).
- Subprocess exit-code contract verified: 0 / 2 / 3 / 4.
- Regression caught by E2E: knockout-bracket placeholder fixtures carry
  `odds: [null]`; `_odds_line` now guards the None entry.
