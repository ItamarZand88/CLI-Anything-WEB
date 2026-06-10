# Mitmproxy Capture Mode (`--mitmproxy`)

Proxy-based alternative to playwright-cli tracing. Use when the `--mitmproxy`
flag was passed to `/cli-anything-web`, or when the capture needs untruncated
bodies, real-time noise filtering, or enhanced metadata (timestamps, cookies,
body sizes). Requires `pip install mitmproxy` (Python 3.12+).

The capture workflow in SKILL.md is unchanged except for the four step
substitutions below — exploration (snapshot/click/fill/goto), pacing, and the
validate-capture gate all apply exactly as written there.

## Contents
- Step 1 substitution: open through the proxy
- Step 3 substitution: no tracing-start needed
- Step 4 substitution: stop the proxy instead of parsing a trace
- What the enhanced analysis adds

## Step 1 substitution: open through the proxy

Replace the plain `open` with:

```bash
# Start the proxy (generates .playwright/cli.proxy.config.json automatically)
python ${CLAUDE_PLUGIN_ROOT}/scripts/mitmproxy-capture.py start-proxy --port 8080

npx @playwright/cli@latest -s=<app> open <url> \
  --config=.playwright/cli.proxy.config.json --headed
```

`start-proxy` creates the config file as part of startup — no manual config
needed. All subsequent `snapshot`, `click`, `fill`, `goto` commands work
exactly the same.

## Step 3 substitution: no tracing-start needed

Skip `tracing-start` and HAR recording — the proxy has been capturing all
traffic since Step 1. Just run the exploration from SKILL.md Step 3.

## Step 4 substitution: stop the proxy instead of parsing a trace

Replace the `tracing-stop` + `parse-trace.py` block with:

```bash
# Stop the proxy and save captured traffic (includes auto-analysis)
python ${CLAUDE_PLUGIN_ROOT}/scripts/mitmproxy-capture.py stop-proxy \
  --port 8080 -o <app>/traffic-capture/raw-traffic.json

# Same gate as the default path
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate-capture.py <app>

# Full analysis report
python ${CLAUDE_PLUGIN_ROOT}/scripts/analyze-traffic.py \
  <app>/traffic-capture/raw-traffic.json --summary
```

No `tracing-stop` or `parse-trace.py` — mitmproxy already has the data.

## What the enhanced analysis adds

When traffic was captured through mitmproxy, `traffic-analysis.json` includes
fields the trace-based path cannot produce:

- `request_sequence` — timeline-ordered requests with auth-flow detection
  (login → token → API calls)
- `session_lifecycle` — cookie inventory, auth-cookie identification, session
  pattern (cookie_auth / token_refresh / no_session)
- `endpoint_sizes` — response-size classification per endpoint and total
  data transferred

When these fields are absent (`has_timestamps: false`), the capture came from
the default trace path — rely on manual analysis for sequence/session detail.
