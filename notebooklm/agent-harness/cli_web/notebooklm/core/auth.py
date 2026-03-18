"""Authentication management for NotebookLM CLI.

Handles cookie storage, token extraction, and session management.
Supports three login methods:
1. Playwright browser login (default, for end users)
2. CDP cookie extraction from Chrome debug profile (--from-browser)
3. Manual JSON cookie import (--cookies-json)
"""

import json
import os
import re
import stat
from pathlib import Path

import httpx

from cli_web.notebooklm.core.rpc.types import HOMEPAGE_URL, WIZ_KEYS


def get_config_dir() -> Path:
    """Get the config directory for storing auth data."""
    config_dir = Path.home() / ".config" / "cli-web-notebooklm"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_auth_path() -> Path:
    """Get the path to the auth.json file."""
    return get_config_dir() / "auth.json"


def save_cookies(cookies: list[dict], path: Path | None = None):
    """Save cookies to auth.json with restricted permissions.

    Args:
        cookies: List of cookie dicts with at least 'name' and 'value'.
        path: Optional custom path. Defaults to standard auth.json location.
    """
    auth_path = path or get_auth_path()
    auth_path.write_text(json.dumps(cookies, indent=2, ensure_ascii=False))
    try:
        os.chmod(str(auth_path), stat.S_IRUSR | stat.S_IWUSR)  # 600
    except OSError:
        pass  # Windows may not support chmod


def load_cookies(path: Path | None = None) -> list[dict]:
    """Load cookies from auth.json.

    Returns:
        List of cookie dicts, or empty list if not found.
    """
    auth_path = path or get_auth_path()
    if not auth_path.exists():
        return []
    try:
        data = json.loads(auth_path.read_text())
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def cookies_to_header(cookies: list[dict], target_domain: str = "notebooklm.google.com") -> str:
    """Convert cookie list to a Cookie header string for a target domain.

    Filters cookies by domain match and deduplicates by name,
    preferring .google.com domain over subdomain cookies to avoid CookieMismatch.
    """
    # Filter cookies that would be sent to the target domain
    matching = []
    for c in cookies:
        domain = c.get("domain", "")
        # .google.com matches notebooklm.google.com
        # notebooklm.google.com matches exactly
        # .notebooklm.google.com matches notebooklm.google.com
        if (
            domain == target_domain
            or domain == f".{target_domain}"
            or (domain.startswith(".") and target_domain.endswith(domain))
        ):
            matching.append(c)

    # Deduplicate by name, preferring broader domain
    seen = {}
    for c in matching:
        name = c.get("name", "")
        domain = c.get("domain", "")
        if name in seen:
            existing_domain = seen[name].get("domain", "")
            # Prefer .google.com over .notebooklm.google.com
            if len(domain) < len(existing_domain):
                seen[name] = c
        else:
            seen[name] = c

    return "; ".join(f"{c['name']}={c['value']}" for c in seen.values())


def check_required_cookies(cookies: list[dict]) -> tuple[bool, list[str]]:
    """Check if required cookies are present.

    Returns:
        (all_present, missing_names)
    """
    required = {"SID", "HSID", "SSID", "OSID"}
    names = {c.get("name") for c in cookies}
    missing = required - names
    return len(missing) == 0, sorted(missing)


def extract_tokens_from_html(html: str) -> dict:
    """Extract WIZ_global_data tokens from page HTML.

    Returns:
        Dict with 'at', 'bl', 'fsid' keys (values may be None).
    """
    tokens = {}
    for key, wiz_key in WIZ_KEYS.items():
        pattern = rf'"{wiz_key}":"([^"]+)"'
        match = re.search(pattern, html)
        tokens[key] = match.group(1) if match else None
    return tokens


def fetch_tokens(cookies: list[dict]) -> dict:
    """Fetch the homepage and extract dynamic tokens.

    Args:
        cookies: List of cookie dicts for authentication.

    Returns:
        Dict with 'at', 'bl', 'fsid' keys.

    Raises:
        RuntimeError: If token extraction fails.
    """
    cookie_header = cookies_to_header(cookies)
    headers = {
        "cookie": cookie_header,
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36"
        ),
    }
    resp = httpx.get(HOMEPAGE_URL, headers=headers, follow_redirects=True, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch NotebookLM homepage: HTTP {resp.status_code}"
        )

    tokens = extract_tokens_from_html(resp.text)
    if not tokens.get("at"):
        raise RuntimeError(
            "Could not extract CSRF token from NotebookLM page. "
            "Cookies may be expired. Re-run: cli-web-notebooklm auth login"
        )
    return tokens


async def login_with_playwright(storage_path: Path | None = None):
    """Open a browser for manual login, then save cookies.

    Requires: pip install playwright
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright not installed. Run: pip install 'cli-web-notebooklm[browser]'"
        )

    storage_path = storage_path or (get_config_dir() / "storage_state.json")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(HOMEPAGE_URL)

        input(
            "\n  Log in to NotebookLM in the browser window.\n"
            "  Press ENTER here when done..."
        )

        await context.storage_state(path=str(storage_path))
        await browser.close()

    # Convert storage state to our cookie format
    state = json.loads(storage_path.read_text())
    cookies = state.get("cookies", [])
    save_cookies(cookies)
    return cookies


async def login_from_browser(port: int = 9222):
    """Extract cookies from Chrome debug profile via CDP.

    Requires: pip install websockets
    """
    try:
        import websockets
    except ImportError:
        raise RuntimeError(
            "websockets not installed. Run: pip install websockets"
        )

    # Get page targets (page-level CDP has cookies, browser-level doesn't)
    try:
        pages_resp = httpx.get(f"http://localhost:{port}/json", timeout=5)
    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot connect to Chrome on port {port}. "
            f"Launch Chrome with: chrome --remote-debugging-port={port}"
        )

    if pages_resp.status_code != 200:
        raise RuntimeError(
            f"Cannot connect to Chrome on port {port}. "
            f"Launch Chrome with: chrome --remote-debugging-port={port}"
        )

    pages = pages_resp.json()
    # Prefer a NotebookLM page, fall back to any page
    target = None
    for p in pages:
        if "notebooklm" in p.get("url", ""):
            target = p
            break
    if not target and pages:
        target = pages[0]
    if not target:
        raise RuntimeError("No browser pages found. Open a tab in Chrome first.")

    ws_url = target["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        # Enable Network domain to access cookies
        await ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        await ws.recv()

        # Get cookies specifically for notebooklm.google.com
        # (this returns only cookies the browser would send to this URL)
        await ws.send(json.dumps({
            "id": 2,
            "method": "Network.getCookies",
            "params": {"urls": ["https://notebooklm.google.com/"]},
        }))
        result = json.loads(await ws.recv())

    all_cookies = result.get("result", {}).get("cookies", [])

    cookies = []
    for c in all_cookies:
        cookies.append({
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
        })

    # Deduplicate: prefer .google.com over accounts.google.com
    seen = {}
    for c in cookies:
        name = c["name"]
        if name in seen:
            if c["domain"].startswith(".") and not seen[name]["domain"].startswith("."):
                seen[name] = c
            elif len(c["domain"]) < len(seen[name]["domain"]):
                seen[name] = c
        else:
            seen[name] = c

    deduped = list(seen.values())
    save_cookies(deduped)
    return deduped


def login_from_json(json_path: str):
    """Import cookies from a JSON file.

    Args:
        json_path: Path to a JSON file containing cookie array.

    Returns:
        List of imported cookies.
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Cookie file not found: {json_path}")

    cookies = json.loads(path.read_text())
    if not isinstance(cookies, list):
        raise ValueError("Cookie file must contain a JSON array of cookie objects")

    save_cookies(cookies)
    return cookies


def logout():
    """Remove stored authentication data."""
    auth_path = get_auth_path()
    if auth_path.exists():
        auth_path.unlink()

    storage_path = get_config_dir() / "storage_state.json"
    if storage_path.exists():
        storage_path.unlink()
