"""Auth management for FUTBIN CLI.

Most FUTBIN features are public (no auth required).
Auth is only needed for: comments, voting, saved squads, my evolutions.
"""

import json
import os
import stat
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "cli-web-futbin"
AUTH_FILE = CONFIG_DIR / "auth.json"


def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_cookies(cookies: dict):
    """Save cookies to auth.json with restricted permissions."""
    _ensure_config_dir()
    AUTH_FILE.write_text(json.dumps(cookies, indent=2))
    try:
        os.chmod(AUTH_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 600
    except OSError:
        pass  # Windows may not support chmod


def load_cookies() -> Optional[dict]:
    """Load cookies from auth.json."""
    if not AUTH_FILE.exists():
        return None
    try:
        return json.loads(AUTH_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def clear_cookies():
    """Remove stored cookies."""
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def get_auth_status() -> dict:
    """Check current auth status."""
    cookies = load_cookies()
    if cookies is None:
        return {
            "authenticated": False,
            "message": "No cookies stored. Most features work without login.",
            "cookie_count": 0,
        }
    return {
        "authenticated": True,
        "message": "Cookies loaded. Auth features available.",
        "cookie_count": len(cookies),
        "cookie_names": list(cookies.keys()),
    }


async def login_with_playwright(app_url: str = "https://www.futbin.com/account/login"):
    """Login via Playwright browser — user logs in manually."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright not installed. Install with: pip install 'cli-web-futbin[browser]'"
        )

    storage_path = CONFIG_DIR / "storage_state.json"
    _ensure_config_dir()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(app_url)
        input("Log in to FUTBIN in the browser, then press ENTER here...")
        await context.storage_state(path=str(storage_path))

        # Extract cookies for httpx
        cookies_list = await context.cookies()
        cookies = {}
        for c in cookies_list:
            if "futbin.com" in c.get("domain", ""):
                cookies[c["name"]] = c["value"]

        save_cookies(cookies)
        await browser.close()

    return cookies


def login_from_chrome_cdp(host: str = "localhost", port: int = 9222) -> dict:
    """Extract cookies from a running Chrome debug session via CDP."""
    try:
        import websockets  # noqa: F401
    except ImportError:
        raise RuntimeError("websockets not installed. Install with: pip install websockets")

    import http.client
    import json as json_mod

    # Get WebSocket URL from Chrome
    conn = http.client.HTTPConnection(host, port)
    conn.request("GET", "/json")
    resp = conn.getresponse()
    targets = json_mod.loads(resp.read())
    conn.close()

    if not targets:
        raise RuntimeError("No Chrome tabs found on debug port")

    ws_url = targets[0].get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError("No WebSocket URL found")

    # Use synchronous approach to get cookies
    import asyncio

    async def _get_cookies():
        import websockets

        async with websockets.connect(ws_url) as ws:
            # Get all cookies
            await ws.send(json_mod.dumps({
                "id": 1,
                "method": "Network.getAllCookies",
            }))
            result = json_mod.loads(await ws.recv())
            return result.get("result", {}).get("cookies", [])

    cookies_list = asyncio.run(_get_cookies())

    cookies = {}
    seen = set()
    for c in cookies_list:
        domain = c.get("domain", "")
        name = c.get("name", "")
        if "futbin.com" in domain and name not in seen:
            cookies[name] = c["value"]
            seen.add(name)

    if cookies:
        save_cookies(cookies)

    return cookies


def login_from_json_file(file_path: str) -> dict:
    """Import cookies from a JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Cookie file not found: {file_path}")

    data = json.loads(path.read_text())

    # Handle both formats: {name: value} or [{name, value, domain}, ...]
    cookies = {}
    if isinstance(data, list):
        for c in data:
            if isinstance(c, dict) and "name" in c and "value" in c:
                cookies[c["name"]] = c["value"]
    elif isinstance(data, dict):
        cookies = data

    save_cookies(cookies)
    return cookies
