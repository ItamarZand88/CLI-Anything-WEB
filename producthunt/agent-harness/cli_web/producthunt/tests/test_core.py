"""Unit tests for cli-web-producthunt with mocked HTTP responses.

All HTTP calls are mocked via ``unittest.mock.patch`` against
``curl_cffi.requests.Session.get`` so nothing hits the network.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from cli_web.producthunt.core.client import ProductHuntClient
from cli_web.producthunt.core.exceptions import (
    AppError,
    AuthError,
    GraphQLError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from cli_web.producthunt.core.models import Post, User


# ---------------------------------------------------------------------------
# HTML Fixtures
# ---------------------------------------------------------------------------

POST_CARDS_HTML = """\
<html><body>
<div data-test="post-item-1101888">
  <img src="https://ph-files.imgix.net/thumb1.png" />
  <div data-test="post-name-1101888">
    <a href="/products/stitch-2-0-by-google-2">1. Stitch 2.0 by Google</a>
  </div>
  <div>AI-powered design tool for rapid prototyping</div>
  <a href="/topics/design-tools">Design Tools</a>
  <a href="/topics/artificial-intelligence">Artificial Intelligence</a>
  <button>42</button>
  <button>587</button>
</div>

<div data-test="post-item-1101900">
  <img src="https://ph-files.imgix.net/thumb2.png" />
  <div data-test="post-name-1101900">
    <a href="/products/acme-app">Acme App</a>
  </div>
  <div>Ship faster with less code</div>
  <a href="/topics/developer-tools">Developer Tools</a>
  <button>15</button>
  <button>230</button>
</div>

<div data-test="post-item-1101910">
  <img src="https://ph-files.imgix.net/thumb3.png" />
  <div data-test="post-name-1101910">
    <a href="/posts/cool-thing">3. Cool Thing</a>
  </div>
  <div>The coolest thing ever</div>
  <button>5</button>
  <button>99</button>
</div>
</body></html>
"""

PRODUCT_DETAIL_HTML = """\
<html>
<head>
  <title>Stitch 2.0 by Google - Product Hunt</title>
  <meta name="description" content="AI-powered design tool for rapid prototyping by Google." />
  <meta property="og:image" content="https://ph-files.imgix.net/og-stitch.png" />
</head>
<body>
  <a href="/topics/design-tools">Design Tools</a>
  <a href="/topics/artificial-intelligence">Artificial Intelligence</a>
  <button>42</button>
  <button>587</button>
</body>
</html>
"""

USER_PROFILE_HTML = """\
<html>
<head>
  <title>Ryan Hoover (@rrhoover) - Product Hunt</title>
  <meta property="og:title" content="Ryan Hoover (@rrhoover)" />
  <meta name="description" content="Founder of Product Hunt" />
  <meta property="og:image" content="https://ph-files.imgix.net/ryan.jpg" />
</head>
<body>
  <span>155,000 Followers</span>
</body>
</html>
"""


def _mock_response(status_code: int, text: str = "", headers: dict | None = None):
    """Create a mock curl_cffi response object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.headers = headers or {}
    return resp


# ---------------------------------------------------------------------------
# TestParsePostCards
# ---------------------------------------------------------------------------

class TestParsePostCards(unittest.TestCase):
    """Test _parse_post_cards with realistic HTML fixtures."""

    def setUp(self):
        self.soup = BeautifulSoup(POST_CARDS_HTML, "html.parser")
        self.posts = ProductHuntClient._parse_post_cards(self.soup)

    def test_returns_list_of_posts(self):
        self.assertIsInstance(self.posts, list)
        self.assertEqual(len(self.posts), 3)
        for p in self.posts:
            self.assertIsInstance(p, Post)

    def test_name_extraction(self):
        # Rank prefix "1. " should be stripped from name
        self.assertEqual(self.posts[0].name, "Stitch 2.0 by Google")
        self.assertEqual(self.posts[1].name, "Acme App")

    def test_slug_extraction(self):
        self.assertEqual(self.posts[0].slug, "stitch-2-0-by-google-2")
        self.assertEqual(self.posts[1].slug, "acme-app")

    def test_rank_from_prefix(self):
        self.assertEqual(self.posts[0].rank, 1)
        # Acme App has no rank prefix
        self.assertIsNone(self.posts[1].rank)
        self.assertEqual(self.posts[2].rank, 3)

    def test_votes_and_comments(self):
        # First button = comments, second = votes
        self.assertEqual(self.posts[0].comments_count, 42)
        self.assertEqual(self.posts[0].votes_count, 587)

    def test_topics_from_links(self):
        self.assertIn("Design Tools", self.posts[0].topics)
        self.assertIn("Artificial Intelligence", self.posts[0].topics)
        self.assertIn("Developer Tools", self.posts[1].topics)

    def test_tagline_from_sibling(self):
        self.assertEqual(self.posts[0].tagline, "AI-powered design tool for rapid prototyping")
        self.assertEqual(self.posts[1].tagline, "Ship faster with less code")

    def test_thumbnail_url(self):
        self.assertEqual(self.posts[0].thumbnail_url, "https://ph-files.imgix.net/thumb1.png")

    def test_post_id_from_data_test(self):
        self.assertEqual(self.posts[0].id, "1101888")

    def test_url_built_from_slug(self):
        self.assertEqual(
            self.posts[0].url,
            "https://www.producthunt.com/products/stitch-2-0-by-google-2",
        )


# ---------------------------------------------------------------------------
# TestParseProductDetail
# ---------------------------------------------------------------------------

class TestParseProductDetail(unittest.TestCase):
    """Test get_post() parsing of product detail HTML."""

    @patch("cli_web.producthunt.core.client.ProductHuntClient._get")
    def test_title_parsing(self, mock_get):
        mock_get.return_value = BeautifulSoup(PRODUCT_DETAIL_HTML, "html.parser")
        client = ProductHuntClient()
        post = client.get_post("stitch-2-0-by-google-2")
        self.assertEqual(post.name, "Stitch 2.0 by Google")

    @patch("cli_web.producthunt.core.client.ProductHuntClient._get")
    def test_description_from_meta(self, mock_get):
        mock_get.return_value = BeautifulSoup(PRODUCT_DETAIL_HTML, "html.parser")
        client = ProductHuntClient()
        post = client.get_post("stitch-2-0-by-google-2")
        self.assertEqual(
            post.description,
            "AI-powered design tool for rapid prototyping by Google.",
        )

    @patch("cli_web.producthunt.core.client.ProductHuntClient._get")
    def test_topics_extraction(self, mock_get):
        mock_get.return_value = BeautifulSoup(PRODUCT_DETAIL_HTML, "html.parser")
        client = ProductHuntClient()
        post = client.get_post("stitch-2-0-by-google-2")
        self.assertIn("Design Tools", post.topics)
        self.assertIn("Artificial Intelligence", post.topics)

    @patch("cli_web.producthunt.core.client.ProductHuntClient._get")
    def test_thumbnail_from_og_image(self, mock_get):
        mock_get.return_value = BeautifulSoup(PRODUCT_DETAIL_HTML, "html.parser")
        client = ProductHuntClient()
        post = client.get_post("stitch-2-0-by-google-2")
        self.assertEqual(post.thumbnail_url, "https://ph-files.imgix.net/og-stitch.png")

    @patch("cli_web.producthunt.core.client.ProductHuntClient._get")
    def test_votes_and_comments(self, mock_get):
        mock_get.return_value = BeautifulSoup(PRODUCT_DETAIL_HTML, "html.parser")
        client = ProductHuntClient()
        post = client.get_post("stitch-2-0-by-google-2")
        self.assertEqual(post.votes_count, 587)
        self.assertEqual(post.comments_count, 42)


# ---------------------------------------------------------------------------
# TestParseUserProfile
# ---------------------------------------------------------------------------

class TestParseUserProfile(unittest.TestCase):
    """Test get_user() parsing of user profile HTML."""

    @patch("cli_web.producthunt.core.client.ProductHuntClient._get")
    def test_name_parsing(self, mock_get):
        mock_get.return_value = BeautifulSoup(USER_PROFILE_HTML, "html.parser")
        client = ProductHuntClient()
        user = client.get_user("rrhoover")
        self.assertEqual(user.name, "Ryan Hoover")

    @patch("cli_web.producthunt.core.client.ProductHuntClient._get")
    def test_headline(self, mock_get):
        mock_get.return_value = BeautifulSoup(USER_PROFILE_HTML, "html.parser")
        client = ProductHuntClient()
        user = client.get_user("rrhoover")
        self.assertEqual(user.headline, "Founder of Product Hunt")

    @patch("cli_web.producthunt.core.client.ProductHuntClient._get")
    def test_profile_image(self, mock_get):
        mock_get.return_value = BeautifulSoup(USER_PROFILE_HTML, "html.parser")
        client = ProductHuntClient()
        user = client.get_user("rrhoover")
        self.assertEqual(user.profile_image, "https://ph-files.imgix.net/ryan.jpg")

    @patch("cli_web.producthunt.core.client.ProductHuntClient._get")
    def test_followers_count(self, mock_get):
        mock_get.return_value = BeautifulSoup(USER_PROFILE_HTML, "html.parser")
        client = ProductHuntClient()
        user = client.get_user("rrhoover")
        self.assertEqual(user.followers_count, 155000)


# ---------------------------------------------------------------------------
# TestClientHTTPErrors
# ---------------------------------------------------------------------------

class TestClientHTTPErrors(unittest.TestCase):
    """Test HTTP status code to domain exception mapping."""

    def _make_client_and_get(self, status_code, headers=None):
        client = ProductHuntClient()
        with patch.object(
            client._session,
            "get",
            return_value=_mock_response(status_code, headers=headers or {}),
        ):
            client._get("https://www.producthunt.com/test")

    def test_403_raises_auth_error(self):
        with self.assertRaises(AuthError) as ctx:
            self._make_client_and_get(403)
        self.assertIn("Cloudflare", str(ctx.exception))

    def test_404_raises_not_found_error(self):
        with self.assertRaises(NotFoundError):
            self._make_client_and_get(404)

    def test_429_raises_rate_limit_error(self):
        with self.assertRaises(RateLimitError):
            self._make_client_and_get(429)

    def test_429_with_retry_after(self):
        with self.assertRaises(RateLimitError) as ctx:
            self._make_client_and_get(429, headers={"Retry-After": "60"})
        self.assertEqual(ctx.exception.retry_after, 60.0)

    def test_500_raises_server_error(self):
        with self.assertRaises(ServerError) as ctx:
            self._make_client_and_get(500)
        self.assertEqual(ctx.exception.status_code, 500)

    def test_502_raises_server_error(self):
        with self.assertRaises(ServerError) as ctx:
            self._make_client_and_get(502)
        self.assertEqual(ctx.exception.status_code, 502)

    def test_network_exception_raises_network_error(self):
        client = ProductHuntClient()
        with patch.object(
            client._session, "get", side_effect=ConnectionError("DNS failure")
        ):
            with self.assertRaises(NetworkError):
                client._get("https://www.producthunt.com/test")


# ---------------------------------------------------------------------------
# TestExceptions
# ---------------------------------------------------------------------------

class TestExceptions(unittest.TestCase):
    """Test exception to_dict() methods produce correct error codes."""

    def test_app_error_to_dict(self):
        d = AppError("something broke").to_dict()
        self.assertTrue(d["error"])
        self.assertEqual(d["code"], "UNKNOWN")

    def test_auth_error_to_dict(self):
        d = AuthError("blocked", recoverable=True).to_dict()
        self.assertEqual(d["code"], "AUTH_EXPIRED")

    def test_rate_limit_error_to_dict(self):
        d = RateLimitError("slow down", retry_after=30.0).to_dict()
        self.assertEqual(d["code"], "RATE_LIMITED")
        self.assertEqual(d["retry_after"], 30.0)

    def test_not_found_error_to_dict(self):
        d = NotFoundError("page gone").to_dict()
        self.assertEqual(d["code"], "NOT_FOUND")

    def test_server_error_to_dict(self):
        d = ServerError("oops", status_code=503).to_dict()
        self.assertEqual(d["code"], "SERVER_ERROR")

    def test_network_error_to_dict(self):
        d = NetworkError("timeout").to_dict()
        self.assertEqual(d["code"], "NETWORK_ERROR")

    def test_graphql_error_to_dict(self):
        d = GraphQLError("bad query").to_dict()
        self.assertEqual(d["code"], "GRAPHQL_ERROR")


# ---------------------------------------------------------------------------
# TestModels
# ---------------------------------------------------------------------------

class TestModels(unittest.TestCase):
    """Test Post and User model serialization."""

    def test_post_to_dict_contains_all_keys(self):
        p = Post(
            id="123",
            name="Test",
            tagline="A test",
            slug="test",
            url="https://www.producthunt.com/products/test",
            votes_count=10,
            comments_count=3,
            topics=["AI"],
            rank=1,
        )
        d = p.to_dict()
        self.assertEqual(d["id"], "123")
        self.assertEqual(d["name"], "Test")
        self.assertEqual(d["votes_count"], 10)
        self.assertEqual(d["rank"], 1)
        self.assertEqual(d["topics"], ["AI"])

    def test_post_from_card_strips_rank(self):
        p = Post.from_card({"name": "2. Acme", "slug": "acme"})
        self.assertEqual(p.name, "Acme")
        self.assertEqual(p.rank, 2)

    def test_post_from_card_no_rank(self):
        p = Post.from_card({"name": "Acme", "slug": "acme"})
        self.assertEqual(p.name, "Acme")
        self.assertIsNone(p.rank)

    def test_user_to_dict_contains_all_keys(self):
        u = User(
            id="rrhoover",
            name="Ryan Hoover",
            username="rrhoover",
            headline="Founder",
            followers_count=155000,
        )
        d = u.to_dict()
        self.assertEqual(d["username"], "rrhoover")
        self.assertEqual(d["followers_count"], 155000)
        self.assertIn("website_url", d)

    def test_user_from_card(self):
        u = User.from_card({"id": "x", "name": "X User", "username": "x"})
        self.assertEqual(u.name, "X User")
        self.assertEqual(u.followers_count, 0)


if __name__ == "__main__":
    unittest.main()
