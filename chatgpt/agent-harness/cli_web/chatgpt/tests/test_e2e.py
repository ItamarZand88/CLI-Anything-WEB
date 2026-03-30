"""E2E and subprocess tests for cli-web-chatgpt.

Requires auth to be configured. Tests FAIL (not skip) if auth is missing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

from cli_web.chatgpt.core.auth import is_logged_in
from cli_web.chatgpt.core.client import ChatGPTClient


def _resolve_cli(name: str) -> str:
    """Find the installed CLI binary."""
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        path = shutil.which(name)
        if not path:
            pytest.fail(f"{name} not found on PATH (CLI_WEB_FORCE_INSTALLED=1)")
        return path
    path = shutil.which(name)
    if path:
        return path
    pytest.fail(f"{name} not found on PATH. Run: pip install -e .")


@pytest.fixture(scope="session")
def require_auth():
    if not is_logged_in():
        pytest.fail(
            "Auth not configured. Run: cli-web-chatgpt auth login"
        )


@pytest.fixture(scope="session")
def client(require_auth):
    with ChatGPTClient() as c:
        yield c


@pytest.fixture(scope="session")
def cli_path():
    return _resolve_cli("cli-web-chatgpt")


# ── E2E: Read-only API tests ──────────────────────────────────


class TestE2EReadOnly:
    """Test read-only endpoints that use curl_cffi (no browser needed)."""

    def test_get_me(self, client):
        data = client.get_me()
        assert "id" in data
        assert "email" in data
        assert "name" in data
        assert data["id"].startswith("user-")

    def test_get_models(self, client):
        models = client.get_models()
        assert isinstance(models, list)
        assert len(models) > 0
        slugs = [m["slug"] for m in models]
        # Should have at least one GPT model
        assert any("gpt" in s for s in slugs), f"No GPT model found in {slugs[:5]}"

    def test_list_conversations(self, client):
        data = client.list_conversations(limit=5)
        assert "items" in data
        items = data["items"]
        assert isinstance(items, list)
        if items:
            conv = items[0]
            assert "id" in conv
            assert "title" in conv
            assert "create_time" in conv

    def test_list_conversations_pagination(self, client):
        page1 = client.list_conversations(limit=2, offset=0)
        page2 = client.list_conversations(limit=2, offset=2)
        ids1 = {c["id"] for c in page1["items"]}
        ids2 = {c["id"] for c in page2["items"]}
        # Pages should not overlap
        assert ids1.isdisjoint(ids2) or len(ids1) == 0 or len(ids2) == 0

    def test_list_recent_images(self, client):
        data = client.list_recent_images(limit=5)
        assert "items" in data
        items = data["items"]
        assert isinstance(items, list)
        if items:
            img = items[0]
            assert "id" in img
            assert "title" in img
            assert "url" in img

    def test_get_image_styles(self, client):
        data = client.get_image_styles()
        assert "styles" in data
        styles = data["styles"]
        assert isinstance(styles, list)
        assert len(styles) > 0
        assert "id" in styles[0]
        assert "title" in styles[0]


# ── E2E: Chat tests (requires Camoufox browser) ───────────────


class TestE2EChat:
    """Test chat functionality via Camoufox headless browser."""

    def test_ask_simple_question(self, client):
        """Ask a simple question and verify text response."""
        result = client.send_message("What is the capital of Germany? One word only.")
        assert "text" in result
        assert result["text"], "Response text should not be empty"
        assert "Berlin" in result["text"] or "berlin" in result["text"].lower()
        assert result.get("conversation_id"), "Should return conversation_id"

    def test_ask_math_question(self, client):
        """Math questions use Instruments widget — verify extraction."""
        result = client.send_message("What is 100+200? Just the number.")
        assert result.get("text"), "Math response should not be empty"
        assert "300" in result["text"]

    def test_generate_image(self, client):
        """Generate an image and verify file_id is returned."""
        result = client.send_message(
            "A simple red square on white background",
            image_mode=True,
        )
        assert result.get("file_id"), "Image generation should return file_id"
        assert result.get("conversation_id"), "Should return conversation_id"
        assert result.get("download_url"), "Should return download_url"

    def test_download_generated_image(self, client):
        """Generate image then download it."""
        result = client.send_message(
            "A blue circle on gray background",
            image_mode=True,
        )
        if not result.get("download_url"):
            pytest.skip("No download URL returned")

        img_bytes = client.download_file(result["download_url"])
        assert len(img_bytes) > 1000, "Downloaded image should be >1KB"
        # PNG starts with specific bytes
        assert img_bytes[:4] == b"\x89PNG" or img_bytes[:2] == b"\xff\xd8", \
            "Downloaded file should be PNG or JPEG"


# ── E2E: File download tests ──────────────────────────────────


class TestE2EFileDownload:
    """Test file download from recent images."""

    def test_download_recent_image(self, client):
        """Download a recently generated image via its URL."""
        data = client.list_recent_images(limit=1)
        items = data.get("items", [])
        if not items:
            pytest.skip("No recent images to test download")

        url = items[0].get("url")
        assert url, "Image should have a URL"

        img_bytes = client.download_file(url)
        assert len(img_bytes) > 100, "Downloaded image should have content"


# ── Subprocess tests ───────────────────────────────────────────


class TestCLISubprocess:
    """Test the installed CLI binary via subprocess."""

    def test_help(self, cli_path):
        result = subprocess.run(
            [cli_path, "--help"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        assert "ChatGPT" in result.stdout

    def test_json_me(self, cli_path, require_auth):
        result = subprocess.run(
            [cli_path, "--json", "me"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "email" in data["data"]

    def test_json_models(self, cli_path, require_auth):
        result = subprocess.run(
            [cli_path, "--json", "models"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

    def test_json_conversations_list(self, cli_path, require_auth):
        result = subprocess.run(
            [cli_path, "--json", "conversations", "list", "--limit", "3"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "items" in data["data"]

    def test_json_images_list(self, cli_path, require_auth):
        result = subprocess.run(
            [cli_path, "--json", "images", "list", "--limit", "3"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "items" in data["data"]

    def test_json_auth_status(self, cli_path, require_auth):
        result = subprocess.run(
            [cli_path, "--json", "auth", "status"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["logged_in"] is True

    def test_json_chat_ask(self, cli_path, require_auth):
        """Subprocess chat ask — verify JSON output structure."""
        result = subprocess.run(
            [cli_path, "--json", "chat", "ask", "What is 1+1? Just the number."],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"].get("text"), "Chat response should have text"
        # Should not contain raw protocol data
        assert "wrb.fr" not in data["data"]["text"]
        assert "af.httprm" not in data["data"]["text"]

    def test_plain_conversations_list(self, cli_path, require_auth):
        """Non-JSON output should produce readable table."""
        result = subprocess.run(
            [cli_path, "conversations", "list", "--limit", "3"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        assert "Title" in result.stdout  # Table header
        assert "Updated" in result.stdout
