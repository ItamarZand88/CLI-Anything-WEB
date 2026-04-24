"""Auth management for cli-web-${app_name}.

Uses Python playwright for browser-based login.
Stores session cookies at ~/.config/cli-web-${app_name}/auth.json.
Includes headless auto-refresh for expired tokens.
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import stat
import sys
from pathlib import Path

from .exceptions import AuthError

CONFIG_DIR = Path.home() / ".config" / "cli-web-${app_name}"
AUTH_FILE = CONFIG_DIR / "auth.json"
ENV_VAR = "CLI_WEB_${APP_NAME}_AUTH_JSON"


def _ensure_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_auth(data: dict) -> Path:
    """Save auth data to auth.json with restrictive permissions (600)."""
    _ensure_dir()
    AUTH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if platform.system() != "Windows":
        AUTH_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    else:
        try:
            os.chmod(AUTH_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
    return AUTH_FILE


def load_auth() -> dict:
    """Load auth from env var or file.

    Returns:
        Auth data dict with 'cookies' key.

    Raises:
        AuthError: If no auth data is found.
    """
    # 1. Try env var first (CI/CD)
    env_val = os.environ.get(ENV_VAR)
    if env_val:
        try:
            data = json.loads(env_val)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 2. Try auth file
    if AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "cookies" in data:
                return data
            # Handle raw playwright cookie list format
            if isinstance(data, list):
                cookie_dict = {}
                for c in data:
                    if isinstance(c, dict):
                        cookie_dict[c["name"]] = c["value"]
                return {"cookies": cookie_dict}
            # Plain dict without 'cookies' wrapper
            if isinstance(data, dict):
                return {"cookies": data}
        except (json.JSONDecodeError, OSError):
            pass

    raise AuthError("Not logged in. Run: cli-web-${app_name} auth login")


def get_cookies() -> dict:
    """Get cookies dict for session injection."""
    try:
        auth = load_auth()
        return auth.get("cookies", {})
    except AuthError:
        return {}


def clear_auth() -> None:
    """Remove auth file."""
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def is_logged_in() -> bool:
    """Check if auth credentials exist."""
    try:
        load_auth()
        return True
    except AuthError:
        return False


# ---------------------------------------------------------------------------
# Token auto-refresh (headless browser)
# ---------------------------------------------------------------------------

def refresh_auth() -> dict | None:
    """Silently refresh cookies using the persistent browser profile.

    Launches a headless browser with the saved profile, navigates to the
    site (which auto-refreshes session cookies), extracts and saves the
    updated cookies. No user interaction needed.

    Returns:
        Auth data dict or None if refresh failed.
    """
    profile_dir = CONFIG_DIR / "browser-profile"
    if not profile_dir.exists():
        return None

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
            )
            page = context.pages[0] if context.pages else context.new_page()
            # FILL_IN: Navigate to the site's homepage or auth-check URL
            page.goto("https://FILL_IN_SITE_URL/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            cookies = context.cookies()
            cookie_dict = {}
            for c in cookies:
                # FILL_IN: Filter cookies by domain
                if "FILL_IN_DOMAIN" in c.get("domain", ""):
                    cookie_dict[c["name"]] = c["value"]

            context.close()

        if cookie_dict:
            auth_data = {"cookies": cookie_dict}
            save_auth(auth_data)
            return auth_data
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Browser login
# ---------------------------------------------------------------------------

def login_browser() -> dict:
    """Open browser for manual login, capture cookies.

    Uses launch_persistent_context with headless=False so the user can
    manually log in. After login, extracts cookies and saves them.

    Returns:
        Auth data dict with 'cookies' key.

    Raises:
        AuthError: If login failed (required cookies not found).
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(CONFIG_DIR / "browser-profile"),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        page = context.pages[0] if context.pages else context.new_page()
        # FILL_IN: Navigate to the site's login page
        page.goto("https://FILL_IN_SITE_URL/login")

        print("\n  Please log in in the browser window.")
        print("  Press Enter here when you're logged in.\n")
        input("  Waiting... ")

        # Navigate to a page that confirms login
        # FILL_IN: Navigate to homepage/dashboard after login
        page.goto("https://FILL_IN_SITE_URL/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        cookies = context.cookies()
        cookie_dict = {}
        for c in cookies:
            # FILL_IN: Filter cookies by domain
            if "FILL_IN_DOMAIN" in c.get("domain", ""):
                cookie_dict[c["name"]] = c["value"]

        context.close()

    # FILL_IN: Check for required session cookie
    if not cookie_dict:
        raise AuthError("Login failed — no session cookies found. Please try again.")

    auth_data = {"cookies": cookie_dict}
    save_auth(auth_data)
    return auth_data
