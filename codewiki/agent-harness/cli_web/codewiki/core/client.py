"""HTTP client for Code Wiki batchexecute API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from .exceptions import (
    AuthError,
    AppError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from .models import ChatResponse, Repository, WikiPage, WikiSection
from .rpc.decoder import decode_response
from .rpc.encoder import build_url, encode_request
from .rpc.types import DEFAULT_HEADERS, RPCMethod


class CodeWikiClient:
    """Client for Google Code Wiki batchexecute API."""

    def __init__(self) -> None:
        self._http = httpx.Client(
            headers=DEFAULT_HEADERS,
            timeout=30.0,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> CodeWikiClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _call(self, rpc_id: str, params: list) -> Any:
        """Make a batchexecute RPC call."""
        url = build_url(rpc_id)
        body = encode_request(rpc_id, params)

        try:
            resp = self._http.post(
                url,
                content=body.encode("utf-8"),
            )
        except httpx.ConnectError as exc:
            raise NetworkError(f"Connection failed: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}") from exc

        if resp.status_code in (401, 403):
            raise AuthError("Authentication required", recoverable=False)
        if resp.status_code == 404:
            raise NotFoundError("Resource not found")
        if resp.status_code == 429:
            retry = resp.headers.get("Retry-After")
            raise RateLimitError(
                "Rate limited by Code Wiki",
                retry_after=float(retry) if retry else None,
            )
        if resp.status_code >= 500:
            raise ServerError(
                f"Server error: {resp.status_code}", status_code=resp.status_code
            )
        if resp.status_code >= 400:
            raise AppError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        return decode_response(resp.content, rpc_id)

    # ── Repos ───────────────────────────────────────────────

    def featured_repos(self) -> list[Repository]:
        """Get featured repositories from the homepage."""
        raw = self._call(RPCMethod.FEATURED_REPOS, [])
        if not raw:
            return []
        # Response is [[repo1, repo2, ...]] — unwrap outer array
        items = raw[0] if isinstance(raw[0], list) and raw[0] and isinstance(raw[0][0], list) else raw
        repos = []
        for item in items:
            if not isinstance(item, list) or len(item) < 6:
                continue
            slug = item[0] or ""
            meta = item[3] if len(item) > 3 and isinstance(item[3], list) else [None, ""]
            info = item[5] if len(item) > 5 and isinstance(item[5], list) else []
            repos.append(Repository(
                slug=slug,
                github_url=meta[1] if len(meta) > 1 else "",
                description=info[0] if len(info) > 0 else "",
                avatar_url=info[1] if len(info) > 1 else "",
                stars=info[2] if len(info) > 2 else 0,
            ))
        return repos

    def search_repos(
        self, query: str, limit: int = 25, offset: int = 0
    ) -> list[Repository]:
        """Search for repositories."""
        raw = self._call(RPCMethod.SEARCH_REPOS, [query, limit, query, offset])
        if not raw:
            return []
        # Response is [[repo1, repo2, ...]] — unwrap outer array
        items = raw[0] if isinstance(raw[0], list) and raw[0] and isinstance(raw[0][0], list) else raw
        repos = []
        for item in items:
            if not isinstance(item, list) or len(item) < 6:
                continue
            slug = item[0] or ""
            meta = item[3] if isinstance(item[3], list) else [None, ""]
            ts = item[4] if isinstance(item[4], list) else [None, None]
            info = item[5] if isinstance(item[5], list) else []
            updated = None
            if ts and ts[0]:
                try:
                    updated = datetime.fromtimestamp(ts[0])
                except (ValueError, OSError, TypeError):
                    pass
            repos.append(Repository(
                slug=slug,
                github_url=meta[1] if len(meta) > 1 else "",
                description=info[0] if len(info) > 0 else "",
                avatar_url=info[1] if len(info) > 1 else "",
                stars=info[2] if len(info) > 2 else 0,
                updated_at=updated,
            ))
        return repos

    # ── Wiki ────────────────────────────────────────────────

    def get_wiki(self, repo_slug: str) -> WikiPage:
        """Get the full wiki page for a repository."""
        github_url = f"https://github.com/{repo_slug}"
        raw = self._call(RPCMethod.WIKI_PAGE, [github_url])
        if not raw:
            raise NotFoundError(f"Wiki not found for {repo_slug}")

        top = raw[0] if isinstance(raw, list) and raw else []
        if not isinstance(top, list) or len(top) < 2:
            raise NotFoundError(f"Wiki not found for {repo_slug}")

        repo_info = top[0] if isinstance(top[0], list) else []
        sections_raw = top[1] if isinstance(top[1], list) else []
        ts = top[4] if len(top) > 4 and isinstance(top[4], list) else [None, None]

        commit_hash = repo_info[1] if len(repo_info) > 1 else ""
        updated = None
        if ts and ts[0]:
            try:
                updated = datetime.fromtimestamp(ts[0])
            except (ValueError, OSError, TypeError):
                pass

        meta = raw[1] if len(raw) > 1 and isinstance(raw[1], list) else []
        has_wiki = meta[1] if len(meta) > 1 else False

        sections = []
        for sec in sections_raw:
            if not isinstance(sec, list) or len(sec) < 2:
                continue
            code_refs = []
            if len(sec) > 3 and isinstance(sec[3], list):
                for ref in sec[3]:
                    if isinstance(ref, list) and ref:
                        code_refs.append(ref[0])
            sections.append(WikiSection(
                title=sec[0] or "",
                level=sec[1] if len(sec) > 1 else 1,
                description=sec[2] if len(sec) > 2 else "",
                code_refs=code_refs,
                content=sec[4] if len(sec) > 4 else "",
            ))

        repo = Repository(
            slug=repo_slug,
            github_url=github_url,
            commit_hash=commit_hash,
            updated_at=updated,
        )

        return WikiPage(repo=repo, sections=sections, has_wiki=has_wiki)

    # ── Chat ────────────────────────────────────────────────

    def chat(
        self,
        question: str,
        repo_slug: str,
        history: list[tuple[str, str]] | None = None,
    ) -> ChatResponse:
        """Ask Gemini a question about a repository.

        Args:
            question: The user's question.
            repo_slug: Repository slug (e.g. "excalidraw/excalidraw").
            history: Optional conversation history as [(text, role), ...].
        """
        messages = []
        if history:
            for text, role in history:
                messages.append([text, role])
        messages.append([question, "user"])

        github_url = f"https://github.com/{repo_slug}"
        params = [messages, [None, github_url]]

        raw = self._call(RPCMethod.CHAT, params)
        if not raw:
            raise NotFoundError(f"No response for {repo_slug}")

        answer = raw[0] if isinstance(raw, list) and raw else str(raw)
        return ChatResponse(answer=answer, repo_slug=repo_slug)
