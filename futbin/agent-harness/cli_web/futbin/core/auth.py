"""Auth module for FUTBIN.

FUTBIN is a public read-only site — no authentication is required.
This module is a stub that provides auth status and a no-op login.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from cli_web.futbin.utils.config import get_config_dir

AUTH_FILE = get_config_dir() / "auth.json"


def is_authenticated() -> bool:
    """Always True — FUTBIN is public."""
    return True


def get_cookies() -> dict:
    """Return stored cookies if available, else empty dict."""
    if AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text())
            return data.get("cookies", {})
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def login(app_url: str = "https://www.futbin.com") -> None:
    """
    Optional login for personal features (My Evolutions, Saved Squads).
    Uses playwright-cli to open the browser for manual login.
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    state_file = config_dir / "futbin-state.json"
    session = "futbin-auth"

    print("Opening FUTBIN in browser — log in to your account, then press ENTER here.")
    subprocess.run(
        ["npx", "@playwright/cli@latest", f"-s={session}", "open", app_url,
         "--headed", "--persistent"],
        check=True,
    )
    input("Press ENTER after logging in... ")

    subprocess.run(
        ["npx", "@playwright/cli@latest", f"-s={session}", "state-save", str(state_file)],
        check=True,
    )
    subprocess.run(
        ["npx", "@playwright/cli@latest", f"-s={session}", "close"],
        check=True,
    )

    # Parse and store cookies
    state = json.loads(state_file.read_text())
    cookies = {c["name"]: c["value"] for c in state.get("cookies", [])}

    AUTH_FILE.write_text(json.dumps({"cookies": cookies}, indent=2))
    AUTH_FILE.chmod(0o600)
    print(f"Auth saved to {AUTH_FILE}")


def logout() -> None:
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()
        print("Logged out.")
    else:
        print("Not logged in.")


def get_status() -> dict:
    return {
        "authenticated": is_authenticated(),
        "note": "FUTBIN is public — no auth required for core features.",
        "cookies_stored": AUTH_FILE.exists(),
        "auth_file": str(AUTH_FILE),
    }
