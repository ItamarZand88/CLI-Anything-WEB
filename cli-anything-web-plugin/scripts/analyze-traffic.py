#!/usr/bin/env python3
"""Analyze raw-traffic.json and produce a structured traffic analysis report.

Reads the output of parse-trace.py and auto-detects:
- API protocol type (REST, GraphQL, batchexecute, SSR, etc.)
- Authentication pattern (Bearer, Cookie, API key, none)
- Endpoint grouping by URL prefix
- GraphQL operation names and types
- Rate limit signals (429s, Retry-After headers)
- Protection/WAF signals (Cloudflare, AWS WAF, Akamai, DataDome, PerimeterX, CAPTCHA)
- Pagination pattern detection
- WebSocket library/sub-protocol fingerprinting
- Read vs write operation breakdown
- Suggested CLI command structure

The agent reads this analysis to accelerate Phase 2 (methodology).
Anything the script can't confidently detect is marked "unknown" —
the agent falls back to manual analysis for those fields.

Usage:
    python analyze-traffic.py raw-traffic.json --output traffic-analysis.json
    python analyze-traffic.py raw-traffic.json  # prints to stdout
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote


def _is_noise_url(url: str) -> bool:
    """Check if a URL is analytics/tracking/CDN noise — not a real API call."""
    NOISE = [
        # Google analytics / ads
        "google-analytics", "analytics.google.com", "googletagmanager.com",
        "googlesyndication", "google.com/ads", "google.com/pagead",
        "doubleclick.net", "www.google.co.", "gstatic.com",
        "googleapis.com/css", "fonts.googleapis.com",
        "play.google.com/log", "signaler-pa.clients6",
        "accounts.google.com/gsi", "apis.google.com",
        # Cloudflare
        "cdn-cgi/", "cloudflareinsights", "static.cloudflareinsights",
        # Social / ad networks
        "facebook.com/tr", "facebook.net",
        "twitter.com", "analytics.twitter.com",
        "taboola.com", "optable.co", "admedo.com",
        "scorecardresearch.com", "statcounter.com",
        "liftdsp.com", "bidr.io", "cnv.event.prod",
        # Monitoring / analytics SDKs
        "datadoghq.com", "browser-intake-datadoghq",
        "fullstory.com", "segment.prod",
        # CRM / marketing automation
        "hubspot.com", "hscollectedforms.net", "hsforms.com",
        "cookiebot.com",
        # Generic tracking patterns (same-site endpoints)
        "/ht/event", "/hubspot",
        # GitHub internal
        "avatars.githubusercontent.com", "collector.github.com",
        "api.github.com/_private",
        # Generic noise patterns
        "/manifest.json", "/beacon", "/pixel", "/rum",
        "slinksuggestion.com", "drainpaste.com",
        "e.producthunt.com", "t.producthunt.com",
    ]
    return any(x in url for x in NOISE)


def _detect_ws_library(url: str) -> str | None:
    """Fingerprint WebSocket library from URL path patterns."""
    path = urlparse(url).path.lower()
    if "socket.io" in path or "EIO=" in url:
        return "socket.io"
    if "/sockjs/" in path:
        return "sockjs"
    if "/cable" in path:  # Rails ActionCable convention
        return "action-cable"
    if "/phoenix/" in path or path.endswith("/websocket"):
        return "phoenix-channels"
    if "/signalr/" in path:
        return "signalr"
    return None


def _infer_ws_purpose(urls: list) -> str | None:
    """Infer WebSocket purpose from URL patterns."""
    joined = " ".join(urls).lower()
    if any(x in joined for x in ["chat", "message", "msg"]):
        return "chat/messaging"
    if any(x in joined for x in ["stream", "feed", "live"]):
        return "streaming"
    if any(x in joined for x in ["notify", "notif", "alert", "event"]):
        return "notifications/events"
    if any(x in joined for x in ["realtime", "real-time"]):
        return "real-time updates"
    return None


def detect_protocol(entries: list[dict]) -> dict:
    """Detect the API protocol type from traffic patterns.

    Filters out analytics/tracking noise before scoring to avoid
    false signals from POST-heavy tracking endpoints.
    """
    signals = {
        "graphql": 0,
        "batchexecute": 0,
        "rest": 0,
        "grpc_web": 0,
        "ssr_html": 0,
        "websocket": 0,
        "sse": 0,
        "json_rpc": 0,
        "trpc": 0,
        "firebase": 0,
    }

    graphql_ops = []
    batchexecute_methods = []
    batchexecute_rpc_details = {}
    batchexecute_service = None
    batchexecute_bl = None
    websocket_url_set = set()
    websocket_subprotocols = set()
    websocket_libraries = set()
    sse_urls = []
    json_rpc_methods = []
    trpc_procedures = []
    firebase_paths = []

    for e in entries:
        url = e.get("url", "")
        method = e.get("method", "GET")
        mime = e.get("mime_type", "")
        body = e.get("post_data", "") or ""
        headers = e.get("request_headers", {})
        resp_headers = e.get("response_headers", {})
        content_type = headers.get("content-type", headers.get("Content-Type", ""))

        # Skip noise for protocol detection (analytics, tracking, CDN)
        is_noise = _is_noise_url(url)

        # --- GraphQL ---
        if "/graphql" in url.lower() and not is_noise:
            signals["graphql"] += 5
            if method == "GET" and "operationName=" in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                op = params.get("operationName", [""])[0]
                if op:
                    graphql_ops.append({"name": op, "type": "query", "method": "GET"})
            elif method == "POST" and body:
                try:
                    parsed_body = json.loads(body)
                    op = parsed_body.get("operationName", "")
                    query = parsed_body.get("query", "")
                    op_type = "mutation" if query and "mutation" in query[:50].lower() else "query"
                    if op:
                        graphql_ops.append({"name": op, "type": op_type, "method": "POST"})
                except json.JSONDecodeError:
                    pass  # Non-JSON body on GraphQL endpoint (e.g., multipart upload)
                except TypeError as exc:
                    print(f"Warning: unexpected type in GraphQL body parse for {url}: {exc}", file=sys.stderr)

        # --- Google batchexecute ---
        if "batchexecute" in url and not is_noise:
            signals["batchexecute"] += 5
            parsed_url = urlparse(url)
            url_params = parse_qs(parsed_url.query)
            rpcid = url_params.get("rpcids", [""])[0]
            if rpcid:
                batchexecute_methods.append(rpcid)

                # Parse f.req from POST body to extract param structure per RPC ID
                if body and "f.req=" in body:
                    try:
                        body_params = parse_qs(body)
                        freq_str = body_params.get("f.req", [""])[0]
                        if freq_str:
                            outer = json.loads(freq_str)
                            # Structure: [[[rpc_id, params_json, null, "generic"]]]
                            inner = outer[0][0] if outer and outer[0] and outer[0][0] else None
                            if inner and len(inner) >= 2 and inner[1]:
                                try:
                                    params_data = json.loads(inner[1])
                                except (json.JSONDecodeError, TypeError):
                                    params_data = inner[1][:200] if isinstance(inner[1], str) else str(inner[1])[:200]
                                if rpcid not in batchexecute_rpc_details:
                                    batchexecute_rpc_details[rpcid] = {
                                        "call_count": 0,
                                        "example_params": [params_data],
                                    }
                                else:
                                    # Store distinct param structures (up to 3) per RPC ID
                                    existing = batchexecute_rpc_details[rpcid]["example_params"]
                                    if len(existing) < 3 and params_data not in existing:
                                        existing.append(params_data)
                                batchexecute_rpc_details[rpcid]["call_count"] += 1
                    except (json.JSONDecodeError, TypeError, IndexError, KeyError) as exc:
                        print(
                            f"Warning: failed to parse f.req body for RPC {rpcid}: "
                            f"{type(exc).__name__}: {exc}",
                            file=sys.stderr,
                        )

            # Extract service name: /_/ServiceName/data/batchexecute
            if not batchexecute_service:
                m = re.search(r'/_/([^/]+)/data/batchexecute', url)
                if m:
                    batchexecute_service = m.group(1)

            # Extract build label (bl) as a reference value
            if not batchexecute_bl:
                bl = url_params.get("bl", [""])[0]
                if bl:
                    batchexecute_bl = bl

        # --- gRPC-Web ---
        if "application/grpc" in content_type and not is_noise:
            signals["grpc_web"] += 5

        # --- WebSocket ---
        is_ws_url = url.startswith("wss://") or url.startswith("ws://")
        upgrade = headers.get("upgrade", headers.get("Upgrade", ""))
        has_ws_upgrade = upgrade.lower() == "websocket"
        if is_ws_url or has_ws_upgrade:
            signals["websocket"] += 5  # once per entry regardless of which signal triggered
            websocket_url_set.add(url)
            # Sub-protocol extraction (e.g. "graphql-ws", "stomp", "mqtt")
            subproto = headers.get(
                "sec-websocket-protocol",
                headers.get("Sec-WebSocket-Protocol", "")
            )
            for sp in (subproto.split(",") if subproto else []):
                sp = sp.strip()
                if sp:
                    websocket_subprotocols.add(sp)
            # Library fingerprint from URL
            lib = _detect_ws_library(url)
            if lib:
                websocket_libraries.add(lib)

        # --- Server-Sent Events (SSE) ---
        resp_ct = resp_headers.get("content-type", resp_headers.get("Content-Type", ""))
        if "text/event-stream" in resp_ct:
            signals["sse"] += 5
            sse_urls.append(url)
        accept = headers.get("accept", headers.get("Accept", ""))
        if "text/event-stream" in accept:
            signals["sse"] += 3
            sse_urls.append(url)

        # --- JSON-RPC ---
        if body and not is_noise:
            try:
                parsed_body = json.loads(body)
                if isinstance(parsed_body, dict):
                    if "jsonrpc" in parsed_body and "method" in parsed_body:
                        signals["json_rpc"] += 5
                        json_rpc_methods.append(parsed_body["method"])
                elif isinstance(parsed_body, list) and len(parsed_body) > 0:
                    if isinstance(parsed_body[0], dict) and "jsonrpc" in parsed_body[0] and "method" in parsed_body[0]:
                        signals["json_rpc"] += 5
                        for item in parsed_body:
                            if isinstance(item, dict) and "method" in item:
                                json_rpc_methods.append(item["method"])
            except json.JSONDecodeError:
                pass  # Non-JSON body — expected for non-RPC POST requests
            except TypeError as exc:
                print(f"Warning: unexpected type in JSON-RPC parse: {exc}", file=sys.stderr)

        # --- tRPC ---
        if ("/api/trpc/" in url or "/trpc/" in url) and not is_noise:
            signals["trpc"] += 5
            # Extract procedure name from URL: /api/trpc/post.list
            parsed = urlparse(url)
            path = parsed.path
            trpc_match = re.search(r"/trpc/(.+?)(?:\?|$)", path)
            if trpc_match:
                trpc_procedures.append(trpc_match.group(1))

        # --- Firebase Realtime Database ---
        if "firebaseio.com" in url and not is_noise:
            signals["firebase"] += 5
            parsed = urlparse(url)
            firebase_paths.append(parsed.path)

        # --- REST --- resource-style URLs
        if not is_noise and (re.match(r".*/api/v\d+/", url) or "/api/" in url):
            # Don't count if already matched a specific protocol above
            if signals["graphql"] == 0 and signals["trpc"] == 0:
                signals["rest"] += 2

        # --- SSR/HTML ---
        if "text/html" in mime and method == "GET" and not is_noise:
            signals["ssr_html"] += 2

    # Determine primary protocol
    if not entries:
        return {"protocol": "unknown", "confidence": 0, "signals": {}}

    # Remove zero signals
    active_signals = {k: v for k, v in signals.items() if v > 0}

    if not active_signals:
        return {"protocol": "unknown", "confidence": 0, "signals": {}}

    # Confidence = top signal's share of total signal weight.
    # No artificial boosting — the number reflects actual signal dominance.
    # All signals shown so the agent can judge edge cases.
    max_signal = max(active_signals, key=active_signals.get)
    max_value = active_signals[max_signal]
    total = sum(active_signals.values()) or 1
    confidence = round(max_value / total * 100, 1)

    result = {
        "protocol": max_signal,
        "confidence": min(confidence, 100.0),
        "signals": {k: round(v, 1) for k, v in active_signals.items()},
    }

    if graphql_ops:
        seen = set()
        unique_ops = []
        for op in graphql_ops:
            key = (op["name"], op["type"])
            if key not in seen:
                seen.add(key)
                unique_ops.append(op)
        result["graphql_operations"] = unique_ops

    if batchexecute_methods:
        result["batchexecute_rpc_ids"] = sorted(set(batchexecute_methods))
    if batchexecute_rpc_details:
        result["batchexecute_rpc_details"] = batchexecute_rpc_details
    if batchexecute_service:
        result["batchexecute_service"] = batchexecute_service
    if batchexecute_bl:
        result["batchexecute_build_label"] = batchexecute_bl

    if websocket_url_set:
        result["websocket_urls"] = sorted(websocket_url_set)[:10]
        if websocket_subprotocols:
            result["websocket_subprotocols"] = sorted(websocket_subprotocols)
        if websocket_libraries:
            result["websocket_library"] = sorted(websocket_libraries)[0]
        purpose = _infer_ws_purpose(list(websocket_url_set))
        if purpose:
            result["websocket_purpose"] = purpose

    if sse_urls:
        result["sse_urls"] = sorted(set(sse_urls))[:10]

    if json_rpc_methods:
        result["json_rpc_methods"] = sorted(set(json_rpc_methods))

    if trpc_procedures:
        result["trpc_procedures"] = sorted(set(trpc_procedures))

    if firebase_paths:
        result["firebase_paths"] = sorted(set(firebase_paths))[:10]

    return result


def detect_auth(entries: list[dict]) -> dict:
    """Detect authentication pattern from request headers (noise URLs excluded)."""
    bearer_count = 0
    cookie_count = 0
    api_key_count = 0
    no_auth_count = 0

    api_key_headers = set()
    cookie_names = set()

    for e in (e for e in entries if not _is_noise_url(e.get("url", ""))):
        headers = e.get("request_headers", {})
        has_auth = False

        # Bearer token
        auth_header = headers.get("authorization", headers.get("Authorization", ""))
        if auth_header.lower().startswith("bearer "):
            bearer_count += 1
            has_auth = True

        # API key patterns
        for h in headers:
            h_lower = h.lower()
            if h_lower in ("x-api-key", "api-key", "apikey", "x-auth-token"):
                api_key_count += 1
                api_key_headers.add(h)
                has_auth = True

        # Cookie-based
        cookie = headers.get("cookie", headers.get("Cookie", ""))
        if cookie:
            cookie_count += 1
            # Extract meaningful cookie names (skip tracking cookies)
            for part in cookie.split(";"):
                name = part.strip().split("=")[0]
                if name and name not in ("_ga", "_gid", "_gat", "__cf_bm", "cf_clearance"):
                    cookie_names.add(name)
            has_auth = True

        if not has_auth:
            no_auth_count += 1

    # Use actual count of non-noise entries as denominator (a request may have
    # both bearer and cookie, so summing individual counters would inflate total)
    total = sum(1 for _ in (e for e in entries if not _is_noise_url(e.get("url", "")))) or 1
    patterns = {}
    if bearer_count > 0:
        patterns["bearer"] = round(bearer_count / total * 100, 1)
    if api_key_count > 0:
        patterns["api_key"] = round(api_key_count / total * 100, 1)
    if cookie_count > 0:
        patterns["cookie"] = round(cookie_count / total * 100, 1)
    if no_auth_count > 0:
        patterns["none"] = round(no_auth_count / total * 100, 1)

    # Determine primary auth
    if not patterns:
        primary = "none"
    else:
        primary = max(patterns, key=patterns.get)

    result = {
        "primary": primary,
        "patterns": patterns,
    }

    if api_key_headers:
        result["api_key_header_names"] = sorted(api_key_headers)
    if cookie_names and primary == "cookie":
        # Show auth-relevant cookies (SID, session, etc.)
        auth_cookies = [c for c in cookie_names
                        if any(k in c.lower() for k in ("sid", "session", "auth", "token", "osid", "secure"))]
        if auth_cookies:
            result["auth_cookie_names"] = sorted(auth_cookies)

    return result


def detect_protections(entries: list[dict]) -> dict:
    """Detect WAF/bot protection signals."""
    protections = {
        "cloudflare": False,
        "aws_waf": False,
        "akamai": False,
        "datadome": False,
        "perimeterx": False,
        "captcha": False,
        "rate_limited": False,
    }
    details_seen = set()
    details = []

    def _add_detail(msg: str) -> None:
        if msg not in details_seen:
            details_seen.add(msg)
            details.append(msg)

    for e in entries:
        status = e.get("status", 0)
        req_headers = e.get("request_headers", {})
        headers = e.get("response_headers", {})
        body = e.get("response_body", "")
        body_str = str(body)[:2000].lower() if body else ""
        cookie = req_headers.get("cookie", req_headers.get("Cookie", ""))

        # Cloudflare
        if headers.get("cf-ray") or headers.get("CF-RAY"):
            protections["cloudflare"] = True
        if "just a moment" in body_str and "cloudflare" in body_str:
            protections["cloudflare"] = True
            _add_detail("Cloudflare challenge page detected")

        # AWS WAF — 202 JS challenge or x-amzn-waf-* response headers
        if status == 202 and "aws-waf-token" in body_str:
            protections["aws_waf"] = True
            _add_detail("AWS WAF JavaScript challenge detected (202 response)")
        if any(h.lower().startswith("x-amzn-waf") for h in headers):
            protections["aws_waf"] = True
        if "aws-waf-token" in cookie:
            protections["aws_waf"] = True

        # Akamai
        if headers.get("akamai-grn") or headers.get("Akamai-GRN"):
            protections["akamai"] = True
        if "akamai" in body_str and ("access denied" in body_str or "reference #" in body_str):
            protections["akamai"] = True
            _add_detail("Akamai access denial detected")

        # DataDome
        if any(h.lower() in ("x-dd-b", "x-datadome") for h in headers):
            protections["datadome"] = True
        if "datadome.co" in body_str or "datadome" in body_str:
            protections["datadome"] = True
            _add_detail("DataDome bot protection detected")

        # PerimeterX
        if "_pxhd" in cookie or "_px3" in cookie:
            protections["perimeterx"] = True
        if any(h.lower().startswith("x-px") for h in headers):
            protections["perimeterx"] = True
        if "perimeterx" in body_str or "px-captcha" in body_str:
            protections["perimeterx"] = True
            _add_detail("PerimeterX bot protection detected")

        # CAPTCHA
        if any(x in body_str for x in ["g-recaptcha", "h-captcha"]):
            protections["captcha"] = True
            _add_detail("CAPTCHA detected in response")

        # Rate limiting
        if status == 429:
            protections["rate_limited"] = True
            retry_after = headers.get("retry-after", headers.get("Retry-After", ""))
            _add_detail(f"429 Too Many Requests (Retry-After: {retry_after or 'not specified'})")

    active = {k: v for k, v in protections.items() if v}
    return {
        "protections": active,
        "details": details,
        "has_protection": bool(active),
        "recommended_client": _recommend_client(active),
    }


def _recommend_client(active_protections: dict) -> str:
    """Recommend httpx vs curl_cffi based on detected protections."""
    if any(active_protections.get(p) for p in ("cloudflare", "aws_waf", "datadome", "perimeterx")):
        return "curl_cffi (impersonate='chrome') — bot protection detected"
    if active_protections.get("akamai"):
        return "curl_cffi (impersonate='chrome') — Akamai detected"
    return "httpx"


_RE_UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
_RE_NUMERIC_ID = re.compile(r'^\d+$')
_RE_HASH_ID = re.compile(r'^[0-9a-f]{16,}$', re.I)  # long hex IDs


def _normalize_segment(segment: str) -> str:
    """Replace dynamic path segments (UUIDs, numeric IDs, hex hashes) with ``{id}``."""
    if _RE_UUID.match(segment):
        return "{id}"
    # Skip short numbers that could be version segments (v1, v2, api/2)
    if _RE_NUMERIC_ID.match(segment) and len(segment) >= 4:
        return "{id}"
    if _RE_HASH_ID.match(segment) and len(segment) >= 16:
        return "{id}"
    return segment


_STATIC_MIME_PREFIXES = (
    "image/", "font/", "audio/", "video/",
    "text/css", "application/javascript", "application/x-javascript",
    "text/javascript",
)
_STATIC_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".css", ".js", ".map",
)


def _is_static_asset(entry: dict) -> bool:
    """Return True if the entry is a static asset (image, font, CSS, JS)."""
    mime = entry.get("mime_type", "").split(";")[0].strip().lower()
    if any(mime.startswith(p) for p in _STATIC_MIME_PREFIXES):
        return True
    url = entry.get("url", "").split("?")[0].lower()
    if any(url.endswith(ext) for ext in _STATIC_EXTENSIONS):
        return True
    return False


def group_endpoints(entries: list[dict]) -> list[dict]:
    """Group API requests by URL prefix into resource groups."""
    api_entries = [
        e for e in entries
        if not _is_noise_url(e.get("url", "")) and not _is_static_asset(e)
    ]

    # Parse URLs and group by prefix
    groups = defaultdict(lambda: {"methods": Counter(), "urls": set(), "count": 0})

    for e in api_entries:
        url = e.get("url", "")
        method = e.get("method", "GET")
        parsed = urlparse(url)

        # Determine group key: use first 2-3 path segments, normalizing IDs
        path = parsed.path.rstrip("/")
        segments = [_normalize_segment(s) for s in path.split("/") if s]

        if not segments:
            continue

        # Group by domain + first meaningful path segments
        host = parsed.hostname or ""
        if len(segments) >= 2:
            group_key = f"{host}/{segments[0]}/{segments[1]}"
        else:
            group_key = f"{host}/{segments[0]}"

        groups[group_key]["methods"][method] += 1
        groups[group_key]["urls"].add(url.split("?")[0])
        groups[group_key]["count"] += 1

    # Convert to sorted list
    result = []
    for key, data in sorted(groups.items(), key=lambda x: -x[1]["count"]):
        if data["count"] < 1:
            continue
        methods = dict(data["methods"])
        has_writes = any(m in methods for m in ("POST", "PUT", "PATCH", "DELETE"))
        result.append({
            "prefix": key,
            "count": data["count"],
            "methods": methods,
            "has_writes": has_writes,
            "unique_urls": len(data["urls"]),
            "sample_urls": sorted(data["urls"])[:5],
        })

    return result[:20]  # Top 20 groups


_PAGINATION_PARAMS = {
    "page", "offset", "limit", "cursor", "after", "before",
    "skip", "take", "per_page", "pagesize", "page_size", "startindex",
}


def detect_pagination(entries: list[dict]) -> dict:
    """Detect pagination patterns in API requests."""
    paginated_endpoints = {}  # prefix → set of pagination params seen

    for e in entries:
        url = e.get("url", "")
        if _is_noise_url(url):
            continue
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        found = {p.lower() for p in params if p.lower() in _PAGINATION_PARAMS}
        if found:
            # Normalize the path for grouping
            segments = [_normalize_segment(s) for s in parsed.path.strip("/").split("/") if s]
            key = (parsed.hostname or "") + "/" + "/".join(segments[:2])
            if key not in paginated_endpoints:
                paginated_endpoints[key] = set()
            paginated_endpoints[key].update(found)

    if not paginated_endpoints:
        return {"has_pagination": False}

    return {
        "has_pagination": True,
        "paginated_endpoints": [
            {"prefix": k, "params": sorted(v)}
            for k, v in sorted(paginated_endpoints.items())
        ],
        "cli_note": "List commands on paginated endpoints should support --page/--limit/--cursor flags",
    }


def detect_rate_limits(entries: list[dict]) -> dict:
    """Detect rate limit signals from traffic."""
    rate_limit_headers = {}
    status_429_count = 0
    retry_after_values = []

    for e in entries:
        status = e.get("status", 0)
        headers = e.get("response_headers", {})

        if status == 429:
            status_429_count += 1

        # Common rate limit headers
        for h, v in headers.items():
            h_lower = h.lower()
            if any(x in h_lower for x in ["ratelimit", "rate-limit", "x-rate", "retry-after"]):
                rate_limit_headers[h] = v
                if "retry" in h_lower:
                    retry_after_values.append(v)

    return {
        "status_429_count": status_429_count,
        "rate_limit_headers": rate_limit_headers if rate_limit_headers else None,
        "retry_after_values": retry_after_values if retry_after_values else None,
        "has_rate_limiting": status_429_count > 0 or bool(rate_limit_headers),
    }


def compute_stats(entries: list[dict]) -> dict:
    """Compute basic traffic statistics. Noise URLs excluded from method/status/MIME counts; domains include all entries."""
    api_entries = [e for e in entries if not _is_noise_url(e.get("url", ""))]

    methods = Counter(e.get("method", "GET") for e in api_entries)
    statuses = Counter(e.get("status", 0) for e in api_entries)
    mime_types = Counter(e.get("mime_type", "").split(";")[0].strip() for e in api_entries)

    writes = sum(methods.get(m, 0) for m in ("POST", "PUT", "PATCH", "DELETE"))
    reads = methods.get("GET", 0)

    # Unique domains (from all entries, including noise — useful for awareness)
    domains = set()
    for e in entries:
        parsed = urlparse(e.get("url", ""))
        if parsed.hostname:
            domains.add(parsed.hostname)

    return {
        "total_requests": len(api_entries),
        "read_operations": reads,
        "write_operations": writes,
        "is_read_only": writes == 0,
        "methods": dict(methods),
        "status_codes": dict(statuses),
        "top_mime_types": dict(mime_types.most_common(5)),
        "unique_domains": sorted(domains),
    }


def suggest_commands(endpoint_groups: list[dict], protocol: dict) -> list[dict]:
    """Suggest CLI command groups based on endpoint patterns."""
    # For batchexecute: generate RPC-based suggestions instead of REST-based
    if protocol.get("protocol") == "batchexecute":
        rpc_ids = protocol.get("batchexecute_rpc_ids", [])
        rpc_details = protocol.get("batchexecute_rpc_details", {})
        service = protocol.get("batchexecute_service", "rpc")
        if rpc_ids:
            commands = []
            for rpc_id in rpc_ids[:20]:
                detail = rpc_details.get(rpc_id, {})
                count = detail.get("call_count", 1)
                commands.append({
                    "name": rpc_id,
                    "method": "POST",
                    "call_count": count,
                    "description": f"RPC {rpc_id} (captured {count}x) — verify params in batchexecute_rpc_details",
                })
            return [{
                "group": service,
                "prefix": f"/_/{service}/data/batchexecute",
                "note": "Map RPC IDs to CLI commands. See batchexecute_rpc_details for param structures.",
                "commands": commands,
            }]

    suggestions = []

    for group in endpoint_groups[:10]:
        prefix = group["prefix"]
        methods = group["methods"]

        # Extract resource name from prefix
        parts = prefix.split("/")
        resource = parts[-1] if parts else "unknown"
        # Singularize simple cases
        resource_singular = resource.rstrip("s") if resource.endswith("s") and len(resource) > 3 else resource

        commands = []
        if methods.get("GET", 0) > 0:
            commands.append({"name": "list", "method": "GET", "description": f"List {resource}"})
            if group["unique_urls"] > 1:
                commands.append({"name": "get", "method": "GET", "description": f"Get a specific {resource_singular}"})
        if methods.get("POST", 0) > 0:
            commands.append({"name": "create", "method": "POST", "description": f"Create a new {resource_singular}"})
        if methods.get("PUT", 0) > 0 or methods.get("PATCH", 0) > 0:
            commands.append({"name": "update", "method": "PUT/PATCH", "description": f"Update a {resource_singular}"})
        if methods.get("DELETE", 0) > 0:
            commands.append({"name": "delete", "method": "DELETE", "description": f"Delete a {resource_singular}"})

        if commands:
            suggestions.append({
                "group": resource,
                "prefix": prefix,
                "commands": commands,
            })

    return suggestions


def analyze(entries: list[dict]) -> dict:
    """Run all analyses and produce the complete report."""
    protocol = detect_protocol(entries)
    auth = detect_auth(entries)
    protections = detect_protections(entries)
    endpoints = group_endpoints(entries)
    rate_limits = detect_rate_limits(entries)
    pagination = detect_pagination(entries)
    stats = compute_stats(entries)
    suggestions = suggest_commands(endpoints, protocol)

    return {
        "_meta": {
            "tool": "analyze-traffic.py",
            "version": "1.2.1",
            "description": "Auto-generated traffic analysis. Fields marked 'unknown' need manual agent analysis.",
        },
        "protocol": protocol,
        "auth": auth,
        "protections": protections,
        "endpoints": endpoints,
        "rate_limits": rate_limits,
        "pagination": pagination,
        "stats": stats,
        "suggested_commands": suggestions,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze raw-traffic.json and produce structured traffic analysis"
    )
    parser.add_argument(
        "input",
        help="Path to raw-traffic.json (output of parse-trace.py)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: print to stdout)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print human-readable summary instead of JSON",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        entries = json.loads(input_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(
            f"Error: failed to parse {input_path}: {exc}\n"
            f"Ensure this is the JSON output of parse-trace.py.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not isinstance(entries, list):
        print("Error: input must be a JSON array of request entries", file=sys.stderr)
        sys.exit(1)

    report = analyze(entries)

    if args.summary:
        # Human-readable summary
        p = report["protocol"]
        a = report["auth"]
        s = report["stats"]
        print(f"=== Traffic Analysis ===")
        print(f"Requests: {s['total_requests']} ({s['read_operations']} reads, {s['write_operations']} writes)")
        print(f"Read-only: {s['is_read_only']}")
        print(f"Protocol: {p['protocol']} (confidence: {p['confidence']}%)")
        print(f"Auth: {a['primary']} ({', '.join(f'{k}:{v}%' for k,v in a['patterns'].items())})")
        if p.get("graphql_operations"):
            print(f"GraphQL operations: {', '.join(op['name'] for op in p['graphql_operations'])}")
        if p.get("batchexecute_rpc_ids"):
            print(f"batchexecute RPC IDs: {', '.join(p['batchexecute_rpc_ids'])}")
        if p.get("batchexecute_service"):
            print(f"batchexecute service: {p['batchexecute_service']}")
        if p.get("batchexecute_rpc_details"):
            for rid, detail in list(p["batchexecute_rpc_details"].items())[:5]:
                params_list = detail.get("example_params", ["?"])
                params_preview = str(params_list[0] if params_list else "?")[:80]
                variants = f", {len(params_list)} variant(s)" if len(params_list) > 1 else ""
                print(f"  {rid} ({detail.get('call_count', '?')}x{variants}): {params_preview}")
        if p.get("websocket_subprotocols"):
            print(f"WebSocket sub-protocols: {', '.join(p['websocket_subprotocols'])}")
        if p.get("websocket_library"):
            print(f"WebSocket library: {p['websocket_library']}")
        if report["protections"]["has_protection"]:
            print(f"Protections: {', '.join(report['protections']['protections'].keys())}")
            print(f"Recommended client: {report['protections']['recommended_client']}")
        if report["pagination"]["has_pagination"]:
            ep_list = ", ".join(ep["prefix"] for ep in report["pagination"]["paginated_endpoints"][:3])
            print(f"Pagination detected: {ep_list}")
        if report["rate_limits"]["has_rate_limiting"]:
            print(f"Rate limiting: {report['rate_limits']['status_429_count']} x 429 responses")
        print(f"Domains: {', '.join(s['unique_domains'][:5])}")
        print(f"\nEndpoint groups ({len(report['endpoints'])}):")
        for g in report["endpoints"][:10]:
            methods = ", ".join(f"{m}:{c}" for m, c in g["methods"].items())
            print(f"  {g['prefix']} ({g['count']} reqs, {methods})")
        if report["suggested_commands"]:
            print(f"\nSuggested CLI commands:")
            for sg in report["suggested_commands"][:8]:
                cmds = ", ".join(c["name"] for c in sg["commands"])
                print(f"  {sg['group']}: {cmds}")
    else:
        output_json = json.dumps(report, indent=2, default=str)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_json, encoding="utf-8")
            print(f"Analysis written to {output_path}", file=sys.stderr)
        else:
            print(output_json)


if __name__ == "__main__":
    main()
