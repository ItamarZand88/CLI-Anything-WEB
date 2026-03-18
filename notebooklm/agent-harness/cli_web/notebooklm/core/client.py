"""HTTP client for NotebookLM batchexecute API."""
import json
import time
import urllib.parse
from typing import Any, Optional

import httpx

from .auth import fetch_tokens, fetch_user_info, load_cookies
from .exceptions import (
    AuthError, NetworkError, RateLimitError, ServerError, NotFoundError, RPCError,
    NotebookLMError,
)
from .models import (
    Notebook, Source, User, Artifact,
    parse_notebook, parse_source, parse_user,
)
from .rpc import encode_request, build_url, decode_response
from .rpc.decoder import strip_prefix, parse_chunks
from .rpc.types import RPCMethod, ArtifactType
from .session import get_session

BASE_URL = "https://notebooklm.google.com"
GRPC_BASE = (
    "https://notebooklm.google.com/_/LabsTailwindUi/data/"
    "google.internal.labs.tailwind.orchestration.v1"
    ".LabsTailwindOrchestrationService"
)


class NotebookLMClient:
    """Client for the NotebookLM batchexecute API.

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
        """Execute a batchexecute RPC call.

        Args:
            rpc_id: The RPC method identifier
            params: Method parameters
            source_path: URL context path for the request
            retry_on_auth: If True, refresh tokens and retry once on auth error

        Returns:
            Decoded result from the response

        Raises:
            AuthError: If auth fails even after refresh
            httpx.HTTPError: On network errors
        """
        self._ensure_auth()

        req_id = self._session.next_req_id()
        url = build_url(
            rpc_id=rpc_id,
            session_id=self._session_id,
            build_label=self._build_label,
            source_path=source_path,
            req_id=req_id,
        )
        body = encode_request(rpc_id, params, self._csrf)
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
            raise NotebookLMError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        return decode_response(resp.content, rpc_id)

    # ── Notebooks ─────────────────────────────────────────────────────────────

    def list_notebooks(self) -> list[Notebook]:
        """List all notebooks."""
        result = self._call(RPCMethod.LIST_NOTEBOOKS, [None, 1, None, [2]])
        if not result or not isinstance(result, list):
            return []
        notebooks = []
        entries = result[0] if isinstance(result[0], list) else result
        for raw in entries:
            nb = _parse_notebook_content_entry(raw)
            if nb:
                notebooks.append(nb)
        return notebooks

    def create_notebook(self, title: str, emoji: str = "📓") -> Notebook:
        """Create a new notebook."""
        result = self._call(RPCMethod.CREATE_NOTEBOOK, [title])
        if not result:
            raise ServerError("No response from create notebook")
        nb = _parse_create_response(result)
        if not nb:
            raise ServerError(f"Could not parse create response: {result}")
        # Inject the known title and emoji since create response omits them
        nb.title = title
        nb.emoji = emoji
        return nb

    def get_notebook(self, notebook_id: str) -> Notebook:
        """Get notebook details by ID."""
        result = self._call(
            RPCMethod.GET_NOTEBOOK,
            [notebook_id],
            source_path=f"/notebook/{notebook_id}",
        )
        if not result or not isinstance(result, list):
            raise NotFoundError(f"Notebook {notebook_id!r} not found")
        # rLM1Ne returns [[header_array, ...]]
        entries = result[0] if isinstance(result[0], list) else result
        nb = parse_notebook(entries)
        if not nb:
            raise ServerError(f"Could not parse notebook response for {notebook_id!r}")
        return nb

    def rename_notebook(self, notebook_id: str, new_title: str = "", title: str = "") -> Notebook:
        new_title = new_title or title
        """Rename a notebook."""
        result = self._call(
            RPCMethod.RENAME_NOTEBOOK,
            [None, None, notebook_id, new_title],
            source_path=f"/notebook/{notebook_id}",
        )
        if not result:
            raise ServerError("No response from rename notebook")
        # s0tc2d returns the updated notebook as a flat array
        nb = parse_notebook(result if isinstance(result, list) else [result])
        if not nb:
            nb = Notebook(id=notebook_id, title=new_title)
        return nb

    def delete_notebook(self, notebook_id: str):
        """Delete a notebook."""
        self._call(
            RPCMethod.DELETE_NOTEBOOK,
            [None, None, notebook_id],
            source_path=f"/notebook/{notebook_id}",
        )

    # ── Sources ───────────────────────────────────────────────────────────────

    def list_sources(self, notebook_id: str) -> list[Source]:
        """List all sources in a notebook (extracted from get_notebook response).

        izAoDd is deprecated/inaccessible; sources are embedded in rLM1Ne response.
        """
        result = self._call(
            RPCMethod.GET_NOTEBOOK,
            [notebook_id],
            source_path=f"/notebook/{notebook_id}",
        )
        if not result or not isinstance(result, list):
            return []
        raw_sources = _extract_sources_from_nb_result(result)
        sources = []
        for raw in raw_sources:
            if isinstance(raw, list):
                src = parse_source(raw)
                if src:
                    sources.append(src)
        return sources

    def add_url_source(self, notebook_id: str, url: str) -> Source:
        """Add a URL source to a notebook."""
        result = self._call(
            RPCMethod.ADD_URL_SOURCE,
            [notebook_id, [url]],
            source_path=f"/notebook/{notebook_id}",
        )
        # VfAZjd returns [null, "source_id"]
        if result and isinstance(result, list) and len(result) > 1:
            source_id = result[1]
            time.sleep(1)  # Brief delay for source to be indexed
            return Source(id=source_id, name=url, source_type="url", url=url)
        raise ServerError(f"Unexpected add-url response: {result}")

    def add_text_source(self, notebook_id: str, title: str, text: str) -> Source:
        """Add a plain-text source to a notebook."""
        result = self._call(
            RPCMethod.ADD_TEXT_SOURCE,
            [None, None, notebook_id, title, text],
            source_path=f"/notebook/{notebook_id}",
        )
        # hPTbtc returns [[[source_id]]]
        if result and isinstance(result, list):
            try:
                source_id = result[0][0][0]
                return Source(id=source_id, name=title, source_type="text")
            except (IndexError, TypeError):
                pass
        raise ServerError(f"Unexpected add-text response: {result}")

    def get_source(self, notebook_id: str, source_id: str) -> Source:
        """Get source details."""
        result = self._call(
            RPCMethod.GET_SOURCE,
            [None, None, source_id, notebook_id],
            source_path=f"/notebook/{notebook_id}",
        )
        if not result or not isinstance(result, list):
            raise NotFoundError(f"Source {source_id!r} not found")
        src = parse_source(result)
        if not src:
            raise ServerError("Could not parse source response")
        return src

    def delete_source(self, notebook_id: str, source_id: str):
        """Delete a source from a notebook."""
        self._call(
            RPCMethod.DELETE_SOURCE,
            [None, None, notebook_id, [source_id]],
            source_path=f"/notebook/{notebook_id}",
        )

    # ── Chat ──────────────────────────────────────────────────────────────────

    # Aliases for command module compatibility
    def add_source_url(self, notebook_id: str, url: str) -> Source:
        return self.add_url_source(notebook_id, url)

    def add_source_text(self, notebook_id: str, title: str, text: str) -> Source:
        return self.add_text_source(notebook_id, title, text)

    def ask(self, notebook_id: str, query: str) -> str:
        return self.chat_query(notebook_id, query)

    def chat_query(self, notebook_id: str, query: str) -> str:
        """Ask a question to a notebook.

        Uses GenerateFreeFormStreamed endpoint (NotebookLM migrated from yyryJe).
        Returns the answer as a string.
        """
        self._ensure_auth()
        # Fetch source IDs to include in the request
        sources = self.list_sources(notebook_id)
        source_ids = [s.id for s in sources]

        # Build inner JSON: [[["id1"]], [["id2"]], ...], "query", []
        sources_arr = [[[sid]] for sid in source_ids]
        inner = [sources_arr, query, []]
        inner_json = json.dumps(inner, separators=(",", ":"))

        # Outer f.req: [null, inner_json_string]
        freq = json.dumps([None, inner_json], separators=(",", ":"))
        body = urllib.parse.urlencode({"f.req": freq, "at": self._csrf})

        req_id = self._session.next_req_id()
        url_params = urllib.parse.urlencode({
            "f.sid": self._session_id,
            "bl": self._build_label,
            "hl": "en",
            "_reqid": str(req_id),
            "rt": "c",
        })
        url = f"{GRPC_BASE}/GenerateFreeFormStreamed?{url_params}"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "x-same-domain": "1",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/notebook/{notebook_id}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            resp = httpx.post(
                url,
                content=body.encode("utf-8"),
                headers=headers,
                cookies=self._cookies,
                follow_redirects=False,
                timeout=60.0,
            )
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}")
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}")
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}")

        if resp.status_code in (401, 403):
            self._refresh_tokens()
            return self.chat_query(notebook_id, query)

        if resp.status_code == 429:
            raise RateLimitError("Rate limited — please wait and try again")

        if resp.status_code >= 500:
            raise ServerError(f"HTTP {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)

        if resp.status_code >= 400:
            raise NotebookLMError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        return _parse_streaming_chat(resp.content)

    # ── Artifacts ─────────────────────────────────────────────────────────────

    def generate_artifact(self, notebook_id: str, artifact_type: int = ArtifactType.MIND_MAP) -> Artifact:
        """Generate a structured artifact from a notebook.

        Uses the unified CREATE_ARTIFACT (R7cb6c) RPC method.
        artifact_type: ArtifactType.AUDIO (1), REPORT/STUDY_GUIDE (2), VIDEO (3),
                       QUIZ (4), MIND_MAP (5), INFOGRAPHIC (7), SLIDE_DECK (8), DATA_TABLE (9)

        The param structure matches notebooklm-py's _call_generate pattern:
        [[2], notebook_id, [None, None, type_code, source_ids, ...]]
        """
        # Get source IDs — the API requires them for artifact generation
        sources = self.list_sources(notebook_id)
        source_ids = [s.id for s in sources]
        source_ids_triple = [[[sid]] for sid in source_ids] if source_ids else []

        params = [
            [2],
            notebook_id,
            [
                None,
                None,
                artifact_type,
                source_ids_triple,
            ],
        ]
        result = self._call(
            RPCMethod.CREATE_ARTIFACT,
            params,
            source_path=f"/notebook/{notebook_id}",
        )
        # R7cb6c returns [artifact_id, title, date?, null, status_code] or None
        type_names = {
            1: "audio", 2: "report", 3: "video", 4: "quiz",
            5: "mindmap", 7: "infographic", 8: "slide_deck", 9: "data_table",
        }
        type_name = type_names.get(artifact_type, "unknown")

        if not result or not isinstance(result, list):
            # Null result can mean generation was triggered async
            return Artifact(id="", artifact_type=type_name, content="Generation triggered — check artifacts list")

        artifact_id = result[0] if len(result) > 0 else ""
        content = result[1] if len(result) > 1 else ""
        return Artifact(id=str(artifact_id), artifact_type=type_name, content=str(content))

    def generate_notes(self, notebook_id: str, notes_type: int = 1) -> Artifact:
        """Generate study notes/report from a notebook."""
        result = self._call(
            RPCMethod.NOTES_ARTIFACT,
            [None, None, notebook_id, notes_type],
            source_path=f"/notebook/{notebook_id}",
        )
        if not result or not isinstance(result, list):
            raise ServerError("No notes response received")
        # ciyUvf returns [[[title, summary, null, [source_ids], prompt, ...]]]
        try:
            entry = result[0][0]
            title = entry[0] if entry else "Notes"
            content = entry[1] if len(entry) > 1 else ""
            return Artifact(id="", artifact_type="notes", content=content, title=title)
        except (IndexError, TypeError):
            return Artifact(id="", artifact_type="notes", content=str(result))

    def list_audio_types(self, notebook_id: str) -> list[dict]:
        """List available audio overview types."""
        result = self._call(
            RPCMethod.LIST_AUDIO_TYPES,
            [None, None, notebook_id],
            source_path=f"/notebook/{notebook_id}",
        )
        if not result or not isinstance(result, list):
            return []
        # sqTeoe returns [[[[type_id, name, description], ...]]]
        types = []
        try:
            for entry in result[0][0]:
                types.append({
                    "id": entry[0] if len(entry) > 0 else "",
                    "name": entry[1] if len(entry) > 1 else "",
                    "description": entry[2] if len(entry) > 2 else "",
                })
        except (IndexError, TypeError):
            pass
        return types

    # ── User Info ─────────────────────────────────────────────────────────────

    def get_user(self) -> User:
        """Get current user information from the homepage (JFMDGd is non-functional)."""
        self._ensure_auth()
        info = fetch_user_info(self._cookies)
        return User(
            email=info["email"],
            display_name=info.get("display_name", ""),
            avatar_url=info.get("avatar_url"),
        )


# ── Private helpers ────────────────────────────────────────────────────────────

def _parse_notebook_content_entry(raw) -> Optional[Notebook]:
    """Parse a notebook from a wXbhsf list entry.

    wXbhsf returns a flat list. Each notebook "content entry" is:
    [title, [[sources...]], notebook_uuid, emoji, null, [flags...], ...]

    Entries starting with "" are metadata/cursor entries (not notebooks).
    """
    if not raw or not isinstance(raw, list):
        return None
    # Skip header/cursor entries (start with empty string and have UUID at [2])
    if not raw[0] or not isinstance(raw[0], str):
        return None
    if raw[0] == "":
        return None  # metadata entry, not a notebook
    try:
        title = raw[0]
        sources = raw[1] if len(raw) > 1 and isinstance(raw[1], list) else []
        nb_id = raw[2] if len(raw) > 2 and isinstance(raw[2], str) else None
        if not nb_id:
            return None

        emoji = raw[3] if len(raw) > 3 and isinstance(raw[3], str) and raw[3] else "📓"
        flags = raw[5] if len(raw) > 5 and isinstance(raw[5], list) else []
        is_pinned = bool(flags[0]) if flags else False
        created_sec = flags[5][0] if (len(flags) > 5 and isinstance(flags[5], list)) else None
        updated_sec = flags[8][0] if (len(flags) > 8 and isinstance(flags[8], list)) else None

        return Notebook(
            id=nb_id,
            title=title or "(untitled)",
            emoji=emoji,
            created_at=created_sec,
            updated_at=updated_sec,
            source_count=len(sources),
            is_pinned=is_pinned,
        )
    except (IndexError, TypeError):
        return None


def _extract_sources_from_nb_result(result: list) -> list:
    """Extract the sources list embedded in an rLM1Ne (get_notebook) response.

    rLM1Ne decode structure: [[title, sources_list, nb_id, ...]]
    Sources are directly at result[0][1].
    """
    try:
        entries = result[0] if isinstance(result[0], list) else result
        if len(entries) > 1 and isinstance(entries[1], list):
            return entries[1]
    except (IndexError, TypeError):
        pass
    return []


def _parse_streaming_chat(data: "str | bytes") -> str:
    """Parse the GenerateFreeFormStreamed response and extract the answer text.

    The response uses the same batchexecute chunked format with )]}' prefix.
    Extracts the first non-empty text content found in the response.
    """
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="replace")
    else:
        text = data

    # Strip anti-XSSI prefix
    if text.startswith(")]}'"):
        text = text[4:].lstrip("\n")

    # Try to parse all JSON chunks and find text content
    decoder = json.JSONDecoder()
    pos = 0
    answer_parts = []

    while pos < len(text):
        ch = text[pos]
        if ch in " \t\r\n":
            pos += 1
            continue
        if ch.isdigit():
            while pos < len(text) and text[pos] != "\n":
                pos += 1
            continue
        if ch == "[":
            try:
                chunk, end = decoder.raw_decode(text, pos)
                pos = end
                # Look for answer text in the chunk structure
                _collect_answer_text(chunk, answer_parts)
                continue
            except json.JSONDecodeError:
                pass
        pos += 1

    if answer_parts:
        return "".join(answer_parts)

    # Fallback: return raw truncated text for debugging
    return text[:500] if len(text) > 500 else text


def _collect_answer_text(obj, parts: list, depth: int = 0) -> None:
    """Recursively search a parsed JSON structure for answer text strings."""
    if depth > 10:
        return
    if isinstance(obj, str):
        # Try to parse as nested JSON first (GenerateFreeFormStreamed double-encodes)
        stripped = obj.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                inner = json.loads(stripped)
                _collect_answer_text(inner, parts, depth + 1)
                return
            except (json.JSONDecodeError, ValueError):
                pass
        # Keep substantive non-URL text
        if len(obj) > 20 and not obj.startswith("http"):
            parts.append(obj)
        return
    if isinstance(obj, list):
        for item in obj:
            if parts:  # stop after first answer found
                return
            _collect_answer_text(item, parts, depth + 1)


def _parse_create_response(result) -> Optional[Notebook]:
    """Parse notebook from CCqFvf (create) response.

    Structure: ["", null, uuid, null, null, [flags...], ...]
    """
    if not result or not isinstance(result, list):
        return None
    try:
        nb_id = result[2] if len(result) > 2 else None
        if not nb_id:
            return None
        flags = result[5] if len(result) > 5 else []
        return Notebook(id=nb_id, title="", emoji="📓", is_pinned=False)
    except (IndexError, TypeError):
        return None
