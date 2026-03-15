"""Cookie-based authentication management for NotebookLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Required cookies for Google auth
REQUIRED_COOKIES = [
    "SID", "SSID", "HSID", "OSID", "SAPISID", "NID",
    "__Secure-1PSID", "__Secure-3PSID",
]

# Default config directory
CONFIG_DIR = Path.home() / ".config" / "cli-web-notebooklm"
AUTH_FILE = CONFIG_DIR / "auth.json"


def get_config_dir() -> Path:
    """Return (and create) the configuration directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def get_auth_file() -> Path:
    """Return path to the auth JSON file."""
    get_config_dir()
    return AUTH_FILE


def load_cookies() -> dict[str, str]:
    """Load stored cookies from auth.json.

    Returns:
        Dictionary mapping cookie names to values.

    Raises:
        FileNotFoundError: If auth.json does not exist.
        ValueError: If the auth file is malformed.
    """
    path = get_auth_file()
    if not path.exists():
        raise FileNotFoundError(
            f"Auth file not found: {path}\n"
            "Run 'cli-web-notebooklm auth login' to configure authentication."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    cookies = data.get("cookies", {})
    if not isinstance(cookies, dict):
        raise ValueError("Malformed auth file: 'cookies' must be a dict")
    return cookies


def save_cookies(cookies: dict[str, str]) -> Path:
    """Save cookies to auth.json.

    Args:
        cookies: Dictionary mapping cookie names to values.

    Returns:
        Path to the written auth file.
    """
    path = get_auth_file()
    data = {"cookies": cookies}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def validate_cookies(cookies: dict[str, str]) -> list[str]:
    """Check which required cookies are missing.

    Returns:
        List of missing cookie names (empty if all present).
    """
    return [c for c in REQUIRED_COOKIES if c not in cookies]


def build_cookie_header(cookies: dict[str, str]) -> str:
    """Build an HTTP Cookie header string from a dict."""
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def export_cookies_json(cookies: dict[str, str]) -> str:
    """Export cookies as pretty JSON (for user inspection)."""
    return json.dumps(cookies, indent=2)


def extract_cookies_from_browser(
    domain: str = ".google.com",
    port: int = 9222,
) -> dict[str, str]:
    """Extract cookies from the Chrome debug profile via CDP.

    Connects to Chrome's remote debugging port and retrieves all cookies
    for the given domain. Requires 'websockets' package.

    Args:
        domain: Cookie domain to filter (e.g., ".google.com").
        port: Chrome remote debugging port (default: 9222).

    Returns:
        Dictionary mapping cookie names to values.

    Raises:
        ConnectionRefusedError: If Chrome is not running on the given port.
        ImportError: If 'websockets' is not installed.
    """
    import asyncio
    import http.client

    # Get the WebSocket debugger URL
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/json/version")
    resp = conn.getresponse()
    if resp.status != 200:
        raise ConnectionError(f"Chrome debug port returned status {resp.status}")
    ws_url = json.loads(resp.read())["webSocketDebuggerUrl"]

    async def _extract():
        try:
            import websockets
        except ImportError:
            raise ImportError(
                "'websockets' package required for browser auth.\n"
                "Install with: pip install websockets"
            )
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({
                "id": 1,
                "method": "Storage.getCookies",
            }))
            response = json.loads(await ws.recv())
            all_cookies = response.get("result", {}).get("cookies", [])
            return {
                c["name"]: c["value"]
                for c in all_cookies
                if domain in c.get("domain", "")
            }

    return asyncio.run(_extract())
