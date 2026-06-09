{% if auth_type == "google_sso" -%}
"""Auth management for cli-web-${app_name} (Google SSO).

Handles:
- Login via Python playwright (opens browser, saves state)
- Cookie import from JSON file (manual fallback)
- Secure storage at ~/.config/cli-web-${app_name}/auth.json with chmod 600
- Regional cookie priority (.google.com > .google.co.il / .google.de / etc.) —
  CRITICAL for international users (see CLAUDE.md "Auth cookie priority")

Customize:
- BASE_URL — the app's landing URL
- AUTH_COOKIE_NAMES — which Google cookies matter for this app
- fetch_tokens() — per-app CSRF / session-id regex extraction
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from .exceptions import AuthError

# ---------------------------------------------------------------------------
# Customize these for your app
# ---------------------------------------------------------------------------

BASE_URL = "https://FILL_IN_BASE_URL"
GOOGLE_ACCOUNTS_URL = "https://accounts.google.com/"

AUTH_DIR = Path.home() / ".config" / "cli-web-${app_name}"
AUTH_FILE = AUTH_DIR / "auth.json"
ENV_VAR = "CLI_WEB_${APP_NAME}_AUTH_JSON"
BROWSER_PROFILE_DIR = AUTH_DIR / "browser-profile"

# Google SID-family cookies — extend if the target app needs additional ones.
AUTH_COOKIE_NAMES = {
    "SID", "HSID", "SSID", "APISID", "SAPISID",
    "__Secure-1PSID", "__Secure-3PSID",
    "__Secure-1PSIDTS", "__Secure-3PSIDTS",
    "__Secure-1PAPISID", "__Secure-3PAPISID",
    "NID", "LSID", "OSID",
}

# Regional Google ccTLDs for international users. Cookies from any of these
# domains are recognized, but `.google.com` values take priority.
GOOGLE_REGIONAL_CCTLDS = frozenset({
    "google.co.uk", "google.co.jp", "google.co.kr", "google.co.in",
    "google.co.il", "google.co.za", "google.co.nz", "google.co.id",
    "google.co.th", "google.co.ke", "google.co.tz",
    "google.com.au", "google.com.br", "google.com.sg", "google.com.hk",
    "google.com.mx", "google.com.ar", "google.com.tr", "google.com.tw",
    "google.com.eg", "google.com.pk", "google.com.ng", "google.com.ph",
    "google.com.co", "google.com.vn", "google.com.ua", "google.com.pe",
    "google.com.sa", "google.com.my", "google.com.bd",
    "google.de", "google.fr", "google.it", "google.es", "google.nl",
    "google.pl", "google.se", "google.no", "google.fi", "google.dk",
    "google.at", "google.ch", "google.be", "google.pt", "google.ie",
    "google.cz", "google.ro", "google.hu", "google.gr", "google.bg",
    "google.sk", "google.hr", "google.lt", "google.lv", "google.ee",
    "google.si",
    "google.ru", "google.ca", "google.cl", "google.ae",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_dir_setup() -> None:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def _windows_playwright_event_loop():
    """On Windows, Playwright's sync API needs the default event loop policy.

    Non-op on POSIX. Always use this around ``sync_playwright()`` calls.
    """
    if sys.platform != "win32":
        yield
        return
    original = asyncio.get_event_loop_policy()
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    try:
        yield
    finally:
        asyncio.set_event_loop_policy(original)


def _ensure_chromium_installed() -> None:
    """Check for Chromium and install it once if missing.

    Silently no-ops if the playwright CLI is unavailable — sync_playwright()
    may still work with a different browser binary.
    """
    try:
        result = subprocess.run(
            ["playwright", "install", "--dry-run", "chromium"],
            capture_output=True, text=True,
        )
        stdout_lower = result.stdout.lower()
        if "chromium" not in stdout_lower or "will download" not in stdout_lower:
            return
        print("Chromium browser not installed. Installing now...")
        install_result = subprocess.run(
            ["playwright", "install", "chromium"],
            capture_output=True, text=True,
        )
        if install_result.returncode != 0:
            raise AuthError("Failed to install Chromium. Run: playwright install chromium")
        print("Chromium installed successfully.")
    except (FileNotFoundError, AuthError):
        pass


def _extract_cookies(raw_cookies: list) -> dict:
    """Filter + prioritize Google auth cookies.

    Supports .google.com and all regional ccTLDs. Critically, values from
    `.google.com` win over regional duplicates (e.g. `.google.co.il`) — this
    is the fix mandated by CLAUDE.md line 93 for international users.
    """
    result: dict[str, str] = {}
    allowed = {
        ".google.com", "google.com",
        ".accounts.google.com", "accounts.google.com",
        ".googleusercontent.com",
    }
    for cctld in GOOGLE_REGIONAL_CCTLDS:
        allowed.add(f".{cctld}")
        allowed.add(cctld)

    for c in raw_cookies:
        domain = c.get("domain", "")
        name = c.get("name", "")
        if domain not in allowed or not name:
            continue
        # Only overwrite an existing entry if the new one is from .google.com
        # (the authoritative domain).
        if name not in result or domain == ".google.com":
            result[name] = c.get("value", "")
    return result


def _save_auth(data: dict) -> None:
    _auth_dir_setup()
    AUTH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(AUTH_FILE, 0o600)
    except OSError:
        pass  # Windows may not support chmod


# ---------------------------------------------------------------------------
# Login flows
# ---------------------------------------------------------------------------

def login_browser(headed: bool = True) -> None:
    """Open Chromium via Python playwright for Google login; save state.

    Uses ``sync_playwright()`` with a persistent context — NOT the npx
    playwright-cli wrapper (that has interactive-input / Popen race issues).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise AuthError(
            "Playwright not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )

    _auth_dir_setup()
    _ensure_chromium_installed()
    state_file = AUTH_DIR / "playwright-state.json"
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    print("Opening Chromium for Google login...")

    with _windows_playwright_event_loop(), sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=not headed,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--password-store=basic",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(BASE_URL)

        print("\nInstructions:")
        print("1. Complete the Google login in the browser window")
        print(f"2. Wait until you see the cli-web-${app_name} homepage")
        print("3. Press ENTER here to save and close\n")
        input("[Press ENTER when logged in] ")

        # Force .google.com cookies for regional users: navigate to
        # accounts.google.com and back to our base URL. This writes the
        # authoritative cookie set even if the user's region redirected
        # them through a regional domain.
        try:
            page.goto(GOOGLE_ACCOUNTS_URL, wait_until="load")
        except Exception:
            pass
        try:
            page.goto(BASE_URL, wait_until="load")
        except Exception:
            pass

        context.storage_state(path=str(state_file))
        context.close()

    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        cookies = _extract_cookies(state.get("cookies", []))
        if not cookies:
            raise AuthError("No Google cookies found in browser state. Did you log in?")
        _save_auth({"cookies": cookies})
        print(f"Auth saved to {AUTH_FILE}")
    except (json.JSONDecodeError, KeyError) as e:
        raise AuthError(f"Failed to parse playwright state: {e}")


def login_from_cookies_json(filepath: str) -> None:
    """Import cookies from a JSON file (manual fallback).

    Accepts either playwright ``state-save`` format or a plain cookies array.
    """
    _auth_dir_setup()
    try:
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        raise AuthError(f"Cannot read cookies file: {e}")

    if isinstance(data, dict) and "cookies" in data:
        raw_cookies = data["cookies"]
    elif isinstance(data, list):
        raw_cookies = data
    else:
        raise AuthError("Unrecognized cookies format — expected array or {cookies: [...]}")

    cookies = _extract_cookies(raw_cookies)
    if not cookies:
        raise AuthError("No Google cookies found in file")
    _save_auth({"cookies": cookies})
    print(f"Auth saved to {AUTH_FILE} ({len(cookies)} cookies)")


def load_cookies() -> dict:
    """Load stored cookies: env var first, then the auth file.

    Handles both flat ``{name: value}`` dicts and raw playwright
    ``[{name, value, domain}, ...]`` arrays.
    """
    env_auth = os.environ.get(ENV_VAR)
    if env_auth:
        try:
            data = json.loads(env_auth)
            cookies = data.get("cookies", data) if isinstance(data, dict) else data
            if isinstance(cookies, list):
                cookies = _extract_cookies(cookies)
            if cookies:
                return cookies
        except (json.JSONDecodeError, TypeError):
            pass  # fall through to file

    if not AUTH_FILE.exists():
        raise AuthError("Not authenticated. Run: cli-web-${app_name} auth login")
    try:
        data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        cookies = data.get("cookies", {})
        if not cookies:
            raise AuthError("No cookies found. Run: cli-web-${app_name} auth login")
        if isinstance(cookies, list):
            cookies = _extract_cookies(cookies)
            if not cookies:
                raise AuthError("No Google cookies found. Run: cli-web-${app_name} auth login")
        return cookies
    except (json.JSONDecodeError, KeyError) as e:
        raise AuthError(f"Corrupted auth file: {e}. Run: cli-web-${app_name} auth login")


def clear_auth() -> None:
    """Remove auth file."""
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def is_logged_in() -> bool:
    try:
        load_cookies()
        return True
    except AuthError:
        return False


# ---------------------------------------------------------------------------
# Per-app token extraction — CUSTOMIZE for your app's homepage
# ---------------------------------------------------------------------------

def fetch_tokens(cookies: dict) -> dict:
    """Fetch the homepage and extract short-lived auth tokens.

    Google batchexecute apps typically need: ``SNlM0e`` (CSRF / ``at``),
    ``FdrFJe`` (session_id), ``cfb2h`` (build_label). Regexes are per-site;
    see ``notebooklm/core/auth.py:289-333`` and ``stitch/core/auth.py`` for
    worked examples.

    TODO: replace FILL_IN regex patterns and return keys below.
    """
    import re

    import httpx

    resp = httpx.get(
        BASE_URL + "/",
        cookies=cookies,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        },
        follow_redirects=True,
        timeout=15.0,
    )
    if "accounts.google.com" in str(resp.url):
        raise AuthError("Session expired — run: cli-web-${app_name} auth login")

    html = resp.text
    m = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
    csrf = m.group(1) if m else None
    if not csrf:
        raise AuthError(
            "Could not extract CSRF token. Session may have expired — "
            "run: cli-web-${app_name} auth login"
        )
    return {"csrf": csrf}
{% else -%}
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
{% endif -%}
