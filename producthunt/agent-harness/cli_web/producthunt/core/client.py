"""HTML-scraping client for Product Hunt using curl_cffi.

No API tokens or cookies required -- curl_cffi with Chrome TLS
impersonation bypasses Cloudflare protection automatically.
"""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

from .exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParsingError,
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

    def _fetch(self, url: str) -> str:
        """Fetch *url* and return raw HTML, mapping status codes to errors."""
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
            raise ServerError(f"Unexpected HTTP {status}: {url}", status_code=status)

        return resp.text

    def _get(self, url: str) -> BeautifulSoup:
        """Fetch *url* and return a parsed BeautifulSoup tree."""
        return BeautifulSoup(self._fetch(url), "html.parser")

    # ------------------------------------------------------------------
    # Shared card-parsing helper
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_posts(html: str) -> list[Post]:
        """Extract Post objects from a Product Hunt page.

        Product Hunt is a Next.js App Router app: the feed is embedded as JSON
        in the React Server Components flight stream (``self.__next_f``), not in
        ``data-test`` DOM attributes. Pull every ``{"__typename":"Post", ...}``
        object out of the page text and read its inline fields.
        """

        def _field(frag: str, key: str) -> str | None:
            m = re.search(r'"' + key + r'":"((?:[^"\\]|\\.)*)"', frag)
            return json.loads(f'"{m.group(1)}"') if m else None

        posts: list[Post] = []
        seen: set[str] = set()
        for match in re.finditer(r'\{"__typename":"Post"', html):
            start = match.start()
            depth = 0
            end = None
            # Brace-match the embedded JSON object (handles nested objects).
            for j in range(start, min(len(html), start + 4000)):
                ch = html[j]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            if end is None:
                continue
            frag = html[start:end]
            slug = _field(frag, "slug")
            name = _field(frag, "name")
            if not slug or not name or slug in seen:
                continue
            seen.add(slug)
            votes = re.search(r'"votesCount":(\d+)', frag)
            comments = re.search(r'"commentsCount":(\d+)', frag)
            post_id = re.search(r'"id":"(\d+)"', frag)
            posts.append(
                Post.from_card(
                    {
                        "id": post_id.group(1) if post_id else "",
                        "name": name,
                        "tagline": _field(frag, "tagline") or "",
                        "slug": slug,
                        "votes_count": int(votes.group(1)) if votes else 0,
                        "comments_count": int(comments.group(1)) if comments else 0,
                        "topics": [],
                        "thumbnail_url": None,
                    }
                )
            )

        return posts

    # ------------------------------------------------------------------
    # Posts
    # ------------------------------------------------------------------

    def list_posts(self) -> list[Post]:
        """Scrape the Product Hunt homepage for today's posts."""
        posts = self._extract_posts(self._fetch(BASE_URL))
        if not posts:
            raise ParsingError(
                "No posts found on the Product Hunt homepage — the page structure may have changed."
            )
        return posts

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
            int(btn.get_text(strip=True)) for btn in buttons if btn.get_text(strip=True).isdigit()
        ]
        if len(nums) >= 2:
            comments_count = nums[0]
            votes_count = nums[1]
        elif len(nums) == 1:
            votes_count = nums[0]

        # Topics from /topics/ links
        topics = [
            a.get_text(strip=True) for a in soup.find_all("a", href=lambda h: h and "/topics/" in h)
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
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
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

        return self._extract_posts(self._fetch(url))

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
