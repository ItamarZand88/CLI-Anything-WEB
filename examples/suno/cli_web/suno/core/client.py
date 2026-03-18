"""HTTP client for Suno Studio API.

Thin wrapper around httpx with centralized auth header injection,
automatic JSON parsing, error handling, and rate limit respect.
"""

import time
from typing import Any, Optional

import click
import httpx

from cli_web.suno.core.auth import get_auth_headers, refresh_jwt_from_cookies, load_auth, save_auth

STUDIO_API = "https://studio-api.prod.suno.com"
DEFAULT_TIMEOUT = 30


class SunoClientError(Exception):
    """Base error for Suno API client."""

    def __init__(self, message: str, status_code: int = 0, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SunoAuthError(SunoClientError):
    """Authentication error (401/403)."""
    pass


class SunoRateLimitError(SunoClientError):
    """Rate limit hit (429)."""

    def __init__(self, retry_after: float = 5.0):
        super().__init__(f"Rate limited. Retry after {retry_after}s", status_code=429)
        self.retry_after = retry_after


class SunoClient:
    """HTTP client for Suno Studio API."""

    def __init__(self, base_url: str = STUDIO_API, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
        retry_on_401: bool = True,
    ) -> Any:
        """Make an authenticated request to the Suno API."""
        url = f"{self.base_url}{path}"
        try:
            headers = get_auth_headers()
        except RuntimeError as e:
            raise click.ClickException(str(e))

        resp = self.client.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_body,
        )

        if resp.status_code == 401 and retry_on_401:
            # Try refreshing token
            auth_data = load_auth()
            if auth_data:
                jwt = refresh_jwt_from_cookies(auth_data.get("cookies", []))
                if jwt:
                    auth_data["jwt"] = jwt
                    auth_data["jwt_refreshed_at"] = time.time()
                    save_auth(auth_data)
                    return self._request(method, path, params, json_body, retry_on_401=False)
            raise SunoAuthError(
                "Authentication failed. Run: cli-web-suno auth login --from-browser",
                status_code=401,
            )

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("retry-after", "5"))
            raise SunoRateLimitError(retry_after)

        if resp.status_code >= 400:
            body = None
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise SunoClientError(
                f"API error {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
                response_body=body,
            )

        if resp.status_code == 204:
            return {}

        return resp.json()

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json_body: Optional[dict] = None, params: Optional[dict] = None) -> Any:
        return self._request("POST", path, params=params, json_body=json_body)

    def put(self, path: str, json_body: Optional[dict] = None) -> Any:
        return self._request("PUT", path, json_body=json_body)

    def delete(self, path: str, params: Optional[dict] = None) -> Any:
        return self._request("DELETE", path, params=params)

    # ─── Convenience methods ──────────────────────────────────────────

    def get_session(self) -> dict:
        """Get full session info (user, models, roles, flags)."""
        return self.get("/api/session/")

    def get_billing_info(self) -> dict:
        """Get billing/credits info."""
        return self.get("/api/billing/info/")

    def get_feed(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
        workspace_id: str = "default",
        trashed: bool = False,
    ) -> dict:
        """Get user's song feed."""
        filters = {
            "disliked": "False",
            "trashed": str(trashed),
            "fromStudioProject": {"presence": "False"},
            "stem": {"presence": "False"},
            "workspace": {"presence": "True", "workspaceId": workspace_id},
        }
        return self.post("/api/feed/v3", json_body={
            "cursor": cursor,
            "limit": limit,
            "filters": filters,
        })

    def generate_song(
        self,
        prompt: str = "",
        tags: str = "",
        title: str = "",
        gpt_description_prompt: str = "",
        make_instrumental: bool = False,
        model: str = "",
        negative_tags: str = "",
        project_id: str = "default",
    ) -> dict:
        """Generate a new song."""
        body = {
            "prompt": prompt,
            "tags": tags,
            "title": title,
            "gpt_description_prompt": gpt_description_prompt,
            "make_instrumental": make_instrumental,
            "negative_tags": negative_tags,
        }
        if model:
            body["model"] = model
        # Filter out empty string values
        body = {k: v for k, v in body.items() if v != "" or k in ("prompt", "make_instrumental")}

        return self.post("/api/generate/v2-web/", json_body=body)

    def get_concurrent_status(self) -> dict:
        """Check generation queue status."""
        return self.get("/api/generate/concurrent-status")

    def list_projects(self, page: int = 1, sort: str = "max_created_at_last_updated_clip") -> dict:
        """List user's projects."""
        return self.get("/api/project/me", params={
            "page": page,
            "sort": sort,
            "show_trashed": "false",
            "exclude_shared": "false",
        })

    def get_project(self, project_id: str = "default") -> dict:
        """Get project with clips."""
        return self.get(f"/api/project/{project_id}")

    def list_prompts(self, prompt_type: Optional[str] = None, page: int = 0, per_page: int = 100) -> dict:
        """List saved prompts."""
        params = {"page": page, "per_page": per_page}
        if prompt_type:
            params["filter_prompt_type"] = prompt_type
        return self.get("/api/prompts/", params=params)

    def get_prompt_suggestions(self) -> dict:
        """Get prompt suggestions."""
        return self.get("/api/prompts/suggestions")

    def recommend_tags(self, tags: Optional[list] = None) -> dict:
        """Get recommended tags."""
        return self.post("/api/tags/recommend", json_body={"tags": tags or []})

    def get_homepage(self, cursor: Optional[str] = None) -> dict:
        """Get homepage feed."""
        return self.post("/api/unified/homepage", json_body={"cursor": cursor})

    def get_notifications(self) -> dict:
        """Get notifications."""
        return self.get("/api/notification/v2")

    def get_notification_count(self) -> dict:
        """Get unread notification count."""
        return self.get("/api/notification/v2/badge-count")

    def get_playlist(self, playlist_id: str, page: int = 0) -> dict:
        """Get playlist by ID."""
        return self.get(f"/api/playlist/{playlist_id}", params={"page": page})
