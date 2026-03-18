"""Auth management for cli-web-notebooklm.

Handles:
- Login via playwright-cli (opens browser, saves state)
- Cookie import from JSON file (manual fallback)
- Token extraction (CSRF, session ID, build label) from homepage
- Secure storage at ~/.config/cli-web-notebooklm/auth.json
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import httpx

AUTH_DIR = Path.home() / ".config" / "cli-web-notebooklm"
AUTH_FILE = AUTH_DIR / "auth.json"
BASE_URL = "https://notebooklm.google.com"

# Google cookies relevant for NotebookLM auth
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


def _npx() -> str:
    """Find npx executable, checking common Windows locations."""
    path = shutil.which("npx")
    if path:
        return path
    # Common Windows locations (nvm4w, nvm, direct install)
    candidates = [
        r"C:\nvm4w\nodejs\npx.cmd",
        r"C:\nvm\versions\node\current\npx.cmd",
        r"C:\Program Files\nodejs\npx.cmd",
        r"C:\Program Files (x86)\nodejs\npx.cmd",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    raise AuthError("npx not found — install Node.js from https://nodejs.org/")


def login_browser(headed: bool = True):
    """Open browser via playwright-cli for Google login, save auth state."""
    _auth_dir_setup()
    session = "notebooklm-auth"
    state_file = AUTH_DIR / "playwright-state.json"
    npx = _npx()

    print(f"Opening browser for NotebookLM login...")
    subprocess.run(
        [npx, "@playwright/cli@latest", f"-s={session}", "open", BASE_URL,
         "--headed", "--persistent"],
        check=False,  # Browser stays open
    )

    input("Log in to Google in the browser, then press ENTER here to continue...")

    # Save playwright state
    result = subprocess.run(
        [npx, "@playwright/cli@latest", f"-s={session}", "state-save", str(state_file)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AuthError(f"Failed to save auth state: {result.stderr}")

    # Close the session
    subprocess.run(
        [npx, "@playwright/cli@latest", f"-s={session}", "close"],
        capture_output=True,
    )

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
    """
    result = {}
    # Build allowed domain set: base domains + regional variants with dots
    allowed = {
        ".google.com", "google.com",
        ".notebooklm.google.com", "notebooklm.google.com",
        ".accounts.google.com", "accounts.google.com",
        ".googleusercontent.com",  # For authenticated media downloads
    }
    for cctld in GOOGLE_REGIONAL_CCTLDS:
        allowed.add(f".{cctld}")
        allowed.add(cctld)

    for c in raw_cookies:
        domain = c.get("domain", "")
        name = c.get("name", "")
        if domain in allowed and name:
            result[name] = c.get("value", "")
    return result


def _save_auth(data: dict):
    _auth_dir_setup()
    AUTH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(AUTH_FILE, 0o600)


def load_cookies() -> dict:
    """Load stored cookies. Checks env var first, then file.

    Priority:
    1. CLI_WEB_NOTEBOOKLM_AUTH_JSON env var (for CI/CD)
    2. ~/.config/cli-web-notebooklm/auth.json file

    Raises AuthError if not configured.
    """
    # Check environment variable first (CI/CD, headless)
    env_auth = os.environ.get("CLI_WEB_NOTEBOOKLM_AUTH_JSON")
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
            "Not authenticated. Run: cli-web-notebooklm auth login"
        )
    try:
        data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        cookies = data.get("cookies", {})
        if not cookies:
            raise AuthError("No cookies found. Run: cli-web-notebooklm auth login")
        return cookies
    except (json.JSONDecodeError, KeyError) as e:
        raise AuthError(f"Corrupted auth file: {e}. Run: cli-web-notebooklm auth login")


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
        raise AuthError("Session expired — run: cli-web-notebooklm auth login")

    m = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
    csrf = m.group(1) if m else None

    m = re.search(r'"FdrFJe"\s*:\s*"(-?[0-9]+)"', html)
    session_id = m.group(1) if m else None

    m = re.search(r'"cfb2h"\s*:\s*"([^"]+)"', html)
    build_label = m.group(1) if m else None

    if not csrf or not session_id or not build_label:
        raise AuthError(
            "Could not extract auth tokens from NotebookLM homepage. "
            "Session may have expired — run: cli-web-notebooklm auth login"
        )

    return csrf, session_id, build_label


def fetch_user_info(cookies: dict) -> dict:
    """Extract user email and display name from the NotebookLM homepage.

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
        csrf, session_id, build_label = fetch_tokens(cookies)
        return {
            "configured": True,
            "valid": True,
            "cookie_count": len(cookies),
            "session_id": session_id[:8] + "..." if session_id else None,
            "message": "OK — session active",
        }
    except AuthError as e:
        return {"configured": True, "valid": False, "message": str(e)}
