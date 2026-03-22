"""WAF cookie management for Booking.com.

Booking.com uses AWS WAF which requires JavaScript challenge completion.
The CLI stores WAF cookies obtained via Python playwright browser session.
"""

from __future__ import annotations

import asyncio
import json
import os
import stat
import sys
from pathlib import Path

from .exceptions import AuthError

CONFIG_DIR = Path.home() / ".config" / "cli-web-booking"
AUTH_FILE = CONFIG_DIR / "auth.json"
ENV_VAR = "CLI_WEB_BOOKING_AUTH_JSON"


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_cookies() -> dict[str, str]:
    """Load WAF cookies from env var or auth file.

    Returns:
        Dict of cookie name -> value.

    Raises:
        AuthError: If no cookies are available.
    """
    # Check env var first (for CI/CD)
    env_auth = os.environ.get(ENV_VAR)
    if env_auth:
        try:
            data = json.loads(env_auth)
            if isinstance(data, dict) and "cookies" in data:
                cookies = data["cookies"]
            elif isinstance(data, dict):
                cookies = data
            else:
                raise AuthError("Invalid auth JSON format in env var", recoverable=False)
        except json.JSONDecodeError:
            raise AuthError("Invalid JSON in CLI_WEB_BOOKING_AUTH_JSON", recoverable=False)
    elif AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
            cookies = data.get("cookies", {})
        except (json.JSONDecodeError, OSError) as e:
            raise AuthError(f"Failed to read auth file: {e}", recoverable=False)
    else:
        raise AuthError(
            "No WAF cookies found. Run: cli-web-booking auth login",
            recoverable=False,
        )

    # Handle playwright state-save list format
    if isinstance(cookies, list):
        cookies = _extract_cookies(cookies)

    if not cookies:
        raise AuthError(
            "Auth file has no cookies. Run: cli-web-booking auth login",
            recoverable=False,
        )
    return cookies


def _extract_cookies(cookie_list: list[dict]) -> dict[str, str]:
    """Extract cookies from playwright state-save list format.

    Handles domain priority — booking.com cookies take precedence.
    """
    result: dict[str, str] = {}
    priority: dict[str, bool] = {}  # True if from .booking.com

    for c in cookie_list:
        name = c.get("name", "")
        value = c.get("value", "")
        domain = c.get("domain", "")

        if not name or not value:
            continue

        is_primary = domain in (".booking.com", "www.booking.com", "booking.com")

        if name not in result or (is_primary and not priority.get(name)):
            result[name] = value
            priority[name] = is_primary

    return result


def save_cookies(cookies: dict[str, str]) -> None:
    """Save cookies to auth file with restricted permissions."""
    _ensure_config_dir()
    data = {"cookies": cookies}
    AUTH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        AUTH_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass  # Windows doesn't support chmod 600 the same way


def clear_cookies() -> None:
    """Remove stored auth cookies."""
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def is_authenticated() -> bool:
    """Check if valid WAF cookies exist."""
    try:
        cookies = load_cookies()
        return bool(cookies.get("aws-waf-token") or cookies.get("bkng"))
    except AuthError:
        return False


def _windows_playwright_event_loop():
    """Context manager: restore default event loop policy for Playwright on Windows."""
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        if sys.platform != "win32":
            yield
            return
        original = asyncio.get_event_loop_policy()
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        try:
            yield
        finally:
            asyncio.set_event_loop_policy(original)

    return _ctx()


def login_browser() -> dict[str, str]:
    """Open browser via Python playwright for WAF challenge resolution.

    Uses sync_playwright() with a persistent context to solve the AWS WAF
    JavaScript challenge automatically, then saves cookies.

    Returns extracted cookies on success.

    Raises:
        AuthError: If playwright is not available or login fails.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise AuthError(
            "Playwright not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium",
            recoverable=False,
        )

    _ensure_config_dir()
    state_file = CONFIG_DIR / "state.json"
    browser_profile = CONFIG_DIR / "browser-profile"
    browser_profile.mkdir(parents=True, exist_ok=True)

    print("Opening browser for Booking.com WAF challenge...")

    with _windows_playwright_event_loop(), sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(browser_profile),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--password-store=basic",
            ],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.booking.com")

        print("\nThe WAF challenge will be solved automatically.")
        print("Wait for the Booking.com homepage to load fully.")
        try:
            input("\nPress ENTER when the page has loaded... ")
        except (EOFError, KeyboardInterrupt):
            context.close()
            raise AuthError("Login cancelled", recoverable=False)

        # Save storage state
        context.storage_state(path=str(state_file))
        context.close()

    # Parse saved state
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise AuthError(f"Failed to parse state file: {e}", recoverable=False)

    raw_cookies = state.get("cookies", [])
    if isinstance(raw_cookies, list):
        cookies = _extract_cookies(raw_cookies)
    elif isinstance(raw_cookies, dict):
        cookies = raw_cookies
    else:
        cookies = {}

    if not cookies:
        raise AuthError("No cookies captured from browser session", recoverable=False)

    save_cookies(cookies)

    # Clean up state file (keep browser profile for reuse)
    try:
        state_file.unlink()
    except OSError:
        pass

    return cookies
