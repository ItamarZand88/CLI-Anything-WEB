---
name: cli-anything-web-methodology
description: This skill should be used when the user asks to "create a CLI for a website", "generate API wrapper", "reverse engineer web API", "record web traffic", "make a web app agent-native", "build CLI from network traffic", or discusses turning closed-source web applications into agent-controllable command-line interfaces via HTTP traffic analysis and playwright-cli (or chrome-devtools-mcp as fallback).
version: 0.1.0
---

# CLI-Anything-Web Methodology

Generate agent-native CLI interfaces for closed-source web applications
by analyzing network traffic captured via playwright-cli (or chrome-devtools-mcp as fallback).

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

1. **Record** — Capture HTTP traffic via playwright-cli (or chrome-devtools-mcp as fallback)
2. **Analyze** — Map endpoints, schemas, auth patterns
3. **Design** — Architect Click CLI command structure
4. **Implement** — Generate Python package under `cli_web.<app>`
5. **Plan Tests** — Write TEST.md Part 1 (test plan before code)
6. **Test** — Unit tests (mocked HTTP) + E2E tests (live/fixtures)
7. **Document** — Append TEST.md Part 2 (results)
8. **Publish** — `pip install -e .` → `cli-web-<app>` on PATH

## Companion Skills

This plugin has three skills that work together — Claude activates the right one
based on what you're doing:

| Skill | Auto-activates when... |
|-------|----------------------|
| **cli-anything-web-methodology** (this) | Building a new CLI from scratch, running the full pipeline |
| **cli-anything-web-testing** | Writing tests, planning test coverage, debugging test failures |
| **cli-anything-web-standards** | Checking quality, reviewing implementations, validating structure |
| **web-reconnaissance** | Analyzing unfamiliar sites, detecting frameworks, choosing capture strategy |

You don't need to invoke these manually — Claude picks the right one based on context.
During the full pipeline, all three activate at the relevant phases.

## Reference Files

- **`${CLAUDE_PLUGIN_ROOT}/HARNESS.md`** — Full methodology SOP (source of truth)
- **`references/traffic-patterns.md`** — Common API patterns (REST, GraphQL, RPC)
- **`references/auth-strategies.md`** — Auth implementation strategies
- **`references/google-batchexecute.md`** — Google batchexecute RPC protocol spec (URL format, encoding, decoding, tokens)
- **`references/ssr-patterns.md`** — SSR framework patterns and data extraction strategies
