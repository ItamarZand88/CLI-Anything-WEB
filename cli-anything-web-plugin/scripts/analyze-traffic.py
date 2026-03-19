#!/usr/bin/env python3
"""Analyze raw-traffic.json and produce a structured traffic analysis report.

Reads the output of parse-trace.py and auto-detects:
- API protocol type (REST, GraphQL, batchexecute, SSR, etc.)
- Authentication pattern (Bearer, Cookie, API key, none)
- Endpoint grouping by URL prefix
- GraphQL operation names and types
- Rate limit signals (429s, Retry-After headers)
- Protection/WAF signals (Cloudflare, CAPTCHA)
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


def detect_protocol(entries: list[dict]) -> dict:
    """Detect the API protocol type from traffic patterns."""
    signals = {
        "graphql": 0,
        "batchexecute": 0,
        "rest": 0,
        "grpc_web": 0,
        "ssr_html": 0,
    }

    graphql_ops = []
    batchexecute_methods = []

    for e in entries:
        url = e.get("url", "")
        method = e.get("method", "GET")
        mime = e.get("mime_type", "")
        body = e.get("post_data", "") or ""
        headers = e.get("request_headers", {})
        content_type = headers.get("content-type", headers.get("Content-Type", ""))

        # GraphQL detection
        if "/graphql" in url.lower():
            signals["graphql"] += 3
            # Extract operation name
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
                    op_type = "mutation" if "mutation" in query[:50].lower() else "query"
                    if op:
                        graphql_ops.append({"name": op, "type": op_type, "method": "POST"})
                except (json.JSONDecodeError, TypeError):
                    pass

        # batchexecute detection
        if "batchexecute" in url:
            signals["batchexecute"] += 3
            if "rpcids=" in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                rpcid = params.get("rpcids", [""])[0]
                if rpcid:
                    batchexecute_methods.append(rpcid)

        # gRPC-Web detection
        if "application/grpc" in content_type:
            signals["grpc_web"] += 3

        # REST detection — resource-style URLs with standard methods
        if re.match(r".*/api/v\d+/", url) or "/api/" in url:
            signals["rest"] += 1

        # SSR/HTML detection
        if "text/html" in mime and method == "GET":
            signals["ssr_html"] += 0.5

    # Determine primary protocol
    if not entries:
        return {"protocol": "unknown", "confidence": 0, "signals": signals}

    max_signal = max(signals, key=signals.get)
    max_value = signals[max_signal]
    total = sum(signals.values()) or 1

    # If no strong signal, check if it's mostly HTML
    if max_value == 0:
        protocol = "unknown"
        confidence = 0
    elif max_signal == "ssr_html" and signals["ssr_html"] > 0 and signals["rest"] == 0 and signals["graphql"] == 0:
        protocol = "ssr_html"
        confidence = min(signals["ssr_html"] / total * 100, 95)
    else:
        protocol = max_signal
        confidence = min(max_value / total * 100, 99)

    result = {
        "protocol": protocol,
        "confidence": round(confidence, 1),
        "signals": {k: round(v, 1) for k, v in signals.items() if v > 0},
    }

    if graphql_ops:
        # Deduplicate
        seen = set()
        unique_ops = []
        for op in graphql_ops:
            key = (op["name"], op["type"])
            if key not in seen:
                seen.add(key)
                unique_ops.append(op)
        result["graphql_operations"] = unique_ops

    if batchexecute_methods:
        result["batchexecute_rpc_ids"] = list(set(batchexecute_methods))

    return result


def detect_auth(entries: list[dict]) -> dict:
    """Detect authentication pattern from request headers."""
    bearer_count = 0
    cookie_count = 0
    api_key_count = 0
    no_auth_count = 0

    api_key_headers = set()
    cookie_names = set()

    for e in entries:
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

    total = len(entries) or 1
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
        "captcha": False,
        "rate_limited": False,
    }
    details = []

    for e in entries:
        status = e.get("status", 0)
        headers = e.get("response_headers", {})
        body = e.get("response_body", "")
        body_str = str(body)[:2000].lower() if body else ""

        # Cloudflare
        if headers.get("cf-ray") or headers.get("CF-RAY"):
            protections["cloudflare"] = True
        if "just a moment" in body_str and "cloudflare" in body_str:
            protections["cloudflare"] = True
            details.append("Cloudflare challenge page detected")

        # CAPTCHA
        if any(x in body_str for x in ["g-recaptcha", "h-captcha", "px-captcha"]):
            protections["captcha"] = True
            details.append("CAPTCHA detected in response")

        # Rate limiting
        if status == 429:
            protections["rate_limited"] = True
            retry_after = headers.get("retry-after", headers.get("Retry-After", ""))
            details.append(f"429 Too Many Requests (Retry-After: {retry_after or 'not specified'})")

    return {
        "protections": {k: v for k, v in protections.items() if v},
        "details": details,
        "has_protection": any(protections.values()),
    }


def group_endpoints(entries: list[dict]) -> list[dict]:
    """Group API requests by URL prefix into resource groups."""
    # Filter to API-like URLs (skip tracking, CDN, analytics, ads)
    NOISE_PATTERNS = [
        "/analytics", "/pixel", "/beacon", "/rum", "/collect",
        "google-analytics", "googletagmanager.com", "cdn-cgi/",
        "facebook.com", "twitter.com", "doubleclick.net",
        "googlesyndication", "google.com/ads", "google.co.",
        "gstatic.com", "googleapis.com/css", "datadoghq.com",
        "cloudflareinsights.com", "cookiebot.com", "segment.prod",
        "bidr.io", "liftdsp.com", "statcounter.com",
        "play.google.com/log", "signaler-pa.clients6",
        "/manifest.json", "drainpaste.com", "slinksuggestion.com",
        "avatars.githubusercontent.com",
    ]
    api_entries = []
    for e in entries:
        url = e.get("url", "")
        if any(x in url for x in NOISE_PATTERNS):
            continue
        api_entries.append(e)

    # Parse URLs and group by prefix
    groups = defaultdict(lambda: {"methods": Counter(), "urls": set(), "count": 0})

    for e in api_entries:
        url = e.get("url", "")
        method = e.get("method", "GET")
        parsed = urlparse(url)

        # Determine group key: use first 2-3 path segments
        path = parsed.path.rstrip("/")
        segments = [s for s in path.split("/") if s]

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
    """Compute basic traffic statistics."""
    methods = Counter(e.get("method", "GET") for e in entries)
    statuses = Counter(e.get("status", 0) for e in entries)
    mime_types = Counter(e.get("mime_type", "").split(";")[0].strip() for e in entries)

    writes = sum(methods.get(m, 0) for m in ("POST", "PUT", "PATCH", "DELETE"))
    reads = methods.get("GET", 0)

    # Unique domains
    domains = set()
    for e in entries:
        parsed = urlparse(e.get("url", ""))
        if parsed.hostname:
            domains.add(parsed.hostname)

    return {
        "total_requests": len(entries),
        "read_operations": reads,
        "write_operations": writes,
        "is_read_only": writes == 0 or all(
            # Check if writes are just analytics/tracking
            any(x in e.get("url", "") for x in ["/analytics", "/pixel", "/beacon", "/rum", "cdn-cgi/", "/t/", "/e/"])
            for e in entries if e.get("method") in ("POST", "PUT", "PATCH", "DELETE")
        ),
        "methods": dict(methods),
        "status_codes": dict(statuses),
        "top_mime_types": dict(mime_types.most_common(5)),
        "unique_domains": sorted(domains),
    }


def suggest_commands(endpoint_groups: list[dict], protocol: dict) -> list[dict]:
    """Suggest CLI command groups based on endpoint patterns."""
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
    stats = compute_stats(entries)
    suggestions = suggest_commands(endpoints, protocol)

    return {
        "_meta": {
            "tool": "analyze-traffic.py",
            "version": "1.0.0",
            "description": "Auto-generated traffic analysis. Fields marked 'unknown' need manual agent analysis.",
        },
        "protocol": protocol,
        "auth": auth,
        "protections": protections,
        "endpoints": endpoints,
        "rate_limits": rate_limits,
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

    entries = json.loads(input_path.read_text(encoding="utf-8"))
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
        if report["protections"]["has_protection"]:
            print(f"Protections: {', '.join(k for k,v in report['protections']['protections'].items() if v)}")
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
