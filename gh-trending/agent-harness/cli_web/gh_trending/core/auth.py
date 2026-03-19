"""Auth management for cli-web-gh-trending.

GitHub Trending is public — auth is optional but supported for
future features (starring, user-specific data).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .exceptions import AuthError

AUTH_DIR = Path.home() / ".config" / "cli-web-gh-trending"
AUTH_FILE = AUTH_DIR / "auth.json"
SESSION_NAME = "github-auth"
APP_URL = "https://github.com"


def load_cookies() -> dict[str, str]:
    """Load cookies from auth.json. Returns empty dict if not configured."""
    # Environment variable override for CI/CD
    env_path = os.environ.get("CLI_WEB_GH_TRENDING_AUTH_JSON")
    if env_path:
        auth_file = Path(env_path)
    else:
        auth_file = AUTH_FILE

    if not auth_file.exists():
        return {}

    try:
        state = json.loads(auth_file.read_text())
        return {c["name"]: c["value"] for c in state.get("cookies", [])}
    except Exception as exc:
        raise AuthError(f"Failed to read auth.json: {exc}") from exc


def save_auth_state(state: dict) -> None:
    """Save playwright-cli storage state to auth.json."""
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(json.dumps(state, indent=2))
    AUTH_FILE.chmod(0o600)


def auth_status() -> dict:
    """Return auth status information."""
    env_path = os.environ.get("CLI_WEB_GH_TRENDING_AUTH_JSON")
    auth_file = Path(env_path) if env_path else AUTH_FILE

    if not auth_file.exists():
        return {
            "authenticated": False,
            "message": "Not authenticated. Run: cli-web-gh-trending auth login",
            "auth_file": str(auth_file),
        }

    try:
        state = json.loads(auth_file.read_text())
        cookies = state.get("cookies", [])
        github_cookies = [c for c in cookies if "github.com" in c.get("domain", "")]
        logged_in = any(c["name"] == "user_session" for c in github_cookies)
        return {
            "authenticated": logged_in,
            "message": "Logged in" if logged_in else "Cookies present but no user session",
            "auth_file": str(auth_file),
            "cookie_count": len(github_cookies),
        }
    except Exception as exc:
        return {
            "authenticated": False,
            "message": f"Auth file error: {exc}",
            "auth_file": str(auth_file),
        }


def login() -> None:
    """Launch browser via playwright-cli for GitHub login."""
    print("Opening GitHub in browser. Please log in, then press ENTER here.")
    subprocess.run(
        ["npx", "@playwright/cli@latest", f"-s={SESSION_NAME}", "open", APP_URL,
         "--headed", "--persistent"],
        check=True,
    )
    input("\nPress ENTER after you have logged in to GitHub... ")
    subprocess.run(
        ["npx", "@playwright/cli@latest", f"-s={SESSION_NAME}", "state-save",
         str(AUTH_FILE)],
        check=True,
    )
    subprocess.run(
        ["npx", "@playwright/cli@latest", f"-s={SESSION_NAME}", "close"],
        check=False,
    )
    AUTH_FILE.chmod(0o600)
    print(f"Auth saved to {AUTH_FILE}")


def login_from_json(cookies_json_path: Path) -> None:
    """Import cookies from a manually exported JSON file."""
    data = json.loads(cookies_json_path.read_text())
    # Wrap in playwright storage state format if raw cookies list
    if isinstance(data, list):
        state = {"cookies": data, "origins": []}
    else:
        state = data
    save_auth_state(state)
    print(f"Auth imported from {cookies_json_path} → {AUTH_FILE}")
