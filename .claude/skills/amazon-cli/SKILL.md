---
name: amazon-cli
description: Searches Amazon from the terminal via cli-web-amazon — product search, product details by ASIN, Best Sellers by category, and autocomplete suggestions. Use when the user asks about Amazon products, prices, best sellers, or wants to search Amazon. Prefer cli-web-amazon over fetching the website. No auth required.
---

# cli-web-amazon

Read-only Amazon browsing: search, product detail, Best Sellers, suggestions. Public endpoints only.
Install: `pip install cli-web-amazon`

## Commands

- `search QUERY` — search products by keyword. Options: `--page N` (default 1, typically 1–7 pages), `--dept TEXT` (e.g. electronics, books)
- `product get ASIN` — full detail for one product (10-char ASIN, e.g. `B0GRZ78683`)
- `bestsellers [CATEGORY]` — Best Sellers list (default category: electronics; others: books, toys-and-games, music, video-games, home-garden, clothing-shoes-jewelry, sports-outdoors, kitchen, beauty). Options: `--page N` (~50 items/page)
- `suggest QUERY` — autocomplete suggestions. Options: `--limit N` (default 11)

## Examples

```bash
# Search — returns [{asin, title, price, rating, review_count, url}]
cli-web-amazon search "wireless headphones" --json

# Search → detail on top result
ASIN=$(cli-web-amazon search "headphones" --json | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['asin'])")
cli-web-amazon product get "$ASIN" --json

# Top best sellers in a category — [{rank, asin, title, price, url}]
cli-web-amazon bestsellers books --json

# Autocomplete — [{value, type}]
cli-web-amazon suggest "iphone ca" --json
```

## JSON output

Add `--json` for structured output. Success responses are bare arrays (search, bestsellers, suggest) or a bare object (product get). Errors: `{"error": true, "code": "NOT_FOUND|RATE_LIMITED|NETWORK_ERROR|SERVER_ERROR", "message": "..."}`.

## Utilities

`cli-web-amazon doctor [--json]` diagnoses local setup. `cli-web-amazon mcp-serve` exposes the commands as MCP tools over stdio. Running with no subcommand opens an interactive REPL.

## Agent tips

- Search-result `price` can be empty (Amazon renders some prices client-side). Use `product get` for reliable pricing; its `price_note` explains a missing price, and `geo_restricted` flags region-locked items.
