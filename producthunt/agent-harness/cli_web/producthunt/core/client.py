"""HTML-scraping client for Product Hunt using curl_cffi.

No API tokens or cookies required -- curl_cffi with Chrome TLS
impersonation bypasses Cloudflare protection automatically.
"""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

from .exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from .models import Post, User

BASE_URL = "https://www.producthunt.com"


class ProductHuntClient:
    """Scrape Product Hunt pages with Chrome TLS impersonation."""

    def __init__(self) -> None:
        self._session = curl_requests.Session(impersonate="chrome131")

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> ProductHuntClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Low-level transport
    # ------------------------------------------------------------------

    def _get(self, url: str) -> BeautifulSoup:
        """Fetch *url* and return a parsed BeautifulSoup tree.

        Maps HTTP status codes to domain exceptions.
        """
        try:
            resp = self._session.get(url, timeout=30)
        except Exception as exc:
            raise NetworkError(f"Request failed: {exc}") from exc

        status = resp.status_code
        if status == 403:
            raise AuthError(
                "Blocked by Cloudflare (HTTP 403). Try again later.",
                recoverable=True,
            )
        if status == 404:
            raise NotFoundError(f"Page not found: {url}")
        if status == 429:
            retry_after = resp.headers.get("Retry-After")
            raise RateLimitError(
                "Rate limited by Product Hunt",
                retry_after=float(retry_after) if retry_after else None,
            )
        if status >= 500:
            raise ServerError(f"Server error (HTTP {status})", status_code=status)
        if status != 200:
            raise ServerError(
                f"Unexpected HTTP {status}: {url}", status_code=status
            )

        return BeautifulSoup(resp.text, "html.parser")

    # ------------------------------------------------------------------
    # Shared card-parsing helper
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_post_cards(soup: BeautifulSoup) -> list[Post]:
        """Extract Post objects from a page containing post-name-* cards."""
        posts: list[Post] = []
        post_names = soup.find_all(attrs={"data-test": re.compile(r"^post-name-")})

        for card in post_names:
            data_test = card.get("data-test", "")
            post_id = data_test.replace("post-name-", "")

            # Name and slug from the <a> link inside the card
            link = card.find("a", href=True)
            if not link:
                continue
            name = link.get_text(strip=True)
            href = link["href"]
            # href may be /posts/<slug> or /products/<slug>
            slug = href.rsplit("/", 1)[-1] if "/" in href else href

            # Tagline from the next sibling element
            tagline_el = card.find_next_sibling()
            tagline = tagline_el.get_text(strip=True) if tagline_el else ""

            # Walk up to find the full card container (up to 8 levels)
            container = card
            for _ in range(8):
                if container.parent:
                    container = container.parent
                if container.get("data-test", "").startswith("post-item"):
                    break

            # Votes and comments from <button> elements with numeric text
            buttons = container.find_all("button")
            nums = [
                int(btn.get_text(strip=True))
                for btn in buttons
                if btn.get_text(strip=True).isdigit()
            ]
            comments_count = nums[0] if len(nums) >= 1 else 0
            votes_count = nums[1] if len(nums) >= 2 else 0

            # Topics from /topics/ links
            topic_links = [
                a.get_text(strip=True)
                for a in container.find_all(
                    "a", href=lambda h: h and "/topics/" in h
                )
            ]

            # Thumbnail from <img> in the container
            img = container.find("img", src=True)
            thumbnail_url = img["src"] if img else None

            posts.append(
                Post.from_card(
                    {
                        "id": post_id,
                        "name": name,
                        "tagline": tagline,
                        "slug": slug,
                        "votes_count": votes_count,
                        "comments_count": comments_count,
                        "topics": topic_links,
                        "thumbnail_url": thumbnail_url,
                    }
                )
            )

        return posts

    # ------------------------------------------------------------------
    # Posts
    # ------------------------------------------------------------------

    def list_posts(self) -> list[Post]:
        """Scrape the Product Hunt homepage for today's posts."""
        soup = self._get(BASE_URL)
        return self._parse_post_cards(soup)

    def get_post(self, slug: str) -> Post:
        """Scrape a single product detail page."""
        url = f"{BASE_URL}/products/{slug}"
        soup = self._get(url)

        # Title from <title> tag (usually "Name - Product Hunt")
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else slug
        # Clean up " - Product Hunt" or " | Product Hunt" suffix
        for sep in (" - Product Hunt", " | Product Hunt"):
            if title.endswith(sep):
                title = title[: -len(sep)]

        # Description from meta tag
        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc["content"] if meta_desc and meta_desc.get("content") else None

        # Thumbnail from og:image
        og_image = soup.find("meta", attrs={"property": "og:image"})
        thumbnail_url = og_image["content"] if og_image and og_image.get("content") else None

        # Try to extract votes/comments from the detail page
        votes_count = 0
        comments_count = 0
        buttons = soup.find_all("button")
        nums = [
            int(btn.get_text(strip=True))
            for btn in buttons
            if btn.get_text(strip=True).isdigit()
        ]
        if len(nums) >= 2:
            comments_count = nums[0]
            votes_count = nums[1]
        elif len(nums) == 1:
            votes_count = nums[0]

        # Topics from /topics/ links
        topics = [
            a.get_text(strip=True)
            for a in soup.find_all("a", href=lambda h: h and "/topics/" in h)
        ]

        return Post(
            id=slug,
            name=title,
            tagline=description or "",
            slug=slug,
            url=f"{BASE_URL}/products/{slug}",
            description=description,
            votes_count=votes_count,
            comments_count=comments_count,
            topics=topics,
            thumbnail_url=thumbnail_url,
        )

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------

    def list_leaderboard(
        self,
        period: str = "daily",
        year: Optional[int] = None,
        month: Optional[int] = None,
        day: Optional[int] = None,
    ) -> list[Post]:
        """Scrape the Product Hunt leaderboard.

        *period* must be one of ``daily``, ``weekly``, ``monthly``.
        Date components are optional; when omitted today's date is used
        for ``daily``, or the plain ``/leaderboard`` page for others.

        The only supported URL pattern is ``/leaderboard/daily/YYYY/M/D``.
        Product Hunt does not expose weekly or monthly leaderboard pages
        as scrapable lists, so *period* is accepted for API compatibility
        but always resolves to the daily leaderboard.
        """
        if year is not None and month is not None and day is not None:
            url = f"{BASE_URL}/leaderboard/daily/{year}/{month}/{day}"
        else:
            # Default to today
            from datetime import date as _date

            today = _date.today()
            url = f"{BASE_URL}/leaderboard/daily/{today.year}/{today.month}/{today.day}"

        soup = self._get(url)
        return self._parse_post_cards(soup)

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def get_user(self, username: str) -> User:
        """Scrape a user's public profile page."""
        url = f"{BASE_URL}/@{username}"
        soup = self._get(url)

        # Name — try og:title first (usually cleaner), then <title>
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            name = og_title["content"]
        else:
            title_tag = soup.find("title")
            name = title_tag.get_text(strip=True) if title_tag else ""

        # Clean suffixes like " - Product Hunt", "'s profile on Product Hunt"
        for suffix in (
            " - Product Hunt",
            " | Product Hunt",
            "'s profile on Product Hunt",
        ):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
        # Strip "(@username)" if present
        paren = f"(@{username})"
        if paren in name:
            name = name.replace(paren, "").strip()
        # Strip leading/trailing quotes or whitespace
        name = name.strip("\" '")

        # Headline from meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        headline = meta_desc["content"] if meta_desc and meta_desc.get("content") else None

        # Profile image from og:image
        og_image = soup.find("meta", attrs={"property": "og:image"})
        profile_image = og_image["content"] if og_image and og_image.get("content") else None

        # Followers — look for text matching "N Followers" or "N followers"
        followers_count = 0
        followers_pattern = re.compile(r"([\d,]+)\s+[Ff]ollowers?")
        for text_el in soup.find_all(string=followers_pattern):
            m = followers_pattern.search(text_el)
            if m:
                followers_count = int(m.group(1).replace(",", ""))
                break

        return User.from_card(
            {
                "id": username,
                "name": name or username,
                "username": username,
                "headline": headline,
                "profile_image": profile_image,
                "followers_count": followers_count,
            }
        )
