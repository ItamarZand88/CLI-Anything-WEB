"""HTTP client for cli-web-linkedin (curl_cffi for anti-bot bypass)."""
from __future__ import annotations

import json
import random
import re
import time
from urllib.parse import quote

from curl_cffi import requests as curl_requests

from .auth import load_auth, refresh_auth
from .exceptions import (
    LinkedinError,
    AuthError,
    NetworkError,
    RateLimitError,
    raise_for_status,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://www.linkedin.com"
VOYAGER_API = f"{BASE_URL}/voyager/api"
GRAPHQL_URL = f"{VOYAGER_API}/graphql"

QUERY_IDS = {
    "feed": "voyagerFeedDashMainFeed.923020905727c01516495a0ac90bb475",
    "search_clusters": "voyagerSearchDashClusters.b0928897b71bd00a5a7291755dcd64f0",
}


def _build_li_track() -> str:
    """Build the x-li-track header with the system timezone offset."""
    try:
        tz_offset = -time.timezone // 60  # minutes, sign matches JS convention
    except Exception:
        tz_offset = 0
    return json.dumps({
        "clientVersion": "1.13.0",
        "mpVersion": "1.13.0",
        "osName": "web",
        "timezoneOffset": tz_offset,
        "deviceFormFactor": "DESKTOP",
        "mpName": "voyager-web",
    })


def _extract_csrf(cookies: dict) -> str:
    """Extract CSRF token from JSESSIONID cookie.

    LinkedIn expects the csrf-token header to be ``ajax:<JSESSIONID_value>``
    (with surrounding double-quotes stripped).
    """
    jsessionid = cookies.get("JSESSIONID", "")
    # The cookie value is often wrapped in double-quotes: "ajax:123456"
    jsessionid = jsessionid.strip('"')
    if not jsessionid:
        raise AuthError(
            "JSESSIONID cookie missing — cannot compute CSRF token. "
            "Run: cli-web-linkedin auth login",
            recoverable=False,
        )
    return jsessionid


class LinkedinClient:
    """REST + GraphQL client using curl_cffi Chrome TLS impersonation."""

    # Minimum seconds between headless browser refresh attempts
    _REFRESH_COOLDOWN = 300  # 5 minutes

    def __init__(self, cookies: dict | None = None):
        if cookies is None:
            auth_data = load_auth()
            cookies = auth_data.get("cookies", auth_data)
        self._cookies = cookies
        self._session = curl_requests.Session(impersonate="chrome")

        csrf = _extract_csrf(self._cookies)
        # Do NOT set User-Agent or accept-language — curl_cffi injects
        # matching headers via impersonation. Overriding breaks consistency.
        self._session.headers.update(
            {
                "csrf-token": csrf,
                "x-restli-protocol-version": "2.0.0",
                "x-li-track": _build_li_track(),
                "x-li-lang": "en_US",
                "Origin": BASE_URL,
            }
        )
        self._request_count = 0
        self._my_urn: str | None = None
        self._last_refresh: float = 0

    # ------------------------------------------------------------------
    # Low-level request helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _human_delay() -> None:
        """Sleep a short Gaussian-random duration between API calls.

        Avoids fixed-interval timing patterns that LinkedIn's behavioral
        analysis flags as bot traffic.  Mean ~1.5s, std ~0.5s, min 0.3s.
        """
        delay = max(0.3, random.gauss(1.5, 0.5))
        time.sleep(delay)

    def _request(
        self,
        method: str,
        url: str,
        *,
        _attempt: int = 0,
        **kwargs,
    ):
        """Issue an HTTP request with retry on auth expiry and rate limits.

        Retry flow:
          attempt 0 → 401/403 → reload cookies from disk
          attempt 1 → 401/403 → headless browser refresh
          attempt 2 → 401/403 → raise AuthError

        On 429: sleep for Retry-After (max 300s) and retry once.
        """
        # Jitter between consecutive requests (skip the first one)
        if self._request_count > 0 and _attempt == 0:
            self._human_delay()
        self._request_count += 1

        # Inject Referer for the current request context
        hdrs = kwargs.get("headers", {}) or {}
        if "Referer" not in hdrs:
            hdrs["Referer"] = f"{BASE_URL}/feed/"
            kwargs["headers"] = hdrs

        kwargs.setdefault("cookies", self._cookies)
        try:
            resp = self._session.request(method, url, **kwargs)
        except Exception as exc:
            raise NetworkError(f"Connection failed: {exc}")

        # Rate limit — honour Retry-After and retry once
        if resp.status_code == 429 and _attempt < 1:
            retry_after = 60.0
            raw = resp.headers.get("Retry-After")
            if raw:
                try:
                    retry_after = float(raw)
                except ValueError:
                    pass
            time.sleep(min(retry_after, 300))
            return self._request(method, url, _attempt=_attempt + 1, **kwargs)

        # Auth expiry — reload cookies or refresh via browser
        if resp.status_code in (401, 403) and _attempt < 2:
            if _attempt == 0:
                self._reload_cookies_from_disk()
            elif _attempt == 1:
                self._refresh_via_browser()
            kwargs.pop("cookies", None)
            kwargs["cookies"] = self._cookies
            return self._request(method, url, _attempt=_attempt + 1, **kwargs)

        raise_for_status(resp)
        return resp

    def _reload_cookies_from_disk(self) -> None:
        """Reload cookies from auth.json (user may have re-logged in)."""
        try:
            auth_data = load_auth()
            self._cookies = auth_data.get("cookies", auth_data)
            csrf = _extract_csrf(self._cookies)
            self._session.headers["csrf-token"] = csrf
        except AuthError:
            pass  # Fall through to browser refresh

    def _refresh_via_browser(self) -> None:
        """Silently refresh cookies by delegating to ``refresh_auth()``."""
        now = time.time()
        if now - self._last_refresh < self._REFRESH_COOLDOWN:
            raise AuthError(
                "Session expired (refresh on cooldown). "
                "Run: cli-web-linkedin auth login",
                recoverable=False,
            )
        self._last_refresh = now
        auth_data = refresh_auth()
        if auth_data:
            self._cookies = auth_data.get("cookies", {})
            csrf = _extract_csrf(self._cookies)
            self._session.headers["csrf-token"] = csrf
        else:
            raise AuthError(
                "Session expired and auto-refresh failed. "
                "Run: cli-web-linkedin auth login",
                recoverable=False,
            )

    # ------------------------------------------------------------------
    # GraphQL & REST primitives
    # ------------------------------------------------------------------

    def _graphql_get(self, query_id: str, variables_str: str) -> dict:
        """Execute a LinkedIn GraphQL GET query.

        Args:
            query_id: The full ``service.hash`` query identifier.
            variables_str: LinkedIn-serialized variables string, e.g.
                ``(start:0,count:10)``.

        Returns:
            Parsed JSON response body.
        """
        # Build URL manually — LinkedIn rejects URL-encoded parentheses in variables
        url = (
            f"{GRAPHQL_URL}"
            f"?includeWebMetadata=true"
            f"&variables={variables_str}"
            f"&queryId={query_id}"
        )
        resp = self._request(
            "GET", url,
            headers={"Accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        data = resp.json()
        if "errors" in data and data["errors"]:
            msg = data["errors"][0].get("message", "GraphQL error")
            raise LinkedinError(f"GraphQL error: {msg}")
        return data

    def _rest_get(self, path: str, params: dict | None = None) -> dict:
        """GET a Voyager REST endpoint.

        Args:
            path: Path relative to ``/voyager/api/`` (no leading slash needed).
            params: Optional query parameters.

        Returns:
            Parsed JSON response body.
        """
        url = f"{VOYAGER_API}/{path.lstrip('/')}"
        resp = self._request(
            "GET", url, params=params,
            headers={"Accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        return resp.json()

    def _rest_post(self, path: str, data: dict | None = None) -> dict:
        """POST to a Voyager REST endpoint.

        Args:
            path: Path relative to ``/voyager/api/``.
            data: JSON-serializable request body.

        Returns:
            Parsed JSON response body (empty dict for 201/204).
        """
        url = f"{VOYAGER_API}/{path.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/vnd.linkedin.normalized+json+2.1",
        }
        resp = self._request("POST", url, json=data, headers=headers)
        if resp.status_code in (201, 204) or not resp.text.strip():
            return {}
        return resp.json()

    # ------------------------------------------------------------------
    # Me
    # ------------------------------------------------------------------

    def get_me(self) -> dict:
        """Get the current user's profile data."""
        return self._rest_get("me")

    # ------------------------------------------------------------------
    # Feed
    # ------------------------------------------------------------------

    def get_feed(self, start: int = 0, count: int = 10) -> dict:
        """Fetch the LinkedIn home feed.

        Args:
            start: Pagination offset.
            count: Number of items to fetch.

        Returns:
            Feed response dict.
        """
        variables = f"(start:{start},count:{count},sortOrder:MEMBER_SETTING)"
        return self._graphql_get(QUERY_IDS["feed"], variables)

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, username: str) -> dict:
        """Get a user profile by public identifier (vanity name).

        Uses the REST identity endpoint which accepts a vanity-name lookup.

        Args:
            username: LinkedIn public profile identifier (e.g. ``johndoe``).

        Returns:
            Profile data dict.
        """
        encoded = quote(username, safe="")
        return self._rest_get(
            f"identity/dash/profiles",
            params={
                "q": "memberIdentity",
                "memberIdentity": encoded,
                "decorationId": (
                    "com.linkedin.voyager.dash.deco.identity.profile."
                    "FullProfileWithEntities-93"
                ),
            },
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_jobs(self, query: str, start: int = 0, count: int = 25) -> dict:
        """Search for jobs via the Voyager JobCards REST endpoint."""
        encoded_query = quote(query, safe="")
        url = (
            f"{VOYAGER_API}/voyagerJobsDashJobCards"
            f"?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-220"
            f"&count={count}"
            f"&q=jobSearch"
            f"&query=(origin:JOB_SEARCH_PAGE_OTHER_ENTRY,keywords:{encoded_query},spellCorrectionEnabled:true)"
            f"&start={start}"
        )
        resp = self._request(
            "GET", url,
            headers={"Accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        return resp.json()

    def search(
        self,
        query: str,
        vertical: str = "PEOPLE",
        start: int = 0,
        count: int = 10,
    ) -> dict:
        """Search via the ``voyagerSearchDashClusters`` GraphQL endpoint.

        Args:
            query: Search keywords.
            vertical: ``PEOPLE``, ``COMPANIES``, ``JOBS``, or ``""`` for unfiltered.
            start: Pagination offset.
            count: Number of results.
        """
        encoded_query = quote(query, safe="")
        type_filter = {
            "PEOPLE": "(key:resultType,value:List(PEOPLE))",
            "COMPANIES": "(key:resultType,value:List(COMPANIES))",
            "JOBS": "(key:resultType,value:List(JOBS))",
        }.get(vertical, "")

        filters = f",queryParameters:List({type_filter})" if type_filter else ""
        variables = (
            f"(start:{start},count:{count},origin:GLOBAL_SEARCH_HEADER,"
            f"query:(keywords:{encoded_query},"
            f"flagshipSearchIntent:SEARCH_SRP"
            f"{filters},"
            f"includeFiltersInResponse:false))"
        )
        return self._graphql_get(QUERY_IDS["search_clusters"], variables)

    def search_people(self, query: str, start: int = 0, count: int = 10) -> dict:
        """Search for people."""
        return self.search(query, vertical="PEOPLE", start=start, count=count)

    def search_companies(self, query: str, start: int = 0, count: int = 10) -> dict:
        """Search for companies."""
        return self.search(query, vertical="COMPANIES", start=start, count=count)

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    def get_job(self, job_id: str) -> dict:
        """Get full job posting details via ``voyagerJobsDashJobPostings``."""
        if job_id.startswith("urn:"):
            job_id = job_id.split(":")[-1]
        encoded_urn = quote(f"urn:li:fsd_jobPosting:{job_id}", safe="")
        url = f"{VOYAGER_API}/voyagerJobsDashJobPostings/{encoded_urn}"
        resp = self._request(
            "GET", url,
            headers={"Accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        return resp.json()

    # ------------------------------------------------------------------
    # Reactions
    # ------------------------------------------------------------------

    def react(self, entity_urn: str, reaction_type: str = "LIKE") -> dict:
        """React to a post.

        Args:
            entity_urn: URN of the entity to react to, e.g.
                ``urn:li:activity:1234567890``.
            reaction_type: One of ``LIKE``, ``PRAISE`` (celebrate),
                ``EMPATHY`` (love), ``INTEREST`` (insightful),
                ``APPRECIATION`` (support), ``ENTERTAINMENT`` (funny).

        Returns:
            Empty dict on success.
        """
        reaction_type = reaction_type.upper()
        valid_types = {
            "LIKE", "PRAISE", "EMPATHY", "INTEREST",
            "APPRECIATION", "ENTERTAINMENT",
        }
        if reaction_type not in valid_types:
            raise LinkedinError(
                f"Invalid reaction type '{reaction_type}'. "
                f"Valid types: {', '.join(sorted(valid_types))}"
            )

        payload = {
            "reactionType": reaction_type,
            "entityUrn": entity_urn,
        }
        return self._rest_post("reactions", data=payload)

    # ------------------------------------------------------------------
    # Create post
    # ------------------------------------------------------------------

    def create_post(self, text: str) -> dict:
        """Publish a text post to the LinkedIn feed.

        Args:
            text: Post body text.

        Returns:
            Response dict (may contain the created post URN).
        """
        payload = {
            "visibleToConnectionsOnly": False,
            "externalAudienceProviders": [],
            "commentaryV2": {
                "text": text,
                "attributes": [],
            },
            "origin": "FEED",
            "allowedCommentersScope": "ALL",
            "postState": "PUBLISHED",
        }
        return self._rest_post("feed/dash/posts", data=payload)

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def add_comment(self, entity_urn: str, text: str) -> dict:
        """Add a comment to a post.

        Args:
            entity_urn: URN of the entity to comment on, e.g.
                ``urn:li:activity:1234567890``.
            text: Comment text.

        Returns:
            Response dict (may contain the created comment URN).
        """
        payload = {
            "threadUrn": entity_urn,
            "commentaryV2": {
                "text": text,
                "attributes": [],
            },
        }
        return self._rest_post("feed/dash/comments", data=payload)

    def edit_comment(self, comment_urn: str, text: str) -> dict:
        """Edit an existing comment."""
        payload = {
            "commentaryV2": {
                "text": text,
                "attributes": [],
            },
        }
        encoded = quote(comment_urn, safe="")
        url = f"{VOYAGER_API}/feed/dash/comments/{encoded}"
        resp = self._request("PUT", url, json=payload,
                             headers={"Content-Type": "application/json"})
        try:
            return resp.json()
        except Exception:
            return {}

    def delete_comment(self, comment_urn: str) -> dict:
        """Delete a comment."""
        url = f"{VOYAGER_API}/feed/dash/comments/{quote(comment_urn, safe='')}"
        self._request("DELETE", url)
        return {}

    # ------------------------------------------------------------------
    # Post management
    # ------------------------------------------------------------------

    def edit_post(self, post_urn: str, text: str) -> dict:
        """Edit an existing post."""
        payload = {
            "commentary": text,
        }
        url = f"{VOYAGER_API}/feed/dash/posts/{quote(post_urn, safe='')}"
        resp = self._request("PUT", url, json=payload)
        try:
            return resp.json()
        except Exception:
            return {}

    def delete_post(self, post_urn: str) -> dict:
        """Delete a post."""
        url = f"{VOYAGER_API}/feed/dash/posts/{quote(post_urn, safe='')}"
        self._request("DELETE", url)
        return {}

    def unreact(self, entity_urn: str) -> dict:
        """Remove a reaction from a post."""
        encoded = quote(entity_urn, safe="")
        url = f"{VOYAGER_API}/reactions/{encoded}"
        self._request("DELETE", url)
        return {}

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def get_notifications(self, start: int = 0, count: int = 20) -> dict:
        """Get notification cards."""
        url = (
            f"{VOYAGER_API}/voyagerIdentityDashNotificationCards"
            f"?decorationId=com.linkedin.voyager.dash.deco.identity.notifications.CardsCollectionWithInjectionsNoPills-24"
            f"&count={count}&start={start}"
            f"&q=filterVanityName"
        )
        resp = self._request(
            "GET", url,
            headers={"Accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        return resp.json()

    # ------------------------------------------------------------------
    # Network / Connections
    # ------------------------------------------------------------------

    def get_connections(self, start: int = 0, count: int = 40) -> dict:
        """Get connections list via the REST endpoint."""
        url = (
            f"{VOYAGER_API}/relationships/dash/connections"
            f"?decorationId=com.linkedin.voyager.dash.deco.web.mynetwork.ConnectionListWithProfile-5"
            f"&count={count}&start={start}"
            f"&q=search&sortType=RECENTLY_ADDED"
        )
        resp = self._request(
            "GET", url,
            headers={"Accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        return resp.json()

    def get_connection_count(self) -> dict:
        """Get connections summary (count only)."""
        url = f"{VOYAGER_API}/relationships/connectionsSummary"
        resp = self._request("GET", url)
        return resp.json()

    def get_invitations(self, start: int = 0, count: int = 10) -> dict:
        """Get pending connection invitations."""
        url = (
            f"{VOYAGER_API}/relationships/invitationViews"
            f"?includeInsights=true&q=receivedInvitation&start={start}&count={count}"
        )
        resp = self._request("GET", url)
        return resp.json()

    def send_connection(self, profile_urn: str, message: str = "") -> dict:
        """Send a connection request."""
        payload = {
            "inviteeProfileUrn": profile_urn,
        }
        if message:
            payload["message"] = message
        return self._rest_post("relationships/invitations", data=payload)

    def accept_invitation(self, invitation_urn: str) -> dict:
        """Accept a pending connection invitation."""
        encoded = quote(invitation_urn, safe="")
        url = f"{VOYAGER_API}/relationships/invitations/{encoded}?action=accept"
        resp = self._request(
            "POST", url,
            headers={"Content-Type": "application/json"},
        )
        try:
            return resp.json()
        except Exception:
            return {}

    def decline_invitation(self, invitation_urn: str) -> dict:
        """Decline a pending connection invitation."""
        encoded = quote(invitation_urn, safe="")
        url = f"{VOYAGER_API}/relationships/invitations/{encoded}?action=decline"
        resp = self._request(
            "POST", url,
            headers={"Content-Type": "application/json"},
        )
        try:
            return resp.json()
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def _messaging_graphql(self, query_id: str, variables_str: str) -> dict:
        """Execute a messaging-specific GraphQL query.

        LinkedIn messaging uses a separate GraphQL endpoint at
        /voyager/api/voyagerMessagingGraphQL/graphql.
        URNs in variables MUST be URL-encoded.
        """
        # Encode colons inside URN identifiers (urn:li:...:value) while
        # preserving structural chars (parens, commas).
        encoded_vars = re.sub(
            r"urn:li:[\w]+:[^,)]+",
            lambda m: quote(m.group(0), safe=""),
            variables_str,
        )
        url = (
            f"{VOYAGER_API}/voyagerMessagingGraphQL/graphql"
            f"?queryId={query_id}"
            f"&variables={encoded_vars}"
        )
        resp = self._request(
            "GET", url,
            headers={"Accept": "application/vnd.linkedin.normalized+json+2.1"},
        )
        return resp.json()

    def get_my_profile_urn(self) -> str:
        """Get the current user's profile URN (cached after first call)."""
        if self._my_urn:
            return self._my_urn
        data = self._rest_get("me")
        mp = data.get("miniProfile", data)
        if not mp.get("dashEntityUrn") and data.get("included"):
            mp = data["included"][0]
        self._my_urn = mp.get("dashEntityUrn", mp.get("entityUrn", ""))
        return self._my_urn

    def get_conversations(self, count: int = 20) -> dict:
        """Get messaging conversations list."""
        profile_urn = self.get_my_profile_urn()
        variables = f"(mailboxUrn:{profile_urn},count:{count})"
        return self._messaging_graphql(
            "messengerConversations.0d5e6781bbee71c3e51c8843c6519f48",
            variables,
        )

    def get_conversation_messages(self, conversation_urn: str, count: int = 20) -> dict:
        """Get messages in a conversation."""
        variables = f"(conversationUrn:{conversation_urn},count:{count})"
        return self._messaging_graphql(
            "messengerMessages.5846eeb71c981f11e0134cb6626cc314",
            variables,
        )

    def send_message(self, recipient: str, text: str) -> dict:
        """Send a message to a recipient.

        Args:
            recipient: Either a conversation URN (urn:li:msg_conversation:...)
                      or a profile URN (urn:li:fsd_profile:...) for new conversations.
            text: Message text.

        Returns:
            Response dict with message entity URN.
        """
        my_urn = self.get_my_profile_urn()
        payload = {
            "body": text,
            "mailboxUrn": my_urn,
        }
        if "msg_conversation" in recipient:
            payload["conversationUrn"] = recipient
        else:
            # New conversation — recipient is a profile URN
            payload["recipientProfileUrns"] = [recipient]

        url = f"{VOYAGER_API}/voyagerMessagingDashMessengerMessages?action=createMessage"
        headers = {"Content-Type": "application/json"}
        resp = self._request("POST", url, json=payload, headers=headers)
        try:
            return resp.json()
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Follow / Unfollow
    # ------------------------------------------------------------------

    def follow_company(self, company_urn: str) -> dict:
        """Follow a company."""
        payload = {"followee": company_urn}
        return self._rest_post("feed/follows", data=payload)

    def unfollow_company(self, company_urn: str) -> dict:
        """Unfollow a company."""
        encoded = quote(company_urn, safe="")
        url = f"{VOYAGER_API}/feed/follows/{encoded}"
        resp = self._request("DELETE", url)
        return {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self) -> LinkedinClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()
