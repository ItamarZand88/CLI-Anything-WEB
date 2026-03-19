"""HTTP client for GitHub Trending — scrapes SSR HTML pages."""

from __future__ import annotations

import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .exceptions import NetworkError, NotFoundError, ParseError, RateLimitError, ServerError
from .models import TrendingDeveloper, TrendingRepo, _parse_int

BASE_URL = "https://github.com"
TRENDING_URL = f"{BASE_URL}/trending"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class GitHubClient:
    """Thin HTTP client wrapping GitHub trending pages."""

    def __init__(self, cookies: dict[str, str] | None = None, timeout: float = 30.0):
        self._cookies = cookies or {}
        self._timeout = timeout

    def _get(self, url: str, params: dict[str, str] | None = None) -> str:
        """Fetch a URL and return the HTML body."""
        params = {k: v for k, v in (params or {}).items() if v}
        try:
            with httpx.Client(
                headers=DEFAULT_HEADERS,
                cookies=self._cookies,
                follow_redirects=True,
                timeout=self._timeout,
            ) as client:
                response = client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {url}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error: {exc}") from exc

        if response.status_code == 404:
            raise NotFoundError("GitHub trending page")
        if response.status_code == 429:
            retry_after = int(response.headers.get("retry-after", "60"))
            raise RateLimitError(retry_after)
        if response.status_code >= 500:
            raise ServerError(response.status_code)
        if response.status_code != 200:
            raise NetworkError(f"Unexpected status {response.status_code}: {url}")

        return response.text

    # ------------------------------------------------------------------ repos

    def get_trending_repos(
        self,
        language: str = "",
        since: str = "daily",
        spoken_language_code: str = "",
    ) -> list[TrendingRepo]:
        """Fetch trending repositories."""
        params: dict[str, str] = {}
        if language:
            params["language"] = language
        if since and since != "daily":
            params["since"] = since
        if spoken_language_code:
            params["spoken_language_code"] = spoken_language_code

        html = self._get(TRENDING_URL, params)
        return self._parse_repos(html)

    def _parse_repos(self, html: str) -> list[TrendingRepo]:
        """Parse `article.Box-row` elements from trending repos HTML."""
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("article.Box-row")

        if not articles:
            # GitHub may return different markup — check for no-results message
            no_results = soup.select_one(".blankslate")
            if no_results:
                return []
            raise ParseError(
                "Could not find trending repos on page. "
                "GitHub may have changed its HTML structure."
            )

        repos: list[TrendingRepo] = []
        for rank, article in enumerate(articles, start=1):
            repo = self._parse_repo_article(article, rank)
            if repo:
                repos.append(repo)
        return repos

    def _parse_repo_article(self, article: Any, rank: int) -> TrendingRepo | None:
        """Extract a TrendingRepo from a single article element."""
        try:
            # Repo path like /owner/name
            h2_link = article.select_one("h2 a")
            if not h2_link:
                return None
            href = h2_link.get("href", "").strip().lstrip("/")
            parts = href.split("/")
            if len(parts) < 2:
                return None
            owner, name = parts[0], parts[1]
            full_name = f"{owner}/{name}"

            # Description
            desc_el = article.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # Programming language
            lang_el = article.select_one('[itemprop="programmingLanguage"]')
            language = lang_el.get_text(strip=True) if lang_el else None

            # Stars
            stars_el = article.select_one('a[href*="/stargazers"]')
            stars = _parse_int(stars_el.get_text(strip=True)) if stars_el else 0

            # Forks
            forks_el = article.select_one('a[href*="/forks"]')
            forks = _parse_int(forks_el.get_text(strip=True)) if forks_el else 0

            # Stars today
            today_el = article.select_one(".float-sm-right")
            stars_today = _parse_int(today_el.get_text(strip=True)) if today_el else 0

            # Contributors (built by)
            contributors = [
                img.get("alt", "").lstrip("@")
                for img in article.select(".Link--muted img[alt]")
            ]

            return TrendingRepo(
                rank=rank,
                owner=owner,
                name=name,
                full_name=full_name,
                description=description,
                language=language,
                stars=stars,
                forks=forks,
                stars_today=stars_today,
                url=f"{BASE_URL}/{full_name}",
                contributors=contributors,
            )
        except Exception as exc:
            raise ParseError(f"Failed to parse repo article: {exc}") from exc

    # --------------------------------------------------------------- developers

    def get_trending_developers(
        self,
        language: str = "",
        since: str = "daily",
    ) -> list[TrendingDeveloper]:
        """Fetch trending developers."""
        params: dict[str, str] = {}
        if language:
            params["language"] = language
        if since and since != "daily":
            params["since"] = since

        html = self._get(f"{TRENDING_URL}/developers", params)
        return self._parse_developers(html)

    def _parse_developers(self, html: str) -> list[TrendingDeveloper]:
        """Parse `article.Box-row` elements from trending developers HTML."""
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("article.Box-row")

        if not articles:
            no_results = soup.select_one(".blankslate")
            if no_results:
                return []
            raise ParseError(
                "Could not find trending developers on page. "
                "GitHub may have changed its HTML structure."
            )

        developers: list[TrendingDeveloper] = []
        for rank, article in enumerate(articles, start=1):
            dev = self._parse_developer_article(article, rank)
            if dev:
                developers.append(dev)
        return developers

    def _parse_developer_article(self, article: Any, rank: int) -> TrendingDeveloper | None:
        """Extract a TrendingDeveloper from a single article element."""
        try:
            # Avatar
            avatar_el = article.select_one("img.rounded, img.avatar-user")
            avatar_url = avatar_el.get("src", "") if avatar_el else ""

            # Profile link — first link with /username href in h1
            h1_link = article.select_one("h1 a")
            if not h1_link:
                return None
            login = h1_link.get("href", "").strip().lstrip("/")
            name = h1_link.get_text(strip=True)

            # Username (from p.f4 link)
            username_el = article.select_one("p.f4 a")
            if username_el:
                login = username_el.get_text(strip=True)

            # Popular repo
            pop_repo_link = None
            pop_repo_desc = None
            # The popular repo is inside a nested article element
            nested_article = article.select_one("article")
            if nested_article:
                repo_link = nested_article.select_one("a[href]")
                if repo_link:
                    pop_repo_path = repo_link.get("href", "").strip().lstrip("/")
                    pop_repo_link = pop_repo_path if "/" in pop_repo_path else None
                desc_el = nested_article.select_one("p")
                pop_repo_desc = desc_el.get_text(strip=True) if desc_el else None

            return TrendingDeveloper(
                rank=rank,
                login=login,
                name=name if name != login else None,
                avatar_url=avatar_url,
                profile_url=f"{BASE_URL}/{login}",
                popular_repo=pop_repo_link,
                popular_repo_desc=pop_repo_desc,
            )
        except Exception as exc:
            raise ParseError(f"Failed to parse developer article: {exc}") from exc
