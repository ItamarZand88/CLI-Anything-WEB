"""Configuration constants and helpers."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "notebooklm"
CLI_NAME = "cli-web-notebooklm"
VERSION = "0.1.0"

CONFIG_DIR = Path.home() / ".config" / "cli-web-notebooklm"
AUTH_FILE = CONFIG_DIR / "auth.json"
SESSION_FILE = CONFIG_DIR / "session.json"

BASE_URL = "https://notebooklm.google.com"

# RPC IDs
RPC_USER_SETTINGS = "ZwVcOc"
RPC_LIST_NOTEBOOKS = "wXbhsf"
RPC_RECOMMENDED_NOTEBOOKS = "ub2Bae"
RPC_SUBSCRIPTION_INFO = "ozz5Z"
RPC_NOTEBOOK_DETAILS = "rLM1Ne"
RPC_CHAT_SESSIONS = "hPTbtc"
RPC_SHARING_INFO = "JFMDGd"
RPC_OUTPUT_TYPES = "sqTeoe"
RPC_NOTEBOOK_NOTES = "e3bVqc"
RPC_LIST_ARTIFACTS = "gArtLc"
RPC_SESSION_ID = "VfAZjd"
RPC_LAST_MODIFIED = "cFji9"
