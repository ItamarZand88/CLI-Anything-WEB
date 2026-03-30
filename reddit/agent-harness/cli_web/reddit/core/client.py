"""HTTP client for Reddit's public and authenticated OAuth APIs.

Uses curl_cffi with Chrome TLS impersonation to bypass bot detection.
Authenticated calls use oauth.reddit.com with Bearer token.
"""

from __future__ import annotations

from curl_cffi import requests as curl_requests

from .auth import get_bearer_token, get_cookies, load_auth
from .exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    RedditError,
    ServerError,
)

BASE_URL = "https://www.reddit.com"
OAUTH_URL = "https://oauth.reddit.com"


class RedditClient:
    """Client for Reddit's public JSON API and authenticated OAuth API."""

    def __init__(self) -> None:
        self._session = curl_requests.Session(
            impersonate="chrome",
            timeout=30,
        )
        # Warm up session — Reddit requires initial request to set cookies/tokens
        # before JSON API calls succeed. A quick GET to the homepage primes the session.
        try:
            self._session.get(f"{BASE_URL}/", timeout=10)
        except Exception:
            pass

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> RedditClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ── HTTP helpers ────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        url = f"{BASE_URL}{path}"
        try:
            resp = self._session.get(url, params=params)
        except Exception as exc:
            raise NetworkError(f"Request failed: {exc}") from exc
        return self._handle_response(resp, path)

    def _handle_response(self, resp, path: str = "") -> dict | list:
        if resp.status_code == 401:
            raise AuthError("Authentication required. Run: cli-web-reddit auth login", recoverable=True)
        if resp.status_code == 403:
            raise AuthError("Access denied. Token may have expired. Run: cli-web-reddit auth login", recoverable=True)
        if resp.status_code == 404:
            raise NotFoundError(f"Not found: {path}")
        if resp.status_code == 429:
            retry = resp.headers.get("retry-after")
            raise RateLimitError(
                "Rate limited by Reddit",
                retry_after=float(retry) if retry else None,
            )
        if resp.status_code >= 500:
            raise ServerError(
                f"Server error {resp.status_code}", status_code=resp.status_code
            )
        if resp.status_code >= 400:
            raise RedditError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def _get_listing(
        self, path: str, limit: int = 25, after: str | None = None,
        extra_params: dict | None = None,
    ) -> dict:
        """Fetch a Reddit Listing and return raw response."""
        params: dict = {"limit": limit}
        if after:
            params["after"] = after
        if extra_params:
            params.update(extra_params)
        return self._get(path, params=params)

    # ── OAuth helpers (authenticated) ────────────────────────────

    def _oauth_headers(self) -> dict:
        """Get OAuth bearer headers. Raises AuthError if not logged in."""
        token = get_bearer_token()
        if not token:
            raise AuthError("Not logged in. Run: cli-web-reddit auth login")
        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": "cli-web-reddit/0.2.0",
        }

    def _oauth_get(self, path: str, params: dict | None = None) -> dict | list:
        """Authenticated GET to oauth.reddit.com. Retries once on recoverable AuthError."""
        return self._oauth_request("GET", path, params=params)

    def _oauth_request(self, method: str, path: str, params: dict | None = None,
                       data: dict | None = None) -> dict | list:
        """Execute an authenticated request with single retry on recoverable AuthError."""
        url = f"{OAUTH_URL}{path}"
        for attempt in range(2):
            try:
                if method == "GET":
                    resp = self._session.get(url, headers=self._oauth_headers(), params=params)
                else:
                    resp = self._session.post(url, headers=self._oauth_headers(), data=data)
            except AuthError:
                raise
            except Exception as exc:
                raise NetworkError(f"Request failed: {exc}") from exc
            try:
                return self._handle_response(resp, path)
            except AuthError as exc:
                if attempt == 0 and exc.recoverable:
                    continue  # retry once
                raise

    def _oauth_get_listing(
        self, path: str, limit: int = 25, after: str | None = None,
        extra_params: dict | None = None,
    ) -> dict:
        params: dict = {"limit": limit}
        if after:
            params["after"] = after
        if extra_params:
            params.update(extra_params)
        return self._oauth_get(path, params=params)

    def _oauth_post(self, path: str, data: dict | None = None) -> dict:
        """Authenticated POST to oauth.reddit.com. Retries once on recoverable AuthError."""
        return self._oauth_request("POST", path, data=data)

    # ── Feed ──────────────────────────────────────────────────

    def feed_hot(self, limit: int = 25, after: str | None = None) -> dict:
        return self._get_listing("/hot/.json", limit=limit, after=after)

    def feed_new(self, limit: int = 25, after: str | None = None) -> dict:
        return self._get_listing("/new/.json", limit=limit, after=after)

    def feed_top(
        self, limit: int = 25, after: str | None = None, time: str = "day"
    ) -> dict:
        return self._get_listing(
            "/top/.json", limit=limit, after=after, extra_params={"t": time}
        )

    def feed_rising(self, limit: int = 25, after: str | None = None) -> dict:
        return self._get_listing("/rising/.json", limit=limit, after=after)

    def feed_popular(self, limit: int = 25, after: str | None = None) -> dict:
        return self._get_listing("/r/popular/.json", limit=limit, after=after)

    # ── Subreddit ──────────────────────────────────────────────

    def sub_posts(
        self, name: str, sort: str = "hot", limit: int = 25,
        after: str | None = None, time: str | None = None,
    ) -> dict:
        path = f"/r/{name}/{sort}/.json"
        extra = {}
        if time and sort in ("top", "controversial"):
            extra["t"] = time
        return self._get_listing(path, limit=limit, after=after, extra_params=extra or None)

    def sub_info(self, name: str) -> dict:
        return self._get(f"/r/{name}/about.json")

    def sub_rules(self, name: str) -> dict:
        return self._get(f"/r/{name}/about/rules.json")

    def sub_search(
        self, name: str, query: str, limit: int = 25,
        sort: str = "relevance", after: str | None = None,
    ) -> dict:
        return self._get_listing(
            f"/r/{name}/search.json", limit=limit, after=after,
            extra_params={"q": query, "restrict_sr": "on", "sort": sort},
        )

    def sub_join(self, name: str) -> dict:
        """Subscribe to a subreddit (requires auth)."""
        return self._oauth_post("/api/subscribe", data={"sr_name": name, "action": "sub"})

    def sub_leave(self, name: str) -> dict:
        """Unsubscribe from a subreddit (requires auth)."""
        return self._oauth_post("/api/subscribe", data={"sr_name": name, "action": "unsub"})

    # ── Search ──────────────────────────────────────────────────

    def search_posts(
        self, query: str, limit: int = 25, sort: str = "relevance",
        time: str | None = None, after: str | None = None,
    ) -> dict:
        extra: dict = {"q": query, "sort": sort}
        if time:
            extra["t"] = time
        return self._get_listing("/search.json", limit=limit, after=after, extra_params=extra)

    def search_subreddits(
        self, query: str, limit: int = 25, after: str | None = None,
    ) -> dict:
        return self._get_listing(
            "/subreddits/search.json", limit=limit, after=after,
            extra_params={"q": query},
        )

    # ── User ──────────────────────────────────────────────────

    def user_about(self, username: str) -> dict:
        return self._get(f"/user/{username}/about.json")

    def user_posts(
        self, username: str, limit: int = 25, after: str | None = None,
        sort: str = "new", time: str | None = None,
    ) -> dict:
        extra: dict = {"sort": sort}
        if time:
            extra["t"] = time
        return self._get_listing(
            f"/user/{username}/submitted.json", limit=limit, after=after,
            extra_params=extra,
        )

    def user_comments(
        self, username: str, limit: int = 25, after: str | None = None,
        sort: str = "new", time: str | None = None,
    ) -> dict:
        extra: dict = {"sort": sort}
        if time:
            extra["t"] = time
        return self._get_listing(
            f"/user/{username}/comments.json", limit=limit, after=after,
            extra_params=extra,
        )

    # ── Post detail ──────────────────────────────────────────────

    def post_detail(self, subreddit: str, post_id: str, slug: str = "",
                    comment_limit: int = 50, depth: int | None = None) -> list:
        """Get post + comments. Returns [post_listing, comments_listing].

        If subreddit is empty, uses /comments/{id}.json which works without
        knowing the subreddit (Reddit redirects internally).
        """
        if subreddit:
            path = f"/r/{subreddit}/comments/{post_id}/{slug}.json"
        else:
            path = f"/comments/{post_id}.json"
        params: dict = {"limit": comment_limit}
        if depth is not None:
            params["depth"] = depth
        return self._get(path, params=params)

    def more_children(self, link_id: str, children_ids: list[str]) -> list[dict]:
        """Fetch collapsed/hidden comment children via /api/morechildren.json.

        Reddit returns 'more' objects when comments are too deeply nested.
        This fetches the actual comment data for those IDs.
        """
        if not children_ids:
            return []
        path = "/api/morechildren.json"
        params = {
            "api_type": "json",
            "link_id": link_id if link_id.startswith("t3_") else f"t3_{link_id}",
            "children": ",".join(children_ids[:100]),  # Reddit limit: 100 per call
        }
        resp = self._get(path, params=params)
        # Response: {"json": {"data": {"things": [{"kind": "t1", "data": {...}}, ...]}}}
        if isinstance(resp, dict):
            return resp.get("json", {}).get("data", {}).get("things", [])
        return []

    def comment_thread(self, post_id: str, comment_id: str,
                       context: int = 0, depth: int = 20) -> list:
        """Fetch a specific comment thread via permalink .json.

        Used to expand 'continue this thread' links (more objects with empty IDs).
        Returns [post_listing, comment_listing] like post_detail.
        """
        path = f"/comments/{post_id}/_/{comment_id}.json"
        return self._get(path, params={"context": context, "depth": depth})

    # ── Authenticated: Me ────────────────────────────────────────

    def me(self) -> dict:
        """Get current user's profile (requires auth)."""
        return self._oauth_get("/api/v1/me")

    def me_saved(self, limit: int = 25, after: str | None = None) -> dict:
        """Get current user's saved items (requires auth)."""
        me = self.me()
        return self._oauth_get_listing(f"/user/{me['name']}/saved", limit=limit, after=after)

    def me_upvoted(self, limit: int = 25, after: str | None = None) -> dict:
        """Get current user's upvoted items (requires auth)."""
        me = self.me()
        return self._oauth_get_listing(f"/user/{me['name']}/upvoted", limit=limit, after=after)

    def me_subscriptions(self, limit: int = 100, after: str | None = None) -> dict:
        """Get user's subscribed subreddits (requires auth)."""
        return self._oauth_get_listing("/subreddits/mine/subscriber", limit=limit, after=after)

    def me_inbox(self, limit: int = 25, after: str | None = None) -> dict:
        """Get inbox messages (requires auth)."""
        return self._oauth_get_listing("/message/inbox", limit=limit, after=after)

    # ── Authenticated: Vote ──────────────────────────────────────

    def vote(self, thing_id: str, direction: int) -> dict:
        """Vote on a post or comment. direction: 1=up, -1=down, 0=unvote."""
        return self._oauth_post("/api/vote", data={"id": thing_id, "dir": direction})

    # ── Authenticated: Save ──────────────────────────────────────

    def save(self, thing_id: str) -> dict:
        """Save a post or comment (requires auth)."""
        return self._oauth_post("/api/save", data={"id": thing_id})

    def unsave(self, thing_id: str) -> dict:
        """Unsave a post or comment (requires auth)."""
        return self._oauth_post("/api/unsave", data={"id": thing_id})

    # ── Authenticated: Submit ────────────────────────────────────

    def get_subreddit_flairs(self, subreddit: str) -> list[dict]:
        """Get available link flairs for a subreddit (requires auth)."""
        result = self._oauth_get(f"/r/{subreddit}/api/link_flair_v2")
        if not isinstance(result, list):
            return []
        return [
            {"id": f.get("id", ""), "text": f.get("text", "")}
            for f in result if f.get("id")
        ]

    def submit_text(self, subreddit: str, title: str, text: str,
                    flair_id: str | None = None) -> dict:
        """Submit a text post (requires auth)."""
        data = {
            "sr": subreddit, "kind": "self",
            "title": title, "text": text,
            "api_type": "json",
        }
        if flair_id:
            data["flair_id"] = flair_id
        return self._oauth_post("/api/submit", data=data)

    def submit_link(self, subreddit: str, title: str, url: str,
                    flair_id: str | None = None) -> dict:
        """Submit a link post (requires auth)."""
        data = {
            "sr": subreddit, "kind": "link",
            "title": title, "url": url,
            "api_type": "json",
        }
        if flair_id:
            data["flair_id"] = flair_id
        return self._oauth_post("/api/submit", data=data)

    # ── Authenticated: Comment ───────────────────────────────────

    def comment(self, thing_id: str, text: str) -> dict:
        """Add a comment to a post or reply to a comment (requires auth)."""
        return self._oauth_post("/api/comment", data={
            "thing_id": thing_id, "text": text, "api_type": "json",
        })

    def edit(self, thing_id: str, text: str) -> dict:
        """Edit own post or comment text (requires auth)."""
        return self._oauth_post("/api/editusertext", data={
            "thing_id": thing_id, "text": text, "api_type": "json",
        })

    def delete(self, thing_id: str) -> dict:
        """Delete own post or comment (requires auth)."""
        return self._oauth_post("/api/del", data={"id": thing_id})

