"""Auth management for cli-web-stitch.

Handles:
- Login via Python playwright (opens browser, saves state)
- Cookie import from JSON file (manual fallback)
- Token extraction (CSRF, session ID, build label) from homepage
- Secure storage at ~/.config/cli-web-stitch/auth.json
"""
import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import httpx

AUTH_DIR = Path.home() / ".config" / "cli-web-stitch"
AUTH_FILE = AUTH_DIR / "auth.json"
BASE_URL = "https://stitch.withgoogle.com"

# Google cookies relevant for Stitch auth
AUTH_COOKIE_NAMES = {
    "SID", "HSID", "SSID", "APISID", "SAPISID",
    "__Secure-1PSID", "__Secure-3PSID",
    "__Secure-1PSIDTS", "__Secure-3PSIDTS",
    "__Secure-1PAPISID", "__Secure-3PAPISID",
    "NID", "LSID", "OSID",
}


from .exceptions import AuthError


def _auth_dir_setup():
    AUTH_DIR.mkdir(parents=True, exist_ok=True)


GOOGLE_ACCOUNTS_URL = "https://accounts.google.com/"
BROWSER_PROFILE_DIR = AUTH_DIR / "browser-profile"


def _windows_playwright_event_loop():
    """Context manager: restore default event loop policy for Playwright on Windows.

    Playwright's sync API needs ProactorEventLoop on Windows for subprocess spawning.
    This temporarily restores the default policy, then switches back.
    """
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        if sys.platform != "win32":
            yield
            return
        original_policy = asyncio.get_event_loop_policy()
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        try:
            yield
        finally:
            asyncio.set_event_loop_policy(original_policy)

    return _ctx()


def _ensure_chromium_installed():
    """Pre-flight check: install Chromium if needed."""
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
        pass  # playwright CLI not found but sync_playwright may still work


def login_browser(headed: bool = True):
    """Open browser via Python playwright for Google login, save auth state.

    Uses sync_playwright() with a persistent context,
    not the external npx @playwright/cli which has interactive input issues.
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
        print("2. Wait until you see the Stitch homepage")
        print("3. Press ENTER here to save and close\n")

        input("[Press ENTER when logged in] ")

        # Force .google.com cookies for regional users (e.g. Israel → .google.co.il)
        # Navigate to accounts.google.com first, then back to Stitch.
        # accounts.google.com may auto-redirect back, so catch navigation errors.
        try:
            page.goto(GOOGLE_ACCOUNTS_URL, wait_until="load")
        except Exception:
            pass  # Redirect interrupted — cookies are still set
        try:
            page.goto(BASE_URL, wait_until="load")
        except Exception:
            pass  # Already on Stitch

        # Save storage state
        context.storage_state(path=str(state_file))
        context.close()

    # Parse and save cookies
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        cookies = _extract_cookies(state.get("cookies", []))
        if not cookies:
            raise AuthError("No Google cookies found in browser state. Did you log in?")
        _save_auth({"cookies": cookies})
        print(f"Auth saved to {AUTH_FILE}")
    except (json.JSONDecodeError, KeyError) as e:
        raise AuthError(f"Failed to parse playwright state: {e}")


def login_from_cookies_json(filepath: str):
    """Import cookies from a JSON file (manual fallback).

    Accepts either playwright state-save format or a plain cookies array.
    """
    _auth_dir_setup()
    try:
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        raise AuthError(f"Cannot read cookies file: {e}")

    # Handle playwright state-save format
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


# Regional Google ccTLDs for international users
GOOGLE_REGIONAL_CCTLDS = frozenset({
    # Major regions
    "google.co.uk", "google.co.jp", "google.co.kr", "google.co.in",
    "google.co.il", "google.co.za", "google.co.nz", "google.co.id",
    "google.co.th", "google.co.ke", "google.co.tz",
    # .com.XX variants
    "google.com.au", "google.com.br", "google.com.sg", "google.com.hk",
    "google.com.mx", "google.com.ar", "google.com.tr", "google.com.tw",
    "google.com.eg", "google.com.pk", "google.com.ng", "google.com.ph",
    "google.com.co", "google.com.vn", "google.com.ua", "google.com.pe",
    "google.com.sa", "google.com.my", "google.com.bd",
    # European
    "google.de", "google.fr", "google.it", "google.es", "google.nl",
    "google.pl", "google.se", "google.no", "google.fi", "google.dk",
    "google.at", "google.ch", "google.be", "google.pt", "google.ie",
    "google.cz", "google.ro", "google.hu", "google.gr", "google.bg",
    "google.sk", "google.hr", "google.lt", "google.lv", "google.ee",
    "google.si",
    # Other
    "google.ru", "google.ca", "google.cl", "google.ae",
})


def _extract_cookies(raw_cookies: list) -> dict:
    """Filter to Google auth cookies from relevant domains.

    Supports .google.com and 60+ regional Google domains for international users.
    Prioritizes .google.com values over regional duplicates (e.g., .google.co.il).
    """
    result = {}
    result_domains: dict[str, str] = {}
    # Build allowed domain set: base domains + regional variants with dots
    allowed = {
        ".google.com", "google.com",
        ".stitch.withgoogle.com", "stitch.withgoogle.com",
        ".withgoogle.com", "withgoogle.com",
        ".accounts.google.com", "accounts.google.com",
        ".googleusercontent.com",  # For authenticated media downloads
    }
    for cctld in GOOGLE_REGIONAL_CCTLDS:
        allowed.add(f".{cctld}")
        allowed.add(cctld)

    for c in raw_cookies:
        domain = c.get("domain", "")
        name = c.get("name", "")
        if domain not in allowed or not name:
            continue
        # Prefer .google.com over regional domains — don't overwrite a
        # .google.com cookie with the same name from a regional domain.
        if name not in result or domain == ".google.com":
            result[name] = c.get("value", "")
            result_domains[name] = domain
    return result


def _save_auth(data: dict):
    _auth_dir_setup()
    AUTH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(AUTH_FILE, 0o600)


def load_cookies() -> dict:
    """Load stored cookies. Checks env var first, then file.

    Priority:
    1. CLI_WEB_STITCH_AUTH_JSON env var (for CI/CD)
    2. ~/.config/cli-web-stitch/auth.json file

    Raises AuthError if not configured.
    """
    # Check environment variable first (CI/CD, headless)
    env_auth = os.environ.get("CLI_WEB_STITCH_AUTH_JSON")
    if env_auth:
        try:
            data = json.loads(env_auth)
            cookies = data.get("cookies", data) if isinstance(data, dict) else {}
            if cookies:
                return cookies
        except (json.JSONDecodeError, TypeError):
            pass  # Fall through to file-based auth

    if not AUTH_FILE.exists():
        raise AuthError(
            "Not authenticated. Run: cli-web-stitch auth login"
        )
    try:
        data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        cookies = data.get("cookies", {})
        if not cookies:
            raise AuthError("No cookies found. Run: cli-web-stitch auth login")
        # Handle raw playwright state-save format: cookies is a list of objects
        if isinstance(cookies, list):
            cookies = _extract_cookies(cookies)
            if not cookies:
                raise AuthError("No Google cookies found. Run: cli-web-stitch auth login")
        return cookies
    except (json.JSONDecodeError, KeyError) as e:
        raise AuthError(f"Corrupted auth file: {e}. Run: cli-web-stitch auth login")


def fetch_tokens(cookies: dict) -> tuple[str, str, str]:
    """Fetch and extract CSRF token, session ID, and build label from homepage.

    Returns:
        (csrf_token, session_id, build_label)

    Raises:
        AuthError: If tokens cannot be extracted (session expired or redirected)
    """
    try:
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
    except httpx.RequestError as e:
        raise AuthError(f"Network error fetching homepage: {e}")

    html = resp.text

    # Check for redirect to accounts.google.com (auth expired)
    if "accounts.google.com" in str(resp.url) or "signin" in str(resp.url).lower():
        raise AuthError("Session expired — run: cli-web-stitch auth login")

    m = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
    csrf = m.group(1) if m else None

    m = re.search(r'"FdrFJe"\s*:\s*"(-?[0-9]+)"', html)
    session_id = m.group(1) if m else None

    m = re.search(r'"cfb2h"\s*:\s*"([^"]+)"', html)
    build_label = m.group(1) if m else None

    if not csrf or not session_id or not build_label:
        raise AuthError(
            "Could not extract auth tokens from Stitch homepage. "
            "Session may have expired — run: cli-web-stitch auth login"
        )

    return csrf, session_id, build_label


def fetch_user_info(cookies: dict) -> dict:
    """Extract user email and display name from the Stitch homepage.

    Returns:
        dict with 'email', 'display_name', 'avatar_url' keys

    Raises:
        AuthError: If the page cannot be fetched or user info is missing
    """
    try:
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
    except httpx.RequestError as e:
        raise AuthError(f"Network error: {e}")

    html = resp.text

    # Email is stored in WIZ_global_data under "oPEP7c"
    m = re.search(r'"oPEP7c"\s*:\s*"([^"]+)"', html)
    email = m.group(1) if m else None

    # Display name wrapped in RTL isolate markers \u202a...\u202c in aria-label
    m = re.search(r'aria-label="[^"]*\u202a([^\u202c]+)\u202c', html)
    display_name = m.group(1).strip() if m else ""

    if not email:
        raise AuthError("Could not extract user email from homepage — session may have expired")

    return {"email": email, "display_name": display_name, "avatar_url": None}


def get_auth_status() -> dict:
    """Return auth status for display."""
    if not AUTH_FILE.exists():
        return {"configured": False, "message": "Not configured"}
    try:
        cookies = load_cookies()
        # Try fetching tokens to validate live session
        _csrf, session_id, _build_label = fetch_tokens(cookies)
        return {
            "configured": True,
            "valid": True,
            "cookie_count": len(cookies),
            "session_id": session_id[:8] + "..." if session_id else None,
            "message": "OK — session active",
        }
    except AuthError as e:
        return {"configured": True, "valid": False, "message": str(e)}
