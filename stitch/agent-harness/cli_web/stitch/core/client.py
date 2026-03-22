"""HTTP client for Stitch batchexecute API."""
import json
import time
from typing import Any, Optional

import httpx

from .auth import fetch_tokens, fetch_user_info, load_cookies
from .exceptions import (
    AuthError, NetworkError, RateLimitError, ServerError, NotFoundError, RPCError,
    StitchError,
)
from .models import (
    Project, Screen, Session, User,
    parse_project, parse_screen, parse_session,
)
from .rpc import encode_request, build_url, decode_response
from .rpc.types import RPCMethod, BASE_URL
from .session import get_session

DOWNLOAD_BASE = "https://contribution.usercontent.google.com/download"


class StitchClient:
    """Client for the Stitch batchexecute API.

    Manages auth tokens, request IDs, and automatic token refresh on auth errors.
    """

    def __init__(self):
        self._cookies: Optional[dict] = None
        self._csrf: Optional[str] = None
        self._session_id: Optional[str] = None
        self._build_label: Optional[str] = None
        self._session = get_session()

    def _ensure_auth(self):
        """Load cookies and fetch tokens if not already done."""
        if self._cookies is None:
            self._cookies = load_cookies()
        if self._csrf is None:
            self._csrf, self._session_id, self._build_label = fetch_tokens(self._cookies)

    def _refresh_tokens(self):
        """Re-fetch tokens (called on auth error to retry)."""
        if self._cookies is None:
            self._cookies = load_cookies()
        self._csrf, self._session_id, self._build_label = fetch_tokens(self._cookies)

    def _call(
        self,
        rpc_id: str,
        params: list,
        source_path: str = "/",
        retry_on_auth: bool = True,
    ) -> Any:
        """Execute a batchexecute RPC call."""
        self._ensure_auth()

        req_id = self._session.next_req_id()
        url = build_url(
            rpc_id=rpc_id,
            session_id=self._session_id or "",
            build_label=self._build_label or "",
            source_path=source_path,
            req_id=req_id,
        )
        body = encode_request(rpc_id, params, self._csrf or "")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "x-same-domain": "1",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        try:
            resp = httpx.post(
                url,
                content=body.encode("utf-8"),
                headers=headers,
                cookies=self._cookies,
                follow_redirects=False,
                timeout=30.0,
            )
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}")
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}")
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}")

        if resp.status_code in (401, 403) and retry_on_auth:
            self._refresh_tokens()
            return self._call(rpc_id, params, source_path, retry_on_auth=False)

        if resp.status_code == 404:
            raise NotFoundError(f"Not found: {resp.text[:200]}")

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            raise RateLimitError(
                "Rate limited — please wait and try again",
                retry_after=float(retry_after) if retry_after else None,
            )

        if resp.status_code >= 500:
            raise ServerError(f"HTTP {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)

        if resp.status_code >= 400:
            raise StitchError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        return decode_response(resp.content, rpc_id)

    # ── Projects ──────────────────────────────────────────────────────────

    def list_projects(self) -> list[Project]:
        """List all projects owned by the current user."""
        result = self._call(RPCMethod.LIST_PROJECTS, [])
        if not result or not isinstance(result, list):
            return []
        projects = []
        entries = result[0] if result and isinstance(result[0], list) else result
        for raw in entries:
            if isinstance(raw, list):
                p = parse_project(raw)
                if p:
                    projects.append(p)
        return projects

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project details."""
        resource_name = _to_resource(project_id)
        result = self._call(
            RPCMethod.GET_PROJECT,
            [resource_name],
            source_path=f"/projects/{_bare_id(project_id)}",
        )
        if result and isinstance(result, list):
            return parse_project(result)
        return None

    def create_project(self) -> Optional[Project]:
        """Create a new empty project.

        The CREATE_PROJECT RPC params are: [[null, null, null, null, null, 4]]
        where 4 is the initial project status.
        """
        result = self._call(RPCMethod.CREATE_PROJECT, [[None, None, None, None, None, 4]])
        if result and isinstance(result, list):
            return parse_project(result)
        return None

    def create_project_and_generate(
        self,
        prompt: str,
        platform: str = "app",
        timeout: float = 300.0,
        on_progress: Any = None,
    ) -> Optional[Project]:
        """Create a new project and generate a design from prompt."""
        project = self.create_project()
        if not project:
            return None

        # Generate design in the new project
        self.generate_and_wait(
            project.id, prompt, platform=platform, timeout=timeout, on_progress=on_progress
        )

        # Refresh project to get updated state
        refreshed = self.get_project(project.id)
        return refreshed if refreshed else project

    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        resource_name = _to_resource(project_id)
        self._call(
            RPCMethod.DELETE_PROJECT,
            [resource_name],
            source_path=f"/projects/{_bare_id(project_id)}",
        )
        return True

    def duplicate_project(self, project_id: str) -> Optional[str]:
        """Duplicate a project. Returns the new project ID.

        Uses vW3whd RPC with params [resource_name].
        Response: [null, "projects/<new_id>"].
        """
        resource_name = _to_resource(project_id)
        result = self._call(
            "vW3whd",  # DUPLICATE_PROJECT
            [resource_name],
            source_path=f"/projects/{_bare_id(project_id)}",
        )
        if result and isinstance(result, list) and len(result) > 1:
            new_resource = result[1]
            if isinstance(new_resource, str) and "projects/" in new_resource:
                return new_resource.split("/")[-1]
        return None

    def rename_project(self, project_id: str, new_title: str) -> Optional[Project]:
        """Rename a project using GET_PROJECT_STATE (f6CJY) with updated title.

        The rename is done by sending the full project state with the new title
        at index [1] of the project array. The server interprets this as an update.
        """
        resource_name = _to_resource(project_id)
        # Get current project state first
        project = self.get_project(project_id)
        if not project:
            return None

        # Build the update params: [project_state, field_mask]
        # The state array has: [resource_name, title, type, ...]
        state = [
            resource_name,
            new_title,
            2,  # type
            None,  # created_at
            None,  # modified_at
            4,  # status
            [None, None, ""],  # thumbnail placeholder
            1,  # owner flag
            None,  # theme_mode
            [],  # theme_config
        ]
        field_mask = [["title"]]
        result = self._call(
            RPCMethod.GET_PROJECT_STATE,
            [state, field_mask],
            source_path=f"/projects/{_bare_id(project_id)}",
        )
        if result and isinstance(result, list):
            return parse_project(result)
        return None

    def get_design_system(self, project_id: str) -> Optional[dict]:
        """Get the design system (colors, typography) for a project.

        Returns a dict with 'name', 'colors' (Material Design 3 tokens),
        and 'description' (markdown). Uses GET_PROJECT (eW2RYb) which
        returns the theme config at result[9].
        """
        resource_name = _to_resource(project_id)
        result = self._call(
            RPCMethod.GET_PROJECT,
            [resource_name],
            source_path=f"/projects/{_bare_id(project_id)}",
        )
        if not result or not isinstance(result, list):
            return None

        # Design system is at index [9] of the project response
        theme_config = None
        try:
            theme_config = result[9] if len(result) > 9 else None
        except (IndexError, TypeError):
            pass

        if not theme_config or not isinstance(theme_config, list):
            return None

        # Extract name from the design system
        name = ""
        primary_color = ""
        colors = {}
        description = ""

        try:
            # Primary color at index [4]
            primary_color = theme_config[4] if len(theme_config) > 4 else ""

            # Color tokens at index [12] — array of [name, hex_color]
            if len(theme_config) > 12 and isinstance(theme_config[12], list):
                for pair in theme_config[12]:
                    if isinstance(pair, list) and len(pair) >= 2:
                        colors[pair[0]] = pair[1]

            # Design system markdown at index [13]
            if len(theme_config) > 13 and isinstance(theme_config[13], str):
                description = theme_config[13]
                # Extract name from first heading
                for line in description.split("\n"):
                    if line.startswith("# "):
                        name = line[2:].strip()
                        break
        except (IndexError, TypeError):
            pass

        return {
            "name": name,
            "primary_color": primary_color,
            "colors": colors,
            "description": description,
        }

    def export_project(self, project_id: str) -> bool:
        """Trigger project export as ZIP. Download happens separately."""
        resource_name = _to_resource(project_id)
        self._call(
            RPCMethod.EXPORT_PROJECT,
            [resource_name],
            source_path=f"/projects/{_bare_id(project_id)}",
        )
        return True

    # ── Screens ───────────────────────────────────────────────────────────

    def list_screens(self, project_id: str) -> list[Screen]:
        """List all screens in a project."""
        resource_name = _to_resource(project_id)
        result = self._call(
            RPCMethod.LIST_SCREENS,
            [resource_name],
            source_path=f"/projects/{_bare_id(project_id)}",
        )
        if not result or not isinstance(result, list):
            return []
        screens = []
        # Response is nested: [[screen1, screen2, ...]]
        entries = result[0] if result and isinstance(result[0], list) else result
        for raw in entries:
            if isinstance(raw, list):
                s = parse_screen(raw)
                if s:
                    screens.append(s)
        return screens

    def download_screen_html(self, html_url: str) -> bytes:
        """Download screen HTML content from Google content server."""
        self._ensure_auth()
        try:
            resp = httpx.get(
                html_url,
                cookies=self._cookies,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
                follow_redirects=True,
                timeout=30.0,
            )
            if resp.status_code == 404:
                raise NotFoundError(f"Screen HTML not found: {html_url[:100]}")
            if resp.status_code in (401, 403):
                raise AuthError("Auth failed downloading screen HTML", recoverable=True)
            if resp.status_code >= 400:
                raise ServerError(f"HTTP {resp.status_code} downloading screen", status_code=resp.status_code)
            return resp.content
        except httpx.RequestError as e:
            raise NetworkError(f"Download failed: {e}")

    # ── Design (Generation) ──────────────────────────────────────────────

    def send_prompt(
        self,
        project_id: str,
        prompt: str,
        platform: str = "app",
        model: str = "flash",
    ) -> Optional[Session]:
        """Send an AI design prompt to generate or modify screens.

        Args:
            project_id: Project to generate in
            prompt: Text description of desired design
            platform: "app" (mobile), "web", "tablet", or "agnostic"
            model: "flash" (3.0 Flash), "pro" (3.1 Pro Thinking), "redesign" (Nano Banana Pro)

        Returns:
            Session with initial status
        """
        resource_name = _to_resource(project_id)
        # Platform IDs: 1=mobile, 2=web/desktop, 3=tablet, 4=agnostic
        platform_map = {"app": 1, "mobile": 1, "web": 2, "desktop": 2, "tablet": 3, "agnostic": 4}
        platform_id = platform_map.get(platform.lower(), 1)
        # Model IDs: 3=Flash (default), values TBD for Pro/Redesign
        # The model ID goes at [1][3][2] in the param array (value 1 = default/flash)
        model_id = 1  # default flash
        if model.lower() in ("pro", "thinking"):
            model_id = 2
        elif model.lower() == "redesign":
            model_id = 3
        # Actual param structure from captured traffic:
        # ["projects/<id>", [null, null, null, [prompt, null, model_id, null, [], null, null, 1, [], platform_id], null, null, 1]]
        params = [
            resource_name,
            [None, None, None, [prompt, None, model_id, None, [], None, None, 1, [], platform_id], None, None, 1],
        ]
        result = self._call(
            RPCMethod.SEND_PROMPT,
            params,
            source_path=f"/projects/{_bare_id(project_id)}",
        )
        if result and isinstance(result, list):
            return parse_session(result)
        return None

    def poll_session(self, session_resource_name: str) -> Optional[Session]:
        """Poll a generation session for progress."""
        result = self._call(
            RPCMethod.POLL_SESSION,
            [session_resource_name],
        )
        if result and isinstance(result, list):
            return parse_session(result)
        return None

    def generate_and_wait(
        self,
        project_id: str,
        prompt: str,
        platform: str = "app",
        model: str = "flash",
        timeout: float = 300.0,
        on_progress: Any = None,
    ) -> Optional[Session]:
        """Send prompt and poll until generation completes.

        Args:
            project_id: Project to generate in
            prompt: Design prompt
            platform: "app", "web", "tablet", or "agnostic"
            model: "flash", "pro", or "redesign"
            timeout: Max seconds to wait
            on_progress: Optional callback(session) for progress updates

        Returns:
            Completed session with screens
        """
        session = self.send_prompt(project_id, prompt, platform, model)
        if not session:
            return None

        start = time.time()
        delay = 2.0
        max_delay = 10.0
        factor = 1.5

        while time.time() - start < timeout:
            time.sleep(delay)
            try:
                updated = self.poll_session(session.resource_name)
            except (RPCError, StitchError):
                updated = None

            if updated:
                session = updated
                if on_progress:
                    on_progress(session)
                # Status 3 = fully completed (2 = in-progress, 3 = done)
                if session.status is not None and session.status >= 3:
                    return session

            delay = min(delay * factor, max_delay)

        return session  # Return last state even if not complete

    def list_sessions(self, project_id: str) -> list[Session]:
        """List generation sessions (prompt history) for a project."""
        resource_name = _to_resource(project_id)
        result = self._call(
            RPCMethod.LIST_SESSIONS,
            [resource_name],
            source_path=f"/projects/{_bare_id(project_id)}",
        )
        if not result or not isinstance(result, list):
            return []
        sessions = []
        entries = result[0] if result and isinstance(result[0], list) else result
        for raw in entries:
            if isinstance(raw, list):
                s = parse_session(raw)
                if s:
                    sessions.append(s)
        return sessions

    # ── User ──────────────────────────────────────────────────────────────

    def get_user(self) -> Optional[User]:
        """Get current user info."""
        self._ensure_auth()
        info = fetch_user_info(self._cookies or {})
        if info:
            return User(
                id=info.get("email", ""),
                name=info.get("display_name", ""),
                avatar_url=info.get("avatar_url"),
            )
        return None


def _to_resource(project_id: str) -> str:
    """Convert a bare ID to resource name if needed."""
    if project_id.startswith("projects/"):
        return project_id
    return f"projects/{project_id}"


def _bare_id(project_id: str) -> str:
    """Extract bare ID from resource name."""
    if project_id.startswith("projects/"):
        return project_id[len("projects/"):]
    return project_id
