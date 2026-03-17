"""Authentication management for Suno CLI.

Supports three login methods:
1. Playwright browser login (default, for end users)
2. CDP extraction from Chrome debug profile (--from-browser)
3. Manual cookie JSON import (--cookies-json)
"""

import asyncio
import base64
import json
import os
import stat
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx

CONFIG_DIR = Path.home() / ".config" / "cli-web-suno"
AUTH_FILE = CONFIG_DIR / "auth.json"
CLERK_BASE = "https://auth.suno.com"
SUNO_ORIGIN = "https://suno.com"
STUDIO_API = "https://studio-api.prod.suno.com"


def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _make_browser_token() -> str:
    """Generate the browser-token header value."""
    ts = int(time.time() * 1000)
    payload = json.dumps({"timestamp": ts})
    encoded = base64.b64encode(payload.encode()).decode()
    # The actual format from the browser is a JWT-like base64 string
    # but inspection shows it's just base64(json with timestamp)
    return json.dumps({"token": f"eyJ0aW1lc3RhbXAiOnt0c319".replace("{ts}", str(ts))})


def _get_device_id() -> str:
    """Get or create a persistent device ID."""
    _ensure_config_dir()
    device_file = CONFIG_DIR / "device_id"
    if device_file.exists():
        return device_file.read_text().strip()
    device_id = str(uuid.uuid4())
    device_file.write_text(device_id)
    return device_id


def load_auth() -> Optional[dict]:
    """Load stored auth data."""
    if not AUTH_FILE.exists():
        return None
    try:
        data = json.loads(AUTH_FILE.read_text())
        return data
    except (json.JSONDecodeError, OSError):
        return None


def save_auth(data: dict):
    """Save auth data securely."""
    _ensure_config_dir()
    AUTH_FILE.write_text(json.dumps(data, indent=2))
    try:
        os.chmod(AUTH_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass  # Windows may not support chmod 600


def get_jwt() -> Optional[str]:
    """Get the current JWT token, refreshing if needed."""
    auth = load_auth()
    if not auth:
        return None

    jwt = auth.get("jwt")
    if not jwt:
        # Try refreshing from cookies
        jwt = refresh_jwt_from_cookies(auth.get("cookies", []))
        if jwt:
            auth["jwt"] = jwt
            auth["jwt_refreshed_at"] = time.time()
            save_auth(auth)
    return jwt


def refresh_jwt_from_cookies(cookies: list) -> Optional[str]:
    """Refresh JWT by calling Clerk's client endpoint with session cookie."""
    session_cookie = None
    for c in cookies:
        if c.get("name") == "__session":
            session_cookie = c.get("value")
            break
    if not session_cookie:
        # Try __client_uat or __clerk_db_jwt
        for c in cookies:
            if c.get("name") in ("__clerk_db_jwt",):
                session_cookie = c.get("value")
                break

    if not session_cookie:
        return None

    # Build cookie string for Clerk
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

    try:
        resp = httpx.get(
            f"{CLERK_BASE}/v1/client",
            params={
                "__clerk_api_version": "2025-11-10",
                "_clerk_js_version": "5.117.0",
            },
            headers={
                "cookie": cookie_str,
                "origin": SUNO_ORIGIN,
                "referer": f"{SUNO_ORIGIN}/",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Extract JWT from Clerk response
            sessions = data.get("response", {}).get("sessions", [])
            if sessions:
                last_token = sessions[0].get("last_active_token", {})
                jwt = last_token.get("jwt")
                if jwt:
                    return jwt
            # Also try last_active_session_id path
            last_session = data.get("response", {}).get("last_active_session_id")
            if last_session and sessions:
                for s in sessions:
                    if s.get("id") == last_session:
                        jwt = s.get("last_active_token", {}).get("jwt")
                        if jwt:
                            return jwt
    except Exception:
        pass
    return None


def get_auth_headers() -> dict:
    """Get all required headers for authenticated API calls."""
    jwt = get_jwt()
    if not jwt:
        raise RuntimeError(
            "Not authenticated. Run: cli-web-suno auth login --from-browser"
        )

    # Generate browser token with current timestamp
    ts = int(time.time() * 1000)
    raw = json.dumps({"timestamp": ts})
    b64 = base64.b64encode(raw.encode()).decode()
    browser_token = json.dumps({"token": b64})

    return {
        "Authorization": f"Bearer {jwt}",
        "browser-token": browser_token,
        "device-id": _get_device_id(),
        "origin": SUNO_ORIGIN,
        "referer": f"{SUNO_ORIGIN}/",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36"
        ),
    }


def validate_auth() -> dict:
    """Validate authentication by calling /api/session/. Returns session data or raises."""
    headers = get_auth_headers()
    resp = httpx.get(
        f"{STUDIO_API}/api/session/",
        headers=headers,
        timeout=15,
    )
    if resp.status_code == 401:
        raise RuntimeError(
            "Authentication expired. Run: cli-web-suno auth login --from-browser"
        )
    resp.raise_for_status()
    return resp.json()


async def login_with_playwright(app_url: str = SUNO_ORIGIN):
    """Login using Playwright — opens browser for manual login."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright not installed. Install with: pip install 'cli-web-suno[browser]'"
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(app_url)
        input("\nLog in to Suno in the browser window, then press ENTER here...")

        # Extract cookies
        cookies = await context.cookies()
        storage = await context.storage_state()
        await browser.close()

    # Save cookies
    auth_data = {
        "cookies": cookies,
        "storage_state": storage,
        "login_method": "playwright",
        "login_time": time.time(),
    }

    # Get JWT from cookies
    jwt = refresh_jwt_from_cookies(cookies)
    if jwt:
        auth_data["jwt"] = jwt
        auth_data["jwt_refreshed_at"] = time.time()

    save_auth(auth_data)
    return auth_data


def login_from_browser(port: int = 9222):
    """Extract cookies from Chrome debug profile via CDP."""
    import websockets.sync.client

    # Find a Suno page target (page targets have cookies, browser target may not)
    pages_resp = httpx.get(f"http://localhost:{port}/json", timeout=5)
    pages = pages_resp.json()
    ws_url = None
    for p in pages:
        if "suno.com" in p.get("url", ""):
            ws_url = p["webSocketDebuggerUrl"]
            break

    if not ws_url:
        # Fallback to browser-level endpoint
        ver_resp = httpx.get(f"http://localhost:{port}/json/version", timeout=5)
        ws_url = ver_resp.json()["webSocketDebuggerUrl"]

    with websockets.sync.client.connect(ws_url) as ws:
        # Enable Network domain (required for getAllCookies on page targets)
        ws.send(json.dumps({"id": 1, "method": "Network.enable", "params": {}}))
        ws.recv()
        ws.send(json.dumps({"id": 2, "method": "Network.getAllCookies", "params": {}}))
        result = json.loads(ws.recv())
        all_cookies = result.get("result", {}).get("cookies", [])

    # Filter for Suno-related cookies
    cookies = []
    seen = {}
    for c in all_cookies:
        domain = c.get("domain", "")
        if any(d in domain for d in ["suno.com", "clerk"]):
            name = c["name"]
            # Deduplicate: prefer broader domain (e.g., .suno.com over suno.com)
            if name in seen:
                existing_domain = seen[name].get("domain", "")
                if domain.startswith(".") and not existing_domain.startswith("."):
                    seen[name] = c
                continue
            seen[name] = c
    cookies = list(seen.values())

    if not cookies:
        raise RuntimeError(
            f"No Suno cookies found on port {port}. "
            "Make sure you're logged into suno.com in the debug Chrome."
        )

    auth_data = {
        "cookies": cookies,
        "login_method": "from-browser",
        "login_time": time.time(),
    }

    jwt = refresh_jwt_from_cookies(cookies)
    if jwt:
        auth_data["jwt"] = jwt
        auth_data["jwt_refreshed_at"] = time.time()

    save_auth(auth_data)
    return auth_data


def login_from_cookies_json(file_path: str):
    """Import cookies from a JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Cookie file not found: {file_path}")

    cookies = json.loads(path.read_text())
    if not isinstance(cookies, list):
        raise ValueError("Cookie file must contain a JSON array of cookie objects")

    auth_data = {
        "cookies": cookies,
        "login_method": "cookies-json",
        "login_time": time.time(),
    }

    jwt = refresh_jwt_from_cookies(cookies)
    if jwt:
        auth_data["jwt"] = jwt
        auth_data["jwt_refreshed_at"] = time.time()

    save_auth(auth_data)
    return auth_data
