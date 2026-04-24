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
- Request sequence & auth flow detection (via timestamps)
- Session/cookie lifecycle analysis (via request_cookies/response_cookies)
- Endpoint size classification (via response_body_size)

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

# Ensure sibling modules resolve whether invoked as a script or via importlib.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from traffic_utils import is_noise_url as _is_noise_url  # noqa: E402
from traffic_utils import normalize_headers as _normalize_headers  # noqa: E402


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
        url = (e.get("url") or "")
        method = e.get("method", "GET")
        mime = e.get("mime_type", "")
        body = e.get("post_data", "") or ""
        headers = _normalize_headers(e.get("request_headers", {}))
        resp_headers = _normalize_headers(e.get("response_headers", {}))
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

        # --- REST --- resource-style URLs or JSON responses to GET/POST
        is_rest_candidate = False
        if not is_noise:
            # Explicit /api/ prefix (strong signal)
            if re.match(r".*/api/v\d+/", url) or "/api/" in url:
                is_rest_candidate = True
            # JSON response to a non-noise request without matching another protocol
            elif mime and "json" in mime.lower() and method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                is_rest_candidate = True
        if is_rest_candidate:
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

    for e in (e for e in entries if not _is_noise_url((e.get("url") or ""))):
        headers = _normalize_headers(e.get("request_headers", {}))
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
    total = sum(1 for _ in (e for e in entries if not _is_noise_url((e.get("url") or "")))) or 1
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
        req_headers = _normalize_headers(e.get("request_headers", {}))
        headers = _normalize_headers(e.get("response_headers", {}))
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
    mime = (entry.get("mime_type") or "").split(";")[0].strip().lower()
    if any(mime.startswith(p) for p in _STATIC_MIME_PREFIXES):
        return True
    url = (entry.get("url") or "").split("?")[0].lower()
    if any(url.endswith(ext) for ext in _STATIC_EXTENSIONS):
        return True
    return False


def group_endpoints(entries: list[dict]) -> list[dict]:
    """Group API requests by URL prefix into resource groups."""
    api_entries = [
        e for e in entries
        if not _is_noise_url((e.get("url") or "")) and not _is_static_asset(e)
    ]

    # Parse URLs and group by prefix
    groups = defaultdict(lambda: {"methods": Counter(), "urls": set(), "count": 0})

    for e in api_entries:
        url = (e.get("url") or "")
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
        url = (e.get("url") or "")
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
        headers = _normalize_headers(e.get("response_headers", {}))

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
    api_entries = [e for e in entries if not _is_noise_url((e.get("url") or ""))]

    methods = Counter(e.get("method", "GET") for e in api_entries)
    statuses = Counter(e.get("status", 0) for e in api_entries)
    mime_types = Counter(e.get("mime_type", "").split(";")[0].strip() for e in api_entries)

    writes = sum(methods.get(m, 0) for m in ("POST", "PUT", "PATCH", "DELETE"))
    reads = methods.get("GET", 0)

    # Unique domains (from all entries, including noise — useful for awareness)
    domains = set()
    for e in entries:
        parsed = urlparse((e.get("url") or ""))
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


_AUTH_ENDPOINT_PATTERNS = re.compile(
    r'/(login|auth|oauth|token|signin|sign-in|sso|callback|authorize)', re.I
)
_AUTH_COOKIE_NAMES = re.compile(
    r'(session|auth|token|sid|jwt|access|refresh|id_token|csrftoken|_csrf)', re.I
)


def detect_request_sequence(entries: list[dict]) -> dict:
    """Use timestamp field to detect auth flows, redirect chains, and request ordering."""
    # Check if timestamps are available and numeric
    def _ts(e: dict) -> float | None:
        v = e.get("timestamp")
        if isinstance(v, (int, float)):
            return float(v)
        return None

    has_timestamps = any(_ts(e) is not None for e in entries)
    if not has_timestamps:
        return {"has_timestamps": False}

    # Sort entries by timestamp (only entries with valid numeric timestamps)
    timed = [e for e in entries if _ts(e) is not None]
    timed.sort(key=lambda e: _ts(e) or 0)

    # --- Request timeline (first 20) ---
    timeline = []
    prev_ts = _ts(timed[0]) or 0 if timed else 0
    for i, e in enumerate(timed[:20]):
        ts = _ts(e) or 0
        delta_ms = round((ts - prev_ts) * 1000, 1) if i > 0 else 0
        url = (e.get("url") or "")
        timeline.append({
            "seq": i + 1,
            "method": e.get("method", "GET"),
            "url": url[:80],
            "status": e.get("status", 0),
            "delta_ms": delta_ms,
        })
        prev_ts = ts

    # --- Auth flow detection ---
    auth_flow = {"detected": False, "steps": []}
    # Track which cookies are set by responses
    session_cookies_set = {}  # cookie_name -> seq number where it was set

    for i, e in enumerate(timed):
        seq = i + 1
        url = (e.get("url") or "")
        method = e.get("method", "GET")
        status = e.get("status", 0)
        resp_cookies = e.get("response_cookies", []) or []

        # Check if this is a login/auth request
        is_auth_endpoint = bool(_AUTH_ENDPOINT_PATTERNS.search(url))
        is_auth_post = is_auth_endpoint and method == "POST"

        # Check if response sets auth cookies
        auth_cookies_set = []
        for rc in resp_cookies:
            name = rc.get("name", "") if isinstance(rc, dict) else ""
            if _AUTH_COOKIE_NAMES.search(name):
                auth_cookies_set.append(name)
                session_cookies_set[name] = seq

        if is_auth_post or (auth_cookies_set and is_auth_endpoint):
            auth_flow["detected"] = True
            auth_flow["steps"].append({
                "seq": seq,
                "action": "login",
                "url": url[:80],
                "cookies_set": auth_cookies_set if auth_cookies_set else [],
            })
        elif session_cookies_set:
            # Check if this request uses cookies that were set by an auth step
            req_cookies = e.get("request_cookies", {}) or {}
            used = [name for name in req_cookies if name in session_cookies_set]
            if used and not _is_noise_url(url):
                auth_flow["steps"].append({
                    "seq": seq,
                    "action": "api_call",
                    "url": url[:80],
                    "cookies_used": used,
                })
                # Only keep first 10 api_call steps to avoid huge output
                if len(auth_flow["steps"]) > 15:
                    break

    # --- Redirect chains (follow Location headers, not array adjacency) ---
    redirect_chains = []
    # Build a map of URL → entry for redirect target matching
    url_to_entry = {}
    for e in timed:
        url_to_entry.setdefault((e.get("url") or ""), e)

    visited_redirects: set[str] = set()
    for e in timed:
        url = (e.get("url") or "")
        status = e.get("status", 0)
        if status not in (301, 302, 303, 307, 308):
            continue
        if url in visited_redirects:
            continue

        # Follow the chain via Location headers
        chain_start = url
        chain_hops = 0
        location = ""
        current = e
        while current:
            current_url = current.get("url", "")
            current_status = current.get("status", 0)
            if current_status not in (301, 302, 303, 307, 308):
                break
            visited_redirects.add(current_url)
            chain_hops += 1
            resp_headers = _normalize_headers(current.get("response_headers", {}))
            location = resp_headers.get("location", resp_headers.get("Location", ""))
            if not location:
                break
            # Resolve relative Location
            if location.startswith("/"):
                parsed_curr = urlparse(current_url)
                location = f"{parsed_curr.scheme}://{parsed_curr.netloc}{location}"
            current = url_to_entry.get(location)

        if chain_hops >= 1:
            # Final destination is the last Location or the last entry's URL
            final_url = location if location else chain_start
            redirect_chains.append({
                "from": chain_start[:120],
                "to": final_url[:120],
                "hops": chain_hops,
            })

    return {
        "has_timestamps": True,
        "request_timeline": timeline,
        "auth_flow": auth_flow,
        "redirect_chains": redirect_chains,
    }


def detect_session_lifecycle(entries: list[dict]) -> dict:
    """Analyze cookie flow: which cookies are set and used, and identify auth cookies."""
    has_cookie_data = any(
        e.get("request_cookies") is not None or e.get("response_cookies") is not None
        for e in entries
    )
    if not has_cookie_data:
        return {"has_cookie_data": False}

    cookies_set = []  # list of {name, set_by, domain}
    cookies_used = defaultdict(lambda: {"count": 0, "first_used": None})
    seen_set = set()  # dedupe (name, domain) for cookies_set list

    for e in entries:
        url = (e.get("url") or "")
        parsed = urlparse(url)
        domain = parsed.hostname or ""

        # Response cookies (Set-Cookie)
        resp_cookies = e.get("response_cookies", []) or []
        for rc in resp_cookies:
            name = rc.get("name", "") if isinstance(rc, dict) else ""
            if not name:
                continue
            key = (name, domain)
            if key not in seen_set:
                seen_set.add(key)
                cookies_set.append({
                    "name": name,
                    "set_by": url[:120],
                    "domain": domain,
                })

        # Request cookies (sent with request)
        req_cookies = e.get("request_cookies", {}) or {}
        for name in req_cookies:
            entry = cookies_used[name]
            entry["count"] += 1
            if entry["first_used"] is None:
                entry["first_used"] = url[:120]

    # Identify auth cookies
    all_cookie_names = set(c["name"] for c in cookies_set) | set(cookies_used.keys())
    auth_cookies = sorted(
        name for name in all_cookie_names
        if _AUTH_COOKIE_NAMES.search(name)
    )

    # Determine session pattern
    if not cookies_set and not cookies_used:
        session_pattern = "no_session"
    elif auth_cookies:
        # Check if auth cookies are refreshed (set multiple times across different URLs)
        auth_set_count = sum(1 for c in cookies_set if c["name"] in auth_cookies)
        if auth_set_count > len(auth_cookies):
            session_pattern = "token_refresh"
        else:
            session_pattern = "cookie_auth"
    else:
        session_pattern = "tracking_only"

    return {
        "has_cookie_data": True,
        "cookies_set": cookies_set[:30],  # cap output
        "cookies_used": {k: v for k, v in list(cookies_used.items())[:30]},
        "auth_cookies": auth_cookies,
        "session_pattern": session_pattern,
    }


def classify_endpoints_by_size(entries: list[dict]) -> dict:
    """Classify endpoint groups by response body size."""
    has_size_data = any(e.get("response_body_size") is not None for e in entries)
    if not has_size_data:
        return {"has_size_data": False}

    total_bytes = 0
    largest = {"url": "", "size": 0}
    size_distribution = {"large": 0, "medium": 0, "small": 0, "zero": 0}

    # Group sizes by endpoint prefix (reuse grouping logic)
    prefix_sizes = defaultdict(list)

    for e in entries:
        size = e.get("response_body_size")
        if size is None:
            continue

        url = (e.get("url") or "")
        if _is_noise_url(url) or _is_static_asset(e):
            continue

        total_bytes += size

        if size > largest["size"]:
            largest = {"url": url[:120], "size": size}

        # Classify
        if size == 0:
            size_distribution["zero"] += 1
        elif size < 1024:
            size_distribution["small"] += 1
        elif size <= 51200:
            size_distribution["medium"] += 1
        else:
            size_distribution["large"] += 1

        # Group by prefix
        parsed = urlparse(url)
        host = parsed.hostname or ""
        segments = [_normalize_segment(s) for s in parsed.path.strip("/").split("/") if s]
        if len(segments) >= 2:
            prefix = f"{host}/{segments[0]}/{segments[1]}"
        elif segments:
            prefix = f"{host}/{segments[0]}"
        else:
            prefix = host
        prefix_sizes[prefix].append(size)

    # Compute per-prefix averages
    endpoint_sizes = []
    for prefix, sizes in sorted(prefix_sizes.items(), key=lambda x: -sum(x[1])):
        avg = int(sum(sizes) / len(sizes)) if sizes else 0
        if avg == 0:
            classification = "empty"
        elif avg < 1024:
            classification = "small (<1KB)"
        elif avg <= 51200:
            classification = "medium (1-50KB)"
        else:
            classification = "large (>50KB)"
        endpoint_sizes.append({
            "prefix": prefix,
            "avg_size": avg,
            "classification": classification,
        })

    return {
        "has_size_data": True,
        "total_data_bytes": total_bytes,
        "largest_response": largest,
        "endpoint_sizes": endpoint_sizes[:20],
        "size_distribution": size_distribution,
    }


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
    request_sequence = detect_request_sequence(entries)
    session_lifecycle = detect_session_lifecycle(entries)
    endpoint_sizes = classify_endpoints_by_size(entries)

    return {
        "_meta": {
            "tool": "analyze-traffic.py",
            "version": "1.3.0",
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
        "request_sequence": request_sequence,
        "session_lifecycle": session_lifecycle,
        "endpoint_sizes": endpoint_sizes,
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

        # Request sequence
        seq = report.get("request_sequence", {})
        if seq.get("has_timestamps"):
            print(f"\nRequest sequence: {len(seq.get('request_timeline', []))} requests in timeline")
            if seq.get("auth_flow", {}).get("detected"):
                steps = seq["auth_flow"]["steps"]
                login_steps = [s for s in steps if s["action"] == "login"]
                api_steps = [s for s in steps if s["action"] == "api_call"]
                print(f"  Auth flow: {len(login_steps)} login step(s), {len(api_steps)} authenticated API call(s)")
            if seq.get("redirect_chains"):
                for chain in seq["redirect_chains"][:3]:
                    print(f"  Redirect: {chain['from'][:60]} -> {chain['to'][:60]} ({chain['hops']} hops)")

        # Session lifecycle
        sess = report.get("session_lifecycle", {})
        if sess.get("has_cookie_data"):
            print(f"\nSession lifecycle: pattern={sess.get('session_pattern', 'unknown')}")
            if sess.get("auth_cookies"):
                print(f"  Auth cookies: {', '.join(sess['auth_cookies'][:10])}")
            print(f"  Cookies set: {len(sess.get('cookies_set', []))}, Cookies used: {len(sess.get('cookies_used', {}))}")

        # Endpoint sizes
        esz = report.get("endpoint_sizes", {})
        if esz.get("has_size_data"):
            dist = esz.get("size_distribution", {})
            total_kb = esz.get("total_data_bytes", 0) / 1024
            print(f"\nEndpoint sizes: {total_kb:.1f} KB total")
            print(f"  Distribution: {dist.get('large', 0)} large, {dist.get('medium', 0)} medium, {dist.get('small', 0)} small, {dist.get('zero', 0)} zero")
            if esz.get("largest_response", {}).get("size", 0) > 0:
                lr = esz["largest_response"]
                print(f"  Largest: {lr['url'][:60]} ({lr['size']} bytes)")
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
