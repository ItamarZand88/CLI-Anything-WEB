---
name: cli-anything-web-methodology
description: This skill should be used when the user asks to "create a CLI for a website", "generate API wrapper", "reverse engineer web API", "record web traffic", "make a web app agent-native", "build CLI from network traffic", or discusses turning closed-source web applications into agent-controllable command-line interfaces via HTTP traffic analysis and Chrome DevTools MCP.
version: 0.1.0
---

# CLI-Anything-Web Methodology

Generate agent-native CLI interfaces for closed-source web applications
by analyzing network traffic captured via Chrome DevTools MCP.

## Overview

CLI-Anything-Web builds production-grade Python CLI interfaces for closed-source
web applications by observing their live HTTP traffic. It records HTTP
traffic between browser and server, maps the API surface, and generates
a production-ready Python CLI.

## When to Use

- Target is a web application (SaaS, internal tools, any browser-based app)
- No source code available (or source code is irrelevant — the API is the interface)
- Goal is programmatic/agent access to the web app's functionality

## Pipeline Summary

Eight phases:

1. **Record** — Capture HTTP traffic via Chrome DevTools MCP
2. **Analyze** — Map endpoints, schemas, auth patterns
3. **Design** — Architect Click CLI command structure
4. **Implement** — Generate Python package under `cli_web.<app>`
5. **Plan Tests** — Write TEST.md Part 1 (test plan before code)
6. **Test** — Unit tests (mocked HTTP) + E2E tests (live/fixtures)
7. **Document** — Append TEST.md Part 2 (results)
8. **Publish** — `pip install -e .` → `cli-web-<app>` on PATH

## Reference Files

- **`${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md`** — Full methodology SOP (source of truth)
- **`references/traffic-patterns.md`** — Common API patterns (REST, GraphQL, RPC)
- **`references/auth-strategies.md`** — Auth implementation strategies
