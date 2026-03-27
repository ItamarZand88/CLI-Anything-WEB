"""Auth management for cli-web-hackernews — cookie-based HN authentication."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

import httpx

from .exceptions import AuthError

HN_BASE = "https://news.ycombinator.com"
CONFIG_DIR = Path.home() / ".config" / "cli-web-hackernews"
AUTH_FILE = CONFIG_DIR / "auth.json"
ENV_VAR = "CLI_WEB_HACKERNEWS_AUTH_JSON"


def _get_config_dir() -> Path:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def save_auth(user_cookie: str, username: str) -> Path:
    """Save auth cookie to auth.json with restrictive permissions."""
    _get_config_dir()
    data = {"user_cookie": user_cookie, "username": username}
    AUTH_FILE.write_text(json.dumps(data, indent=2))
    try:
        os.chmod(AUTH_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 600
    except OSError:
        pass  # Windows may not support chmod
    return AUTH_FILE


def load_auth() -> dict[str, str]:
    """Load auth from env var or file. Returns dict with user_cookie and username."""
    # 1. Try env var first (CI/CD)
    env_val = os.environ.get(ENV_VAR)
    if env_val:
        try:
            data = json.loads(env_val)
            if isinstance(data, dict) and "user_cookie" in data:
                return data
        except json.JSONDecodeError:
            pass

    # 2. Try auth file
    if AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text())
            if isinstance(data, dict) and "user_cookie" in data:
                return data
        except (json.JSONDecodeError, OSError):
            pass

    raise AuthError("Not logged in. Run: cli-web-hackernews auth login")


def get_user_cookie() -> str:
    """Get the HN user cookie value."""
    return load_auth()["user_cookie"]


def get_username() -> str:
    """Get the logged-in username."""
    return load_auth()["username"]


def is_logged_in() -> bool:
    """Check if auth credentials exist."""
    try:
        load_auth()
        return True
    except AuthError:
        return False


def logout() -> None:
    """Remove auth credentials."""
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def login_with_password(username: str, password: str) -> dict[str, str]:
    """Login to HN with username/password and return auth data.

    HN login is a POST to /login with acct=username&pw=password.
    On success, it sets a 'user' cookie and redirects.
    """
    with httpx.Client(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        follow_redirects=False,
        timeout=30.0,
    ) as client:
        response = client.post(
            f"{HN_BASE}/login",
            data={"acct": username, "pw": password, "goto": "news"},
        )

        # HN returns 302 on success, 200 with error on failure
        user_cookie = None
        for cookie_header in response.headers.get_list("set-cookie"):
            if cookie_header.startswith("user="):
                user_cookie = cookie_header.split("user=")[1].split(";")[0]
                break

        if not user_cookie:
            # Check if response body has error message
            if response.status_code == 200:
                raise AuthError("Login failed: bad username or password", recoverable=False)
            raise AuthError(f"Login failed: HTTP {response.status_code}", recoverable=False)

        auth_data = {"user_cookie": user_cookie, "username": username}
        save_auth(user_cookie, username)
        return auth_data


def login_browser() -> dict[str, str]:
    """Login to HN via browser (for users who prefer not to enter password in CLI).

    Uses Python sync_playwright with persistent context.
    """
    import asyncio
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise AuthError(
            "Browser login requires playwright. Install: pip install playwright && playwright install chromium",
            recoverable=False,
        )

    user_data_dir = str(_get_config_dir() / "browser-profile")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(f"{HN_BASE}/login")

        print("Please log in to Hacker News in the browser window.")
        print("The window will close automatically after login.")

        # Wait for the user cookie to appear (max 5 minutes)
        try:
            page.wait_for_url(
                lambda url: "login" not in url,
                timeout=300_000,
            )
        except Exception:
            context.close()
            raise AuthError("Login timed out after 5 minutes", recoverable=False)

        # Extract cookies
        cookies = context.cookies("https://news.ycombinator.com")
        user_cookie = None
        username = None
        for cookie in cookies:
            if cookie["name"] == "user":
                user_cookie = cookie["value"]
                # Username is the part before &
                username = user_cookie.split("&")[0] if "&" in user_cookie else None
                break

        context.close()

        if not user_cookie or not username:
            raise AuthError("Could not extract login cookie from browser", recoverable=False)

        auth_data = {"user_cookie": user_cookie, "username": username}
        save_auth(user_cookie, username)
        return auth_data


def validate_auth() -> dict[str, Any]:
    """Validate that the stored auth is still valid by checking the HN profile page."""
    auth = load_auth()
    cookie = auth["user_cookie"]
    username = auth["username"]

    with httpx.Client(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        },
        cookies={"user": cookie},
        follow_redirects=True,
        timeout=15.0,
    ) as client:
        response = client.get(f"{HN_BASE}/user?id={username}")

    if response.status_code != 200:
        raise AuthError("Auth validation failed — cookie may be expired", recoverable=False)

    # Check if we're actually logged in (page shows logout link)
    if f'id="logout"' not in response.text and "logout" not in response.text:
        raise AuthError("Auth cookie expired. Run: cli-web-hackernews auth login", recoverable=False)

    return {"username": username, "valid": True}
