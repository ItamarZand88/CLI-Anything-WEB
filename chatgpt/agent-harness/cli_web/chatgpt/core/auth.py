"""Auth management for cli-web-chatgpt — browser-based OpenAI SSO login."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from .exceptions import AuthError

BASE_URL = "https://chatgpt.com"
CONFIG_DIR = Path.home() / ".config" / "cli-web-chatgpt"
AUTH_FILE = CONFIG_DIR / "auth.json"
ENV_VAR = "CLI_WEB_CHATGPT_AUTH_JSON"


def _get_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def save_auth(data: dict[str, Any]) -> Path:
    """Save auth data (access_token, cookies, device_id) to auth.json."""
    _get_config_dir()
    AUTH_FILE.write_text(json.dumps(data, indent=2))
    try:
        os.chmod(AUTH_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return AUTH_FILE


def load_auth() -> dict[str, Any]:
    """Load auth from env var or file."""
    env_val = os.environ.get(ENV_VAR)
    if env_val:
        try:
            data = json.loads(env_val)
            if isinstance(data, dict) and "access_token" in data:
                return data
        except json.JSONDecodeError:
            pass

    if AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text())
            if isinstance(data, dict) and "access_token" in data:
                return data
        except (json.JSONDecodeError, OSError):
            pass

    raise AuthError("Not logged in. Run: cli-web-chatgpt auth login")


def is_logged_in() -> bool:
    try:
        load_auth()
        return True
    except AuthError:
        return False


def clear_auth() -> None:
    """Remove stored credentials."""
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def _extract_auth_data(page, context) -> dict[str, Any] | None:
    """Extract access token + cookies from a live ChatGPT browser session.

    Returns the auth data dict, or None if no access token could be obtained.
    """
    access_token = page.evaluate("""() => {
        try {
            // Try getting from session storage
            const session = JSON.parse(sessionStorage.getItem('__session') || '{}');
            if (session.accessToken) return session.accessToken;
        } catch {}
        try {
            // Try from cookie
            const cookies = document.cookie.split(';');
            for (const c of cookies) {
                const [name, val] = c.trim().split('=');
                if (name === '__Secure-next-auth.session-token') return val;
            }
        } catch {}
        return null;
    }""")

    # Get cookies
    cookies = context.cookies()

    # Extract key values
    device_id = None
    cf_clearance = None
    all_cookies = {}
    for cookie in cookies:
        all_cookies[cookie["name"]] = cookie["value"]
        if cookie["name"] == "oai-did":
            device_id = cookie["value"]
        elif cookie["name"] == "cf_clearance":
            cf_clearance = cookie["value"]

    # If no access_token from JS, try to get it via API call
    if not access_token:
        try:
            resp = page.evaluate("""async () => {
                const r = await fetch('/api/auth/session');
                const data = await r.json();
                return data.accessToken || null;
            }""")
            access_token = resp
        except Exception:
            pass

    if not access_token:
        return None

    return {
        "access_token": access_token,
        "device_id": device_id or "",
        "cf_clearance": cf_clearance or "",
        "cookies": all_cookies,
    }


def login_browser() -> dict[str, Any]:
    """Open browser for OpenAI SSO login and extract auth tokens."""
    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise AuthError(
            "playwright not installed. Run: pip install playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        user_data = CONFIG_DIR / "browser-data"
        user_data.mkdir(parents=True, exist_ok=True)

        context = p.chromium.launch_persistent_context(
            str(user_data),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")

        print("Please log in to ChatGPT in the browser window.")
        print("After logging in, press Enter here to continue...")
        input()

        # Navigate to trigger token refresh
        page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=30000)

        auth_data = _extract_auth_data(page, context)

        context.close()

        if not auth_data:
            raise AuthError("Could not extract access token. Make sure you're fully logged in.")

        save_auth(auth_data)
        return auth_data


def refresh_auth() -> dict[str, Any]:
    """Headlessly refresh the access token using the persistent browser profile.

    Reuses the browser session saved by login_browser() in headless mode to
    re-obtain the session token and cookies, then saves them via save_auth().

    Raises:
        AuthError: If the profile is missing or the underlying SSO session is
            dead — the user must run `cli-web-chatgpt auth login`.
    """
    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise AuthError(
            "playwright not installed. Run: pip install playwright && playwright install chromium"
        ) from exc

    user_data = CONFIG_DIR / "browser-data"
    if not user_data.exists():
        raise AuthError("Session expired. Run: cli-web-chatgpt auth login")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(user_data),
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            # Navigate to trigger token refresh
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=30000)
            auth_data = _extract_auth_data(page, context)
        finally:
            context.close()

    if not auth_data:
        raise AuthError("Session expired. Run: cli-web-chatgpt auth login")

    save_auth(auth_data)
    return auth_data
