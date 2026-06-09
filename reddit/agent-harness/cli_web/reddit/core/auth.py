"""Auth management for cli-web-reddit.

Uses Python playwright for browser-based Reddit login.
Stores bearer token (token_v2) and cookies at ~/.config/cli-web-reddit/auth.json.
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

AUTH_DIR = Path.home() / ".config" / "cli-web-reddit"
AUTH_FILE = AUTH_DIR / "auth.json"

# Environment variable override for CI/CD
ENV_VAR = "CLI_WEB_REDDIT_AUTH_JSON"

# Apex domain — its cookies win over subdomain duplicates on name collision.
APEX_DOMAIN = ".reddit.com"


def _ensure_dir() -> None:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)


def _collect_cookies(raw_cookies: list) -> tuple[dict, str]:
    """Collect reddit.com cookies into a ``{name: value}`` dict + token_v2.

    On a name collision across subdomains (e.g. ``www.reddit.com`` vs
    ``.reddit.com`` vs ``accounts.reddit.com``) the apex ``.reddit.com`` value
    wins, so the result no longer depends on arbitrary iteration order.
    """
    cookie_dict: dict[str, str] = {}
    domains: dict[str, str] = {}
    token = ""
    for c in raw_cookies:
        if not isinstance(c, dict):
            continue
        name = c.get("name")
        domain = c.get("domain", "")
        if not name or "reddit.com" not in domain:
            continue
        if name not in cookie_dict or domain == APEX_DOMAIN:
            cookie_dict[name] = c.get("value", "")
            domains[name] = domain
        if name == "token_v2" and (domain == APEX_DOMAIN or not token):
            token = c.get("value", "")
    return cookie_dict, token


def load_auth() -> dict | None:
    """Load auth data from env var or file. Returns dict with 'token' and 'cookies' keys."""
    # Env var override
    env = os.environ.get(ENV_VAR)
    if env:
        try:
            return json.loads(env)
        except json.JSONDecodeError:
            return None

    if not AUTH_FILE.exists():
        return None

    try:
        data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        # Handle both formats
        if isinstance(data, dict) and "token" in data:
            return data
        if isinstance(data, list):
            # Raw cookie list — extract token_v2
            cookie_dict, token = _collect_cookies(data)
            return {"token": token, "cookies": cookie_dict}
        if isinstance(data, dict):
            # Plain dict without "token" key — try to find token_v2 in values
            token = data.get("token_v2", "")
            return {"token": token, "cookies": data}
        return None
    except (json.JSONDecodeError, KeyError):
        return None


def save_auth(token: str, cookies: dict) -> None:
    """Save auth data to file with restricted permissions."""
    _ensure_dir()
    data = {"token": token, "cookies": cookies}
    # Create with 0600 *before* writing so the token is never briefly
    # world-readable at the default umask (TOCTOU window).
    fd = os.open(AUTH_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2))
    # chmod 600 on Unix to cover pre-existing files
    if platform.system() != "Windows":
        AUTH_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)


def clear_auth() -> None:
    """Remove auth file."""
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def get_bearer_token() -> str | None:
    """Get the bearer token for OAuth API calls."""
    auth = load_auth()
    if not auth:
        return None
    return auth.get("token") or None


def get_cookies() -> dict:
    """Get cookies dict for session warmup."""
    auth = load_auth()
    if not auth:
        return {}
    return auth.get("cookies", {})


def refresh_token() -> str | None:
    """Silently refresh token_v2 using the persistent browser profile.

    Launches a headless browser with the saved profile, navigates to Reddit
    (which auto-refreshes the token_v2 cookie), extracts and saves the new token.
    Returns the new token or None if refresh failed.
    """
    profile_dir = AUTH_DIR / "browser-profile"
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
            page.goto("https://www.reddit.com/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            cookie_dict, token = _collect_cookies(context.cookies())

            context.close()

        if token:
            save_auth(token, cookie_dict)
            return token
        return None
    except Exception:
        return None


def login_browser() -> dict:
    """Open browser for Reddit login, extract cookies and token.

    Returns dict with 'token' and 'cookies' keys.
    """
    # Windows event loop fix
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(AUTH_DIR / "browser-profile"),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.reddit.com/login")

        print("\n  Please log into Reddit in the browser window.")
        print("  Press Enter here when you're logged in and see the Reddit homepage.\n")
        input("  Waiting... ")

        # Navigate to homepage to ensure all cookies are set
        page.goto("https://www.reddit.com/")
        page.wait_for_timeout(2000)

        # Extract cookies
        cookie_dict, token = _collect_cookies(context.cookies())

        context.close()

    if not token:
        raise AuthError("Login failed — no token_v2 cookie found. Please try again.")

    save_auth(token, cookie_dict)
    return {"token": token, "cookies": cookie_dict}
