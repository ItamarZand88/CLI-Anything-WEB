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


def login_browser() -> dict[str, Any]:
    """Open browser for OpenAI SSO login and extract auth tokens."""
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise AuthError(
            "playwright not installed. Run: pip install playwright && playwright install chromium"
        )

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

        # Extract access token from browser
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

        context.close()

        if not access_token:
            raise AuthError(
                "Could not extract access token. Make sure you're fully logged in."
            )

        auth_data = {
            "access_token": access_token,
            "device_id": device_id or "",
            "cf_clearance": cf_clearance or "",
            "cookies": all_cookies,
        }
        save_auth(auth_data)
        return auth_data
