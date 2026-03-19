#!/usr/bin/env python3
"""Parse Playwright trace files into raw-traffic.json format.

Reads .network files and resources/ from a playwright-cli trace directory
and produces a filtered JSON array of API request/response entries.

Usage:
    python parse-trace.py <traces-dir> --output raw-traffic.json
    python parse-trace.py .playwright-cli/traces/ --output suno/traffic-capture/raw-traffic.json
    python parse-trace.py .playwright-cli/traces/ --output raw.json --include-static
"""

import argparse
import json
import sys
from pathlib import Path


STATIC_EXTENSIONS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".webp", ".avif",
)


def parse_network_file(network_path: Path, resources_dir: Path, filter_static: bool = True) -> list[dict]:
    """Parse a single .network trace file into request/response entries."""
    entries = []
    text = network_path.read_text(encoding="utf-8").strip()
    if not text:
        return entries

    for line in text.split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        if data.get("type") != "resource-snapshot":
            continue

        snap = data["snapshot"]
        req = snap.get("request", {})
        resp = snap.get("response", {})
        url = req.get("url", "")

        # Filter static assets
        if filter_static:
            url_path = url.split("?")[0].split("#")[0]
            if any(url_path.endswith(ext) for ext in STATIC_EXTENSIONS):
                continue

        # Load response body from resources/
        body = None
        sha1 = resp.get("content", {}).get("_sha1")
        if sha1 and resources_dir.exists():
            body_file = resources_dir / sha1
            if body_file.exists():
                try:
                    body = json.loads(body_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    try:
                        body = body_file.read_text(encoding="utf-8")[:3000]
                    except Exception:
                        body = "[binary content]"

        entries.append({
            "url": url,
            "method": req.get("method", "GET"),
            "request_headers": {
                h["name"]: h["value"]
                for h in req.get("headers", [])
            },
            "post_data": req.get("postData", {}).get("text") if isinstance(req.get("postData"), dict) else req.get("postData"),
            "status": resp.get("status", 0),
            "response_headers": {
                h["name"]: h["value"]
                for h in resp.get("headers", [])
            },
            "response_body": body,
            "mime_type": resp.get("content", {}).get("mimeType", ""),
            "time_ms": round(snap.get("time", 0), 1),
        })

    return entries


def parse_traces(traces_dir: Path, filter_static: bool = True, latest_only: bool = False) -> list[dict]:
    """Parse .network files in a traces directory."""
    traces_dir = Path(traces_dir)
    resources_dir = traces_dir / "resources"

    network_files = sorted(traces_dir.glob("*.network"))
    if not network_files:
        return []

    if latest_only:
        # Only parse the most recent .network file (by modification time)
        network_files = [max(network_files, key=lambda f: f.stat().st_mtime)]

    all_entries = []
    for network_file in network_files:
        entries = parse_network_file(network_file, resources_dir, filter_static)
        all_entries.extend(entries)

    return all_entries


def main():
    parser = argparse.ArgumentParser(
        description="Parse Playwright trace files into raw-traffic.json"
    )
    parser.add_argument(
        "traces_dir",
        help="Path to .playwright-cli/traces/ directory",
    )
    parser.add_argument(
        "--output", "-o",
        default="raw-traffic.json",
        help="Output file path (default: raw-traffic.json)",
    )
    parser.add_argument(
        "--include-static",
        action="store_true",
        help="Include static assets (JS, CSS, images) — filtered by default",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Only parse the most recent trace (ignore older traces in the directory)",
    )
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir)
    if not traces_dir.exists():
        print(f"Error: traces directory not found: {traces_dir}", file=sys.stderr)
        sys.exit(1)

    entries = parse_traces(traces_dir, filter_static=not args.include_static, latest_only=args.latest)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")

    print(f"Parsed {len(entries)} API requests -> {output_path}")

    # Auto-run analysis if analyze-traffic.py is available
    analysis_path = output_path.parent / "traffic-analysis.json"
    analyze_script = Path(__file__).parent / "analyze-traffic.py"
    if analyze_script.exists() and entries:
        try:
            # Import and run inline (same process, no subprocess overhead)
            import importlib.util
            spec = importlib.util.spec_from_file_location("analyze_traffic", analyze_script)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            report = mod.analyze(entries)
            analysis_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
            p = report["protocol"]
            a = report["auth"]
            s = report["stats"]
            print(f"Analysis: protocol={p['protocol']} ({p['confidence']}%), "
                  f"auth={a['primary']}, "
                  f"requests={s['total_requests']} ({s['read_operations']}R/{s['write_operations']}W)")
            if p.get("graphql_operations"):
                ops = [op["name"] for op in p["graphql_operations"]]
                print(f"  GraphQL ops: {', '.join(ops)}")
            if p.get("batchexecute_rpc_ids"):
                print(f"  batchexecute IDs: {', '.join(p['batchexecute_rpc_ids'])}")
            print(f"  -> {analysis_path}")
        except Exception as e:
            print(f"  (analysis skipped: {e})", file=sys.stderr)


if __name__ == "__main__":
    main()
