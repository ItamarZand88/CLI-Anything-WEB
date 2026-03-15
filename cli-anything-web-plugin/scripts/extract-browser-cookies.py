#!/usr/bin/env python3
"""Extract auth cookies from the Chrome debug profile via CDP.

Connects to Chrome's remote debugging port and extracts cookies for a
given domain. Use this instead of manually copying cookies from DevTools.

Prerequisites:
    pip install websockets

Usage:
    # Extract Google cookies (for NotebookLM, etc.)
    python extract-browser-cookies.py --domain .google.com --save ~/.config/cli-web-notebooklm/auth.json

    # Just print cookies without saving
    python extract-browser-cookies.py --domain .google.com

    # Custom port
    python extract-browser-cookies.py --port 9222 --domain .monday.com
"""

import argparse
import asyncio
import json
import http.client
import os
import sys
from pathlib import Path


def get_ws_url(port: int) -> str:
    """Get the WebSocket debugger URL from Chrome's debug port."""
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/json/version")
        resp = conn.getresponse()
        if resp.status != 200:
            print(f"Error: Chrome debug port returned status {resp.status}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(resp.read())
        return data["webSocketDebuggerUrl"]
    except ConnectionRefusedError:
        print(
            f"Error: Cannot connect to Chrome on port {port}.\n"
            f"Launch Chrome with: chrome --remote-debugging-port={port} "
            f'--user-data-dir="$HOME/.chrome-debug-profile"',
            file=sys.stderr,
        )
        sys.exit(1)


async def extract_cookies(ws_url: str, domain: str) -> dict[str, str]:
    """Connect to Chrome via CDP and extract cookies for the given domain."""
    try:
        import websockets
    except ImportError:
        print(
            "Error: 'websockets' package required.\n"
            "Install with: pip install websockets",
            file=sys.stderr,
        )
        sys.exit(1)

    async with websockets.connect(ws_url) as ws:
        # Use Storage.getCookies CDP command
        await ws.send(json.dumps({
            "id": 1,
            "method": "Storage.getCookies",
        }))
        response = json.loads(await ws.recv())
        all_cookies = response.get("result", {}).get("cookies", [])

        # Filter by domain
        matched = {}
        for cookie in all_cookies:
            cookie_domain = cookie.get("domain", "")
            if domain in cookie_domain or cookie_domain.endswith(domain):
                matched[cookie["name"]] = cookie["value"]

        return matched


def save_cookies(cookies: dict, path: str) -> None:
    """Save cookies to a JSON file with secure permissions."""
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(cookies, indent=2))

    # Secure file permissions (Unix only)
    try:
        os.chmod(filepath, 0o600)
    except OSError:
        pass  # Windows doesn't support chmod 600

    print(f"Saved {len(cookies)} cookies to {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract auth cookies from Chrome debug profile"
    )
    parser.add_argument(
        "--port", type=int, default=9222,
        help="Chrome remote debugging port (default: 9222)",
    )
    parser.add_argument(
        "--domain", required=True,
        help="Cookie domain to filter (e.g., .google.com, .monday.com)",
    )
    parser.add_argument(
        "--save", metavar="PATH",
        help="Save cookies to this JSON file (e.g., ~/.config/cli-web-notebooklm/auth.json)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print cookies as JSON to stdout",
    )
    args = parser.parse_args()

    ws_url = get_ws_url(args.port)
    cookies = asyncio.run(extract_cookies(ws_url, args.domain))

    if not cookies:
        print(f"No cookies found for domain '{args.domain}'", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(cookies)} cookies for {args.domain}")

    if args.save:
        save_cookies(cookies, args.save)
    elif args.json:
        print(json.dumps(cookies, indent=2))
    else:
        # Print summary (not values — those are sensitive)
        for name in sorted(cookies):
            val_preview = cookies[name][:8] + "..." if len(cookies[name]) > 8 else cookies[name]
            print(f"  {name}: {val_preview}")
        print(f"\nUse --save <path> to save, or --json to print full values")


if __name__ == "__main__":
    main()
