---
name: amazon-cli
description: Use cli-web-amazon to search Amazon products, get product details, check
  prices, browse best sellers, and get autocomplete suggestions. Invoke this skill
  whenever the user asks about Amazon products, prices, best sellers, or wants to
  search Amazon. Always prefer cli-web-amazon over manually fetching the website.
  No authentication required — fully public site.
---

# cli-web-amazon

Search Amazon products, view details, browse Best Sellers, and get autocomplete suggestions. No authentication required.

## Quick Start

```bash
cli-web-amazon search "laptop" --json
cli-web-amazon product get B0GRZ78683 --json
cli-web-amazon bestsellers electronics --json
```

Always use `--json` when parsing output programmatically.

---

## Commands

### `search QUERY`
Search Amazon products by keyword.

```bash
cli-web-amazon search "wireless headphones" --json
cli-web-amazon search "laptop" --page 2 --dept electronics --json
```

**Key options:** `--page N` (default 1), `--dept <department>`

**Output fields:** `asin`, `title`, `price`, `rating`, `review_count`, `url`

---

### `suggest QUERY`
Autocomplete suggestions.

```bash
cli-web-amazon suggest "iphone case" --json
```

**Output fields:** `value`, `type`

---

### `product get ASIN`
Full product detail by ASIN.

```bash
cli-web-amazon product get B0GRZ78683 --json
```

**Output fields:** `asin`, `title`, `price`, `price_note`, `geo_restricted`, `rating`, `review_count`, `brand`, `image_url`, `url`

---

### `bestsellers [CATEGORY]`
Browse Amazon Best Sellers by category.

```bash
cli-web-amazon bestsellers electronics --json
cli-web-amazon bestsellers books --page 2 --json
```

**Categories:** `electronics`, `books`, `toys-and-games`, `music`, `kitchen`, `clothing`

**Key options:** `--page N`

**Output fields:** `rank`, `asin`, `title`, `price`, `url`

---

## Agent Patterns

```bash
# Search then get full detail on top result
ASIN=$(cli-web-amazon search "headphones" --json | python -c "import json,sys; print(json.load(sys.stdin)[0]['asin'])")
cli-web-amazon product get "$ASIN" --json

# Top-5 bestsellers
cli-web-amazon bestsellers electronics --json | \
  python -c "import json,sys; [print(p['rank'], p['title'], p['price']) for p in json.load(sys.stdin)[:5]]"

# Autocomplete then search
cli-web-amazon suggest "wireles" --json | \
  python -c "import json,sys; print(json.load(sys.stdin)[0]['value'])"
```

---

## Notes

- **Auth:** No authentication required — all commands work on public Amazon endpoints.
- **Price:** May be empty for some products (Amazon client-side renders prices). Use `product get` for reliable pricing; `price_note` explains why price is missing.
- **ASIN:** 10-character alphanumeric identifier (e.g. `B0GRZ78683`).
- **Pagination:** Search supports `--page N` (typically 1–7 pages). Best sellers supports `--page N`.
- **Errors in --json mode:** `{"error": true, "code": "NOT_FOUND|RATE_LIMITED|NETWORK_ERROR|SERVER_ERROR", "message": "..."}`
- **Installation:** `pip install -e amazon/agent-harness`
