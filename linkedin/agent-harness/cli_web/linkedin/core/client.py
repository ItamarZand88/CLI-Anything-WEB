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
    raise_for_status,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://www.linkedin.com"
VOYAGER_API = f"{BASE_URL}/voyager/api"
GRAPHQL_URL = f"{VOYAGER_API}/graphql"

# GraphQL query IDs captured from LinkedIn traffic
QUERY_IDS = {
    "feed": "voyagerFeedDashMainFeed.923020905727c01516495a0ac90bb475",
    "profile_by_identity": "voyagerIdentityDashProfiles.b5c27c04968c409fc0ed3546575b9b7a",
    "profile_by_urn": "voyagerIdentityDashProfiles.da93c92bffce3da586a992376e42a305",
    "company": "voyagerOrganizationDashCompanies.148b1aebfadd0a455f32806df656c3c1",
    "job_cards": "voyagerJobsDashJobCards.11efe66ab8e00aabdc31cf0a7f095a32",
    "job_posting": "voyagerJobsDashJobPostings.891aed7916d7453a37e4bbf5f1f60de4",
    "topics": "voyagerFeedDashTopics.9075cab8b59e14d62b497b48f77d5e12",
    "search_clusters": "voyagerSearchDashClusters.b0928897b71bd00a5a7291c2a2e5f8b0",
}

# LinkedIn li-track header payload
LI_TRACK = json.dumps(
    {
        "clientVersion": "1.13.0",
        "mpVersion": "1.13.0",
        "osName": "web",
        "timezoneOffset": 0,
        "deviceFormFactor": "DESKTOP",
        "mpName": "voyager-web",
    }
)


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

    def __init__(self, cookies: dict | None = None):
        if cookies is None:
            auth_data = load_auth()
            cookies = auth_data.get("cookies", auth_data)
        self._cookies = cookies
        self._session = curl_requests.Session(impersonate="chrome")

        csrf = _extract_csrf(self._cookies)
        # Do NOT set User-Agent — curl_cffi injects a matching Chrome UA
        # via impersonation. Overriding it breaks TLS/UA consistency.
        self._session.headers.update(
            {
                "csrf-token": csrf,
                "x-restli-protocol-version": "2.0.0",
                "x-li-track": LI_TRACK,
                "x-li-lang": "en_US",
                "accept-language": "en-US,en;q=0.9",
            }
        )
        self._request_count = 0

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
        """Issue an HTTP request with auto-refresh on token expiry.

        Flow (matches Reddit CLI pattern):
          attempt 0: try with current cookies
          attempt 1: reload cookies from disk (user may have re-logged in)
          attempt 2: headless browser refresh (silently navigate to linkedin.com)

        After all retries fail, raises AuthError.
        """
        # Jitter between consecutive requests (skip the first one)
        if self._request_count > 0 and _attempt == 0:
            self._human_delay()
        self._request_count += 1

        kwargs.setdefault("cookies", self._cookies)
        try:
            resp = self._session.request(method, url, **kwargs)
        except Exception as exc:
            raise NetworkError(f"Connection failed: {exc}")

        if resp.status_code in (401, 403) and _attempt < 2:
            if _attempt == 0:
                # First retry: reload cookies from disk
                self._reload_cookies_from_disk()
            elif _attempt == 1:
                # Second retry: headless browser refresh
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
        """Silently refresh cookies using headless browser.

        Launches headless Chromium with the persistent browser profile,
        navigates to LinkedIn (which refreshes the session cookies),
        extracts and saves the new cookies. No user interaction needed.
        """
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
    # Company
    # ------------------------------------------------------------------

    def get_company(self, name: str) -> dict:
        """Get a company page by its universal name (URL slug).

        Args:
            name: Company universal name (e.g. ``google``).

        Returns:
            Company data dict.
        """
        variables = f"(universalName:{name})"
        return self._graphql_get(QUERY_IDS["company"], variables)

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

    def _search(
        self,
        query: str,
        vertical: str = "PEOPLE",
        start: int = 0,
        count: int = 10,
    ) -> dict:
        """Universal search via the ``voyagerSearchDashClusters`` GraphQL endpoint.

        Args:
            query: Search keywords.
            vertical: One of ``PEOPLE``, ``COMPANIES``, ``CONTENT``, ``JOBS``.
            start: Pagination offset.
            count: Number of results.

        Returns:
            Raw GraphQL response dict.
        """
        encoded_query = quote(query, safe="")
        type_filter = ""
        if vertical == "PEOPLE":
            type_filter = "(key:resultType,value:List(PEOPLE))"
        elif vertical == "COMPANIES":
            type_filter = "(key:resultType,value:List(COMPANIES))"
        elif vertical == "CONTENT":
            type_filter = "(key:resultType,value:List(CONTENT))"
        elif vertical == "JOBS":
            type_filter = "(key:resultType,value:List(JOBS))"

        filters = f",queryParameters:List({type_filter})" if type_filter else ""
        variables = (
            f"(start:{start},origin:GLOBAL_SEARCH_HEADER,"
            f"query:(keywords:{encoded_query},"
            f"flagshipSearchIntent:SEARCH_SRP"
            f"{filters},"
            f"includeFiltersInResponse:false))"
        )
        return self._graphql_get(QUERY_IDS["search_clusters"], variables)

    def search_people(self, query: str, start: int = 0, count: int = 10) -> dict:
        """Search for people via the Voyager GraphQL search endpoint."""
        return self._search(query, vertical="PEOPLE", start=start, count=count)

    def search_posts(self, query: str, start: int = 0, count: int = 10) -> dict:
        """Search for posts/content via the Voyager GraphQL search endpoint."""
        return self._search(query, vertical="CONTENT", start=start, count=count)

    def search_companies(self, query: str, start: int = 0, count: int = 10) -> dict:
        """Search for companies via the Voyager GraphQL search endpoint."""
        return self._search(query, vertical="COMPANIES", start=start, count=count)

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    def get_job(self, job_id: str) -> dict:
        """Get job posting details by searching for the specific job."""
        # Strip URN prefix if provided
        if job_id.startswith("urn:"):
            job_id = job_id.split(":")[-1]
        # Search with the job ID as keyword to find it
        result = self.search_jobs(job_id, count=5)
        for el in result.get("elements", []):
            card = el.get("jobCardUnion", {}).get("jobPostingCard", {})
            if card and job_id in str(card.get("entityUrn", "")):
                return card
        # Return first result as fallback
        for el in result.get("elements", []):
            card = el.get("jobCardUnion", {}).get("jobPostingCard", {})
            if card:
                return card
        from .exceptions import NotFoundError
        raise NotFoundError(f"Job {job_id} not found")

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
        resp = self._request("DELETE", url)
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
        resp = self._request("DELETE", url)
        return {}

    def unreact(self, entity_urn: str) -> dict:
        """Remove a reaction from a post."""
        encoded = quote(entity_urn, safe="")
        url = f"{VOYAGER_API}/reactions/{encoded}"
        resp = self._request("DELETE", url)
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
        resp = self._request("GET", url)
        return resp.json()

    # ------------------------------------------------------------------
    # Network / Connections
    # ------------------------------------------------------------------

    def get_connections(self, start: int = 0, count: int = 20) -> dict:
        """Get connections summary."""
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
        resp = self._request("GET", url)
        return resp.json()

    def get_my_profile_urn(self) -> str:
        """Get the current user's profile URN for messaging."""
        data = self._rest_get("me")
        mp = data.get("miniProfile", data)
        return mp.get("dashEntityUrn", mp.get("entityUrn", ""))

    def get_conversations(self, count: int = 20) -> dict:
        """Get messaging conversations list."""
        profile_urn = self.get_my_profile_urn()
        variables = f"(mailboxUrn:{profile_urn})"
        return self._messaging_graphql(
            "messengerConversations.0d5e6781bbee71c3e51c8843c6519f48",
            variables,
        )

    def get_conversation_messages(self, conversation_urn: str, count: int = 20) -> dict:
        """Get messages in a conversation."""
        variables = f"(conversationUrn:{conversation_urn})"
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
