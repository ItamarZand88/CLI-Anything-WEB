"""Auth management for cli-web-linkedin.

Uses Python playwright for browser-based LinkedIn login.
Stores session cookies (li_at, JSESSIONID, li_rm, liap) at ~/.config/cli-web-linkedin/auth.json.
CSRF token is derived from JSESSIONID: ajax:<JSESSIONID_value> (quotes stripped).
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

CONFIG_DIR = Path.home() / ".config" / "cli-web-linkedin"
AUTH_FILE = CONFIG_DIR / "auth.json"
ENV_VAR = "CLI_WEB_LINKEDIN_AUTH_JSON"

# Key cookies we need from LinkedIn
_REQUIRED_COOKIES = ("li_at",)
_IMPORTANT_COOKIES = ("li_at", "JSESSIONID", "li_rm", "liap")


def _ensure_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_auth(data: dict) -> Path:
    """Save auth data to auth.json with restrictive permissions (600).

    Args:
        data: Dict with 'cookies' and optionally 'csrf_token' keys.
    """
    _ensure_dir()
    AUTH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if platform.system() != "Windows":
        AUTH_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    else:
        try:
            os.chmod(AUTH_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass  # Windows may not support chmod
    return AUTH_FILE


def load_auth() -> dict:
    """Load auth from env var or file.

    Returns:
        Auth data dict with 'cookies' key containing cookie dict,
        and 'csrf_token' key with the derived CSRF token.

    Raises:
        AuthError: If no auth data is found.
    """
    # 1. Try env var first (CI/CD)
    env_val = os.environ.get(ENV_VAR)
    if env_val:
        try:
            data = json.loads(env_val)
            if isinstance(data, dict) and "cookies" in data:
                return data
        except json.JSONDecodeError:
            pass

    # 2. Try auth file
    if AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "cookies" in data:
                return data
            # Handle raw cookie list format from playwright
            if isinstance(data, list):
                cookie_dict = {}
                for c in data:
                    if isinstance(c, dict) and ".linkedin.com" in c.get("domain", ""):
                        cookie_dict[c["name"]] = c["value"]
                csrf = _derive_csrf(cookie_dict)
                return {"cookies": cookie_dict, "csrf_token": csrf}
            # Plain dict without 'cookies' wrapper — treat as raw cookie dict
            if isinstance(data, dict):
                csrf = _derive_csrf(data)
                return {"cookies": data, "csrf_token": csrf}
        except (json.JSONDecodeError, OSError):
            pass

    raise AuthError("Not logged in. Run: cli-web-linkedin auth login")


def get_cookies() -> dict:
    """Get cookies dict for session injection.

    Returns:
        Dict of cookie name -> value pairs, or empty dict if not logged in.
    """
    try:
        auth = load_auth()
        return auth.get("cookies", {})
    except AuthError:
        return {}


def get_csrf_token() -> str | None:
    """Get the CSRF token derived from JSESSIONID.

    Returns:
        CSRF token string like 'ajax:<jsessionid>' or None.
    """
    try:
        auth = load_auth()
        return auth.get("csrf_token") or None
    except AuthError:
        return None


def _derive_csrf(cookies: dict) -> str:
    """Derive CSRF token from JSESSIONID cookie.

    LinkedIn CSRF token format: ajax:<JSESSIONID_value>
    The JSESSIONID cookie value is surrounded by quotes which must be stripped.

    Args:
        cookies: Dict of cookie name -> value pairs.

    Returns:
        CSRF token string, or empty string if JSESSIONID not found.
    """
    jsessionid = cookies.get("JSESSIONID", "")
    if jsessionid:
        # Strip surrounding quotes from JSESSIONID value
        jsessionid = jsessionid.strip('"')
        return f"ajax:{jsessionid}"
    return ""


def clear_auth() -> None:
    """Remove auth file."""
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def is_logged_in() -> bool:
    """Check if auth credentials exist and contain required cookies."""
    try:
        auth = load_auth()
        cookies = auth.get("cookies", {})
        return bool(cookies.get("li_at"))
    except AuthError:
        return False


def refresh_auth() -> dict | None:
    """Silently refresh cookies using the persistent browser profile.

    Launches a headless browser with the saved profile, navigates to LinkedIn
    (which auto-refreshes cookies), extracts and saves the updated cookies.

    Returns:
        Auth data dict or None if refresh failed.
    """
    profile_dir = CONFIG_DIR / "browser-profile"
    if not profile_dir.exists():
        return None

    # Windows event loop fix
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
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            cookies = context.cookies()
            cookie_dict = {}

            for c in cookies:
                if ".linkedin.com" in c.get("domain", ""):
                    cookie_dict[c["name"]] = c["value"]

            context.close()

        if cookie_dict.get("li_at"):
            csrf = _derive_csrf(cookie_dict)
            auth_data = {"cookies": cookie_dict, "csrf_token": csrf}
            save_auth(auth_data)
            return auth_data
        return None
    except Exception:
        return None


def login_browser() -> dict:
    """Open browser for LinkedIn login, extract cookies.

    Uses launch_persistent_context with headless=False so the user can
    manually log in. After login, navigates to the feed to verify success
    and extracts all .linkedin.com cookies.

    Returns:
        Dict with 'cookies' and 'csrf_token' keys.

    Raises:
        AuthError: If login failed (no li_at cookie found).
    """
    # Windows event loop fix
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
        page.goto("https://www.linkedin.com/login")

        print("\n  Please log into LinkedIn in the browser window.")
        print("  Press Enter here when you're logged in and see the LinkedIn feed.\n")
        input("  Waiting... ")

        # Navigate to feed to verify login and ensure all cookies are set
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Extract all cookies from .linkedin.com domain
        cookies = context.cookies()
        cookie_dict = {}

        for c in cookies:
            if ".linkedin.com" in c.get("domain", ""):
                cookie_dict[c["name"]] = c["value"]

        context.close()

    # Verify we got the essential session cookie
    if not cookie_dict.get("li_at"):
        raise AuthError(
            "Login failed — no li_at session cookie found. "
            "Please try again and make sure you complete the login."
        )

    # Log which important cookies we captured
    found = [name for name in _IMPORTANT_COOKIES if name in cookie_dict]
    missing = [name for name in _IMPORTANT_COOKIES if name not in cookie_dict]
    print(f"\n  Captured cookies: {', '.join(found)}")
    if missing:
        print(f"  Note: missing optional cookies: {', '.join(missing)}")

    # Derive CSRF token from JSESSIONID
    csrf = _derive_csrf(cookie_dict)
    if csrf:
        print(f"  CSRF token derived from JSESSIONID: {csrf[:20]}...")
    else:
        print("  Warning: No JSESSIONID found — CSRF token unavailable.")

    auth_data = {"cookies": cookie_dict, "csrf_token": csrf}
    save_auth(auth_data)

    print(f"  Auth saved to {AUTH_FILE}\n")
    return auth_data
