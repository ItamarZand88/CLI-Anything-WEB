"""HTTP client for Hacker News — Firebase API + Algolia search + authenticated actions."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from .exceptions import AuthError, NetworkError, NotFoundError, RateLimitError, ServerError
from .models import Comment, SearchResult, Story, User

FIREBASE_BASE = "https://hacker-news.firebaseio.com/v0"
ALGOLIA_BASE = "https://hn.algolia.com/api/v1"
HN_BASE = "https://news.ycombinator.com"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

WEB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Feed name → Firebase endpoint
FEED_ENDPOINTS = {
    "top": "topstories",
    "new": "newstories",
    "best": "beststories",
    "ask": "askstories",
    "show": "showstories",
    "job": "jobstories",
}


class HackerNewsClient:
    """HTTP client wrapping HN Firebase API and Algolia search."""

    def __init__(self, timeout: float = 30.0, user_cookie: str | None = None):
        self._timeout = timeout
        self._user_cookie = user_cookie
        self._client = httpx.Client(
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
            timeout=timeout,
        )
        self._web_client = httpx.Client(
            headers=WEB_HEADERS,
            follow_redirects=True,
            timeout=timeout,
        )

    def close(self):
        """Close underlying HTTP clients."""
        self._client.close()
        self._web_client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """Fetch a URL and return parsed JSON."""
        try:
            response = self._client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {url}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error: {exc}") from exc

        if response.status_code == 404:
            raise NotFoundError(url)
        if response.status_code == 429:
            retry_after = int(response.headers.get("retry-after", "60"))
            raise RateLimitError(retry_after)
        if response.status_code >= 500:
            raise ServerError(response.status_code)
        if response.status_code != 200:
            raise NetworkError(f"Unexpected status {response.status_code}: {url}")

        return response.json()

    # ------------------------------------------------------------------ feeds

    def get_story_ids(self, feed: str = "top") -> list[int]:
        """Get story IDs for a feed (top, new, best, ask, show, job)."""
        endpoint = FEED_ENDPOINTS.get(feed, "topstories")
        return self._get_json(f"{FIREBASE_BASE}/{endpoint}.json")

    def get_stories(self, feed: str = "top", limit: int = 30) -> list[Story]:
        """Get full story objects for a feed."""
        ids = self.get_story_ids(feed)[:limit]
        return self._fetch_items_parallel(ids, Story)

    # ------------------------------------------------------------------ items

    def get_item(self, item_id: int) -> dict:
        """Get a single item (story, comment, job, poll) by ID."""
        data = self._get_json(f"{FIREBASE_BASE}/item/{item_id}.json")
        if data is None:
            raise NotFoundError(f"Item {item_id}")
        return data

    def get_story(self, story_id: int) -> Story:
        """Get a story by ID."""
        data = self.get_item(story_id)
        return Story(
            id=data.get("id", story_id),
            title=data.get("title", ""),
            url=data.get("url"),
            score=data.get("score", 0),
            by=data.get("by", ""),
            time=data.get("time", 0),
            descendants=data.get("descendants", 0),
            type=data.get("type", "story"),
        )

    def get_comments(self, story_id: int, limit: int = 30) -> list[Comment]:
        """Get top-level comments for a story."""
        data = self.get_item(story_id)
        kid_ids = data.get("kids", [])[:limit]
        if not kid_ids:
            return []
        return self._fetch_items_parallel(kid_ids, Comment)

    # ------------------------------------------------------------------ users

    def get_user(self, username: str) -> User:
        """Get a user profile."""
        data = self._get_json(f"{FIREBASE_BASE}/user/{username}.json")
        if data is None:
            raise NotFoundError(f"User '{username}'")
        return User(
            id=data.get("id", username),
            karma=data.get("karma", 0),
            created=data.get("created", 0),
            about=data.get("about", ""),
            submitted=data.get("submitted", []),
        )

    # ------------------------------------------------------------------ search

    def search(
        self,
        query: str,
        tags: str = "story",
        sort_by_date: bool = False,
        hits_per_page: int = 20,
        page: int = 0,
    ) -> list[SearchResult]:
        """Search HN via Algolia API."""
        endpoint = "search_by_date" if sort_by_date else "search"
        params: dict[str, Any] = {
            "query": query,
            "hitsPerPage": hits_per_page,
            "page": page,
        }
        if tags:
            params["tags"] = tags

        data = self._get_json(f"{ALGOLIA_BASE}/{endpoint}", params=params)
        results = []
        for hit in data.get("hits", []):
            results.append(SearchResult(
                objectID=hit.get("objectID", ""),
                title=hit.get("title", ""),
                url=hit.get("url"),
                author=hit.get("author", ""),
                points=hit.get("points"),
                num_comments=hit.get("num_comments"),
                created_at=hit.get("created_at", ""),
                story_id=int(hit.get("objectID", "0")) if hit.get("objectID", "").isdigit() else None,
            ))
        return results

    # -------------------------------------------------------- authenticated web requests

    def _require_auth(self) -> str:
        """Return user cookie or raise AuthError."""
        if not self._user_cookie:
            raise AuthError()
        return self._user_cookie

    def _get_html(
        self, url: str, params: dict[str, str] | None = None,
    ) -> str:
        """Fetch a URL with auth cookie and return HTML body."""
        cookie = self._require_auth()
        try:
            response = self._web_client.get(url, params=params, cookies={"user": cookie})
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {url}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error: {exc}") from exc

        if response.status_code in (401, 403):
            raise AuthError("Auth cookie expired. Run: cli-web-hackernews auth login", recoverable=False)
        if response.status_code >= 500:
            raise ServerError(response.status_code)
        if response.status_code != 200:
            raise NetworkError(f"Unexpected status {response.status_code}: {url}")

        return response.text

    def _post_form(
        self, url: str, data: dict[str, str],
    ) -> str:
        """POST form data with auth cookie, return response text."""
        cookie = self._require_auth()
        try:
            response = self._web_client.post(
                url, data=data, cookies={"user": cookie},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {url}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error: {exc}") from exc

        if response.status_code in (401, 403):
            raise AuthError("Auth cookie expired. Run: cli-web-hackernews auth login", recoverable=False)
        if response.status_code >= 500:
            raise ServerError(response.status_code)

        return response.text

    def _extract_auth_token(self, html: str, item_id: int) -> str:
        """Extract the auth token for an item from HN page HTML.

        HN embeds auth tokens in links like: vote?id=X&how=up&auth=HEXTOKEN
        """
        pattern = rf'auth=([a-f0-9]+).*?(?:id={item_id}|{item_id})'
        match = re.search(pattern, html)
        if match:
            return match.group(1)
        # Try reverse order (auth after id)
        pattern2 = rf'id={item_id}[^"]*auth=([a-f0-9]+)'
        match2 = re.search(pattern2, html)
        if match2:
            return match2.group(1)
        raise AuthError("Could not extract auth token — page format may have changed")

    # ------------------------------------------------------------------ upvote

    def upvote(self, item_id: int) -> dict:
        """Upvote a story or comment. Returns success status."""
        # First, load the item page to get the auth token
        html = self._get_html(f"{HN_BASE}/item?id={item_id}")
        auth_token = self._extract_auth_token(html, item_id)

        # Execute the upvote via GET
        result_html = self._get_html(
            f"{HN_BASE}/vote",
            params={"id": str(item_id), "how": "up", "auth": auth_token},
        )

        return {"success": True, "item_id": item_id, "action": "upvoted"}

    # ------------------------------------------------------------------ submit

    def submit_story(self, title: str, url: str | None = None, text: str | None = None) -> dict:
        """Submit a new story to HN. Returns submission result."""
        # Get the submit page to extract fnid
        html = self._get_html(f"{HN_BASE}/submit")
        fnid_match = re.search(r'name="fnid"\s+value="([^"]+)"', html)
        if not fnid_match:
            raise AuthError("Could not get submission token — login may have expired")

        form_data: dict[str, str] = {
            "fnid": fnid_match.group(1),
            "fnop": "submit-page",
            "title": title,
            "url": url or "",
            "text": text or "",
        }

        result_html = self._post_form(f"{HN_BASE}/r", form_data)

        # Check for errors in result
        if "unknown or expired link" in result_html.lower():
            raise AuthError("Submission token expired — please try again")
        if "please slow down" in result_html.lower():
            raise RateLimitError(retry_after=120)

        return {"success": True, "title": title, "type": "url" if url else "ask"}

    # ------------------------------------------------------------------ comment

    def post_comment(self, parent_id: int, text: str) -> dict:
        """Post a comment on a story or reply to another comment."""
        # Get the item page to extract hmac
        html = self._get_html(f"{HN_BASE}/item?id={parent_id}")
        hmac_match = re.search(r'name="hmac"\s+value="([^"]+)"', html)
        if not hmac_match:
            raise AuthError("Could not get comment token — login may have expired")

        form_data = {
            "parent": str(parent_id),
            "goto": f"item?id={parent_id}",
            "hmac": hmac_match.group(1),
            "text": text,
        }

        result_html = self._post_form(f"{HN_BASE}/comment", form_data)

        if "unknown or expired link" in result_html.lower():
            raise AuthError("Comment token expired — please try again")

        return {"success": True, "parent_id": parent_id}

    # ------------------------------------------------------------------ favorite

    def favorite(self, item_id: int) -> dict:
        """Favorite (save) a story."""
        html = self._get_html(f"{HN_BASE}/item?id={item_id}")
        auth_token = self._extract_auth_token(html, item_id)

        self._get_html(
            f"{HN_BASE}/fave",
            params={"id": str(item_id), "auth": auth_token},
        )

        return {"success": True, "item_id": item_id, "action": "favorited"}

    # ------------------------------------------------------------------ hide

    def hide(self, item_id: int) -> dict:
        """Hide a story from the feed."""
        html = self._get_html(f"{HN_BASE}/item?id={item_id}")
        auth_token = self._extract_auth_token(html, item_id)

        self._get_html(
            f"{HN_BASE}/hide",
            params={"id": str(item_id), "auth": auth_token},
        )

        return {"success": True, "item_id": item_id, "action": "hidden"}

    # ------------------------------------------------------------ favorites page

    def get_favorites(self, username: str, limit: int = 30) -> list[Story]:
        """Get a user's favorite stories by scraping the favorites page."""
        html = self._get_html(f"{HN_BASE}/favorites", params={"id": username})
        return self._parse_stories_from_html(html, limit)

    # ----------------------------------------------------------- submissions page

    def get_submissions(self, username: str, limit: int = 30) -> list[Story]:
        """Get a user's submitted stories by scraping the submitted page."""
        html = self._get_html(f"{HN_BASE}/submitted", params={"id": username})
        return self._parse_stories_from_html(html, limit)

    def _parse_stories_from_html(self, html: str, limit: int = 30) -> list[Story]:
        """Parse story items from HN HTML pages (favorites, submitted, etc.)."""
        stories: list[Story] = []
        # Find all story IDs from the HTML
        id_matches = re.findall(r'class="athing[^"]*"\s+id="(\d+)"', html)
        if not id_matches:
            return []
        item_ids = [int(m) for m in id_matches[:limit]]
        return self._fetch_items_parallel(item_ids, Story)

    # --------------------------------------------------------------- threads page

    def get_threads(self, username: str, limit: int = 20) -> list[Comment]:
        """Get comment replies to a user (threads page) by scraping HTML."""
        html = self._get_html(f"{HN_BASE}/threads", params={"id": username})
        return self._parse_comments_from_html(html, limit)

    def _parse_comments_from_html(self, html: str, limit: int = 20) -> list[Comment]:
        """Parse comment items from HN threads HTML page."""
        id_matches = re.findall(r'class="athing[^"]*"\s+id="(\d+)"', html)
        if not id_matches:
            return []
        item_ids = [int(m) for m in id_matches[:limit]]
        return self._fetch_items_parallel(item_ids, Comment)

    # -------------------------------------------------------------- parallel fetch

    def _fetch_items_parallel(self, ids: list[int], model_cls: type) -> list:
        """Fetch multiple items in parallel using asyncio + httpx."""
        async def _fetch_all():
            async with httpx.AsyncClient(
                headers=DEFAULT_HEADERS,
                follow_redirects=True,
                timeout=self._timeout,
            ) as client:
                tasks = [
                    client.get(f"{FIREBASE_BASE}/item/{item_id}.json")
                    for item_id in ids
                ]
                responses = await asyncio.gather(*tasks, return_exceptions=True)

            items = []
            for resp in responses:
                if isinstance(resp, Exception):
                    continue
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if data is None or data.get("deleted"):
                    continue
                try:
                    if model_cls == Story:
                        items.append(Story(
                            id=data.get("id", 0),
                            title=data.get("title", ""),
                            url=data.get("url"),
                            score=data.get("score", 0),
                            by=data.get("by", ""),
                            time=data.get("time", 0),
                            descendants=data.get("descendants", 0),
                            type=data.get("type", "story"),
                        ))
                    elif model_cls == Comment:
                        items.append(Comment(
                            id=data.get("id", 0),
                            by=data.get("by", ""),
                            text=data.get("text", ""),
                            time=data.get("time", 0),
                            parent=data.get("parent", 0),
                            kids=data.get("kids", []),
                            dead=data.get("dead", False),
                            deleted=data.get("deleted", False),
                            type=data.get("type", "comment"),
                        ))
                except (KeyError, TypeError):
                    continue
            return items

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already in async context — run synchronously as fallback
            items = []
            for item_id in ids:
                try:
                    data = self.get_item(item_id)
                    if data.get("deleted"):
                        continue
                    if model_cls == Story:
                        items.append(Story(
                            id=data.get("id", 0),
                            title=data.get("title", ""),
                            url=data.get("url"),
                            score=data.get("score", 0),
                            by=data.get("by", ""),
                            time=data.get("time", 0),
                            descendants=data.get("descendants", 0),
                            type=data.get("type", "story"),
                        ))
                    elif model_cls == Comment:
                        items.append(Comment(
                            id=data.get("id", 0),
                            by=data.get("by", ""),
                            text=data.get("text", ""),
                            time=data.get("time", 0),
                            parent=data.get("parent", 0),
                            kids=data.get("kids", []),
                            dead=data.get("dead", False),
                            deleted=data.get("deleted", False),
                            type=data.get("type", "comment"),
                        ))
                except Exception:
                    continue
            return items
        else:
            return asyncio.run(_fetch_all())
