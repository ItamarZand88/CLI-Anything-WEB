"""End-to-end tests for cli-web-producthunt.

TestLiveAPI — hits the real Product Hunt site (no auth needed).
TestCLISubprocess — invokes the CLI binary and checks JSON output.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest

from cli_web.producthunt.core.client import ProductHuntClient
from cli_web.producthunt.core.models import Post, User


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _resolve_cli(name: str) -> list[str]:
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        path = shutil.which(name)
        if not path:
            raise FileNotFoundError(f"{name} not found in PATH")
        return [path]
    return ["python", "-m", "cli_web.producthunt.producthunt_cli"]


# ---------------------------------------------------------------------------
# TestLiveAPI
# ---------------------------------------------------------------------------

class TestLiveAPI(unittest.TestCase):
    """E2E tests that hit the real Product Hunt site."""

    @classmethod
    def setUpClass(cls):
        cls.client = ProductHuntClient()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_list_posts(self):
        """Homepage returns a non-empty list of Post objects with core fields."""
        posts = self.client.list_posts()
        self.assertIsInstance(posts, list)
        self.assertGreater(len(posts), 0, "Expected at least one post from homepage")
        first = posts[0]
        self.assertIsInstance(first, Post)
        self.assertTrue(first.name, "Post name should be non-empty")
        self.assertTrue(first.slug, "Post slug should be non-empty")

    def test_get_post(self):
        """Fetch a well-known product detail page and verify fields."""
        post = self.client.get_post("producthunt")
        self.assertIsInstance(post, Post)
        # The canonical name should contain "Product Hunt"
        self.assertIn("Product Hunt", post.name)
        self.assertEqual(post.slug, "producthunt")
        # Description should exist
        self.assertTrue(post.description, "Expected non-empty description")

    def test_leaderboard(self):
        """Leaderboard returns ranked products."""
        posts = self.client.list_leaderboard(period="daily")
        self.assertIsInstance(posts, list)
        self.assertGreater(len(posts), 0, "Expected at least one leaderboard entry")
        for p in posts:
            self.assertIsInstance(p, Post)
            self.assertTrue(p.name, "Leaderboard post name should be non-empty")

    def test_get_user(self):
        """Fetch Ryan Hoover's profile."""
        user = self.client.get_user("rrhoover")
        self.assertIsInstance(user, User)
        self.assertEqual(user.username, "rrhoover")
        self.assertIn("Ryan", user.name)
        self.assertGreater(user.followers_count, 100000)

    def test_list_posts_have_urls(self):
        """All posts from homepage should have properly formed URLs."""
        posts = self.client.list_posts()
        for p in posts[:5]:
            self.assertTrue(
                p.url.startswith("https://www.producthunt.com/products/"),
                f"Unexpected URL format: {p.url}",
            )


# ---------------------------------------------------------------------------
# TestCLISubprocess
# ---------------------------------------------------------------------------

class TestCLISubprocess(unittest.TestCase):
    """Subprocess tests invoking the CLI binary."""

    @classmethod
    def setUpClass(cls):
        cls.cli_cmd = _resolve_cli("cli-web-producthunt")

    def _run(self, *args: str, expect_rc: int = 0) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [*self.cli_cmd, *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        self.assertEqual(
            result.returncode,
            expect_rc,
            f"Expected exit code {expect_rc} but got {result.returncode}.\n"
            f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}",
        )
        return result

    def test_help(self):
        """--help exits 0 and shows usage."""
        result = self._run("--help")
        self.assertIn("cli-web-producthunt", result.stdout.lower())

    def test_posts_list_json(self):
        """posts list --json produces valid JSON with expected fields."""
        result = self._run("posts", "list", "--json")
        data = json.loads(result.stdout)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        first = data[0]
        self.assertIn("name", first)
        self.assertIn("slug", first)

    def test_posts_get_json(self):
        """posts get --json returns a single product dict."""
        result = self._run("posts", "get", "producthunt", "--json")
        data = json.loads(result.stdout)
        self.assertIsInstance(data, dict)
        self.assertIn("Product Hunt", data.get("name", ""))

    def test_version(self):
        """--version exits 0 and prints version string."""
        result = self._run("--version")
        self.assertIn("cli-web-producthunt", result.stdout.lower())

    def test_posts_leaderboard_json(self):
        """posts leaderboard --json returns a list."""
        result = self._run("posts", "leaderboard", "--json")
        data = json.loads(result.stdout)
        self.assertIsInstance(data, list)

    def test_users_get_json(self):
        """users get rrhoover --json returns user dict."""
        result = self._run("users", "get", "rrhoover", "--json")
        data = json.loads(result.stdout)
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("username"), "rrhoover")

    def test_invalid_command(self):
        """Invalid subcommand produces non-zero exit code."""
        result = subprocess.run(
            [*self.cli_cmd, "nonexistent"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
