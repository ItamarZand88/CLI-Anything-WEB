"""HTTP client for NotebookLM batchexecute API."""
import json
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
from .rpc.types import RPCMethod, ArtifactType, BATCHEXECUTE_URL
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
            [notebook_id, None, [2], None, 0],
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

        Sources are embedded in rLM1Ne (GET_NOTEBOOK) response at result[0][1].
        """
        result = self._call(
            RPCMethod.GET_NOTEBOOK,
            [notebook_id, None, [2], None, 0],
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
        """Add a URL source to a notebook.

        Uses izAoDd (ADD_SOURCE) with correct param structure.
        """
        params = [
            [[None, None, [url], None, None, None, None, None]],
            notebook_id,
            [2],
            None,
            None,
        ]
        result = self._call(
            RPCMethod.ADD_SOURCE,
            params,
            source_path=f"/notebook/{notebook_id}",
        )
        # izAoDd returns source data — extract source ID
        source_id = _extract_source_id_from_add(result)
        if source_id:
            return Source(id=source_id, name=url, source_type="url", url=url)
        raise ServerError(f"Unexpected add-url response: {result}")

    def add_text_source(self, notebook_id: str, title: str, text: str) -> Source:
        """Add a plain-text source to a notebook.

        Uses izAoDd (ADD_SOURCE) with correct param structure.
        """
        params = [
            [[None, [title, text], None, None, None, None, None, None]],
            notebook_id,
            [2],
            None,
            None,
        ]
        result = self._call(
            RPCMethod.ADD_SOURCE,
            params,
            source_path=f"/notebook/{notebook_id}",
        )
        source_id = _extract_source_id_from_add(result)
        if source_id:
            return Source(id=source_id, name=title, source_type="text")
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

        Uses GenerateFreeFormStreamed endpoint.
        Returns the answer as a string.
        """
        self._ensure_auth()
        # Fetch source IDs to include in the request
        sources = self.list_sources(notebook_id)
        source_ids = [s.id for s in sources]

        # Build inner params matching the reference implementation
        sources_arr = [[[sid]] for sid in source_ids]
        inner = [sources_arr, query, None, [2, None, [1], [1]], None, None, None, notebook_id, 1]
        inner_json = json.dumps(inner, separators=(",", ":"))

        # Outer f.req: [null, inner_json_string]
        freq = json.dumps([None, inner_json], separators=(",", ":"))

        # URL-encode body parts with quote() for proper encoding
        body_parts = [f"f.req={urllib.parse.quote(freq, safe='')}"]
        if self._csrf:
            body_parts.append(f"at={urllib.parse.quote(self._csrf, safe='')}")
        body = "&".join(body_parts) + "&"

        req_id = self._session.next_req_id()
        url_params = urllib.parse.urlencode({
            "f.sid": self._session_id or "",
            "bl": self._build_label or "",
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
                content=body,
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

    def _get_source_ids(self, notebook_id: str) -> tuple[list, list]:
        """Get source IDs in both triple and double nested formats."""
        sources = self.list_sources(notebook_id)
        source_ids = [s.id for s in sources]
        triple = [[[sid]] for sid in source_ids] if source_ids else []
        double = [[sid] for sid in source_ids] if source_ids else []
        return triple, double

    def generate_artifact(
        self,
        notebook_id: str,
        artifact_type: int = ArtifactType.MIND_MAP,
        report_format: str = "briefing",
    ) -> Artifact:
        """Generate an artifact from a notebook.

        Supports all artifact types from NotebookLM:
        - audio (1), report (2), video (3), quiz (4), mindmap (5),
          infographic (7), slide_deck (8), data_table (9)

        Mind maps use GENERATE_MIND_MAP (yyryJe). All others use CREATE_ARTIFACT (R7cb6c).
        """
        type_names = {
            1: "audio", 2: "report", 3: "video", 4: "quiz",
            5: "mindmap", 7: "infographic", 8: "slide_deck", 9: "data_table",
        }
        type_name = type_names.get(artifact_type, "unknown")

        source_ids_triple, source_ids_double = self._get_source_ids(notebook_id)

        # Mind map uses a completely different RPC method
        if artifact_type == ArtifactType.MIND_MAP:
            return self._generate_mind_map(notebook_id, source_ids_triple)

        # Build params — each type has a unique structure
        params = self._build_artifact_params(
            notebook_id, artifact_type, source_ids_triple, source_ids_double, report_format
        )
        result = self._call(
            RPCMethod.CREATE_ARTIFACT,
            params,
            source_path=f"/notebook/{notebook_id}",
        )
        return _parse_generation_result(result, type_name)

    def _build_artifact_params(
        self, notebook_id: str, artifact_type: int,
        sids_triple: list, sids_double: list, report_format: str,
    ) -> list:
        """Build the full params array for CREATE_ARTIFACT (R7cb6c).

        Each artifact type has a unique inner structure at different array
        positions. These structures are reverse-engineered from traffic analysis.
        """
        if artifact_type == ArtifactType.AUDIO:
            return [
                [2], notebook_id,
                [None, None, 1, sids_triple, None, None,
                 [None, [None, None, None, sids_double, "en", None, None]]],
            ]

        if artifact_type == ArtifactType.REPORT:
            report_configs = {
                "briefing": ("Briefing Doc", "Key insights and important quotes",
                    "Create a comprehensive briefing document that includes an "
                    "Executive Summary, detailed analysis of key themes, important "
                    "quotes with context, and actionable insights."),
                "study-guide": ("Study Guide", "Short-answer quiz, essay questions, glossary",
                    "Create a comprehensive study guide that includes key concepts, "
                    "short-answer practice questions, essay prompts for deeper "
                    "exploration, and a glossary of important terms."),
                "blog-post": ("Blog Post", "Insightful takeaways in readable article format",
                    "Write an engaging blog post that presents the key insights "
                    "in an accessible, reader-friendly format."),
            }
            title, desc, prompt = report_configs.get(report_format, report_configs["briefing"])
            return [
                [2], notebook_id,
                [None, None, 2, sids_triple, None, None, None,
                 [None, [title, desc, None, sids_double, "en", prompt, None, True]]],
            ]

        if artifact_type == ArtifactType.VIDEO:
            return [
                [2], notebook_id,
                [None, None, 3, sids_triple, None, None, None, None,
                 [None, None, [sids_double, "en", None, None, None, None]]],
            ]

        if artifact_type == ArtifactType.QUIZ:
            return [
                [2], notebook_id,
                [None, None, 4, sids_triple, None, None, None, None, None,
                 [None, [2, None, None, None, None, None, None, [None, None]]]],
            ]

        if artifact_type == ArtifactType.INFOGRAPHIC:
            return [
                [2], notebook_id,
                [None, None, 7, sids_triple, None, None, None, None, None,
                 None, None, None, None, None,
                 [[None, "en", None, None, None, None]]],
            ]

        if artifact_type == ArtifactType.SLIDE_DECK:
            return [
                [2], notebook_id,
                [None, None, 8, sids_triple, None, None, None, None, None,
                 None, None, None, None, None, None, None,
                 [[None, "en", None, None]]],
            ]

        if artifact_type == ArtifactType.DATA_TABLE:
            return [
                [2], notebook_id,
                [None, None, 9, sids_triple, None, None, None, None, None,
                 None, None, None, None, None, None, None, None, None,
                 [None, [None, "en"]]],
            ]

        # Fallback for unknown types
        return [[2], notebook_id, [None, None, artifact_type, sids_triple]]

    def _generate_mind_map(self, notebook_id: str, source_ids_triple: list) -> Artifact:
        """Generate a mind map using GENERATE_MIND_MAP (yyryJe) RPC.

        Mind maps use the chat/query RPC with a special prompt structure,
        not CREATE_ARTIFACT.
        """
        params = [
            source_ids_triple,
            None, None, None, None,
            ["interactive_mindmap", [["[CONTEXT]", ""]], ""],
            None,
            [2, None, [1]],
        ]
        result = self._call(
            RPCMethod.CHAT_QUERY,
            params,
            source_path=f"/notebook/{notebook_id}",
        )
        if result and isinstance(result, list) and len(result) > 0:
            inner = result[0]
            if isinstance(inner, list) and len(inner) > 0:
                content = inner[0] if isinstance(inner[0], str) else json.dumps(inner[0])
                return Artifact(id="", artifact_type="mindmap", content=content)
        return Artifact(id="", artifact_type="mindmap", content="Mind map generation triggered")

    def list_artifacts(self, notebook_id: str) -> list[dict]:
        """List all artifacts in a notebook with their status."""
        params = [[2], notebook_id, 'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"']
        result = self._call(
            RPCMethod.LIST_ARTIFACTS,
            params,
            source_path=f"/notebook/{notebook_id}",
        )
        if not result or not isinstance(result, list):
            return []
        artifacts_data = result[0] if isinstance(result[0], list) else result
        artifacts = []
        status_names = {1: "in_progress", 2: "pending", 3: "completed", 4: "failed"}
        type_names = {1: "audio", 2: "report", 3: "video", 4: "quiz",
                      5: "mindmap", 7: "infographic", 8: "slide_deck", 9: "data_table"}
        for art in artifacts_data:
            if not isinstance(art, list) or len(art) < 1:
                continue
            art_id = art[0] if len(art) > 0 else ""
            art_type = type_names.get(art[2], "unknown") if len(art) > 2 else "unknown"
            status = status_names.get(art[4], "unknown") if len(art) > 4 else "unknown"
            title = art[1] if len(art) > 1 and isinstance(art[1], str) else ""
            artifacts.append({"id": art_id, "type": art_type, "title": title, "status": status})
        return artifacts

    def poll_artifact_status(self, notebook_id: str, artifact_id: str) -> dict:
        """Poll the status of a specific artifact."""
        all_artifacts = self.list_artifacts(notebook_id)
        for art in all_artifacts:
            if art["id"] == artifact_id:
                return art
        return {"id": artifact_id, "status": "pending"}

    def _list_artifacts_raw(self, notebook_id: str) -> list:
        """Get raw artifact list data for download parsing."""
        params = [[2], notebook_id, 'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"']
        result = self._call(
            RPCMethod.LIST_ARTIFACTS, params,
            source_path=f"/notebook/{notebook_id}",
        )
        if result and isinstance(result, list) and len(result) > 0:
            return result[0] if isinstance(result[0], list) else result
        return []

    def download_artifact(self, notebook_id: str, artifact_id: str, output_path: str) -> str:
        """Download a completed artifact to a file.

        Supports: report (md), audio (mp4), video (mp4), infographic (png),
        slide_deck (pdf), data_table (csv), quiz (json), mind_map (json).

        Returns the output path on success.
        """
        from pathlib import Path
        import csv

        raw = self._list_artifacts_raw(notebook_id)
        art = None
        for a in raw:
            if isinstance(a, list) and len(a) > 0 and a[0] == artifact_id:
                art = a
                break
        if not art:
            raise NotFoundError(f"Artifact {artifact_id} not found")

        art_type = art[2] if len(art) > 2 else 0
        status = art[4] if len(art) > 4 else 0
        if status != 3:  # 3 = completed
            raise ServerError(f"Artifact not completed (status={status}). Wait and retry.")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Report — markdown content at art[7][0]
        if art_type == 2:
            content = art[7][0] if len(art) > 7 and isinstance(art[7], list) and art[7] else ""
            if not isinstance(content, str):
                content = str(content)
            out.write_text(content, encoding="utf-8")
            return str(out)

        # Audio — URL at art[6][5][0][0]
        if art_type == 1:
            url = art[6][5][0][0] if (len(art) > 6 and isinstance(art[6], list)
                                      and len(art[6]) > 5 and isinstance(art[6][5], list)
                                      and art[6][5] and isinstance(art[6][5][0], list)) else None
            if not url:
                raise ServerError("Audio URL not found in artifact data")
            return self._download_url(url, out)

        # Video — URL at art[8], scan for first HTTP string
        if art_type == 3:
            url = None
            if len(art) > 8 and isinstance(art[8], list):
                for item in art[8]:
                    if isinstance(item, str) and item.startswith("http"):
                        url = item
                        break
            if not url:
                raise ServerError("Video URL not found in artifact data")
            return self._download_url(url, out)

        # Infographic — scan reversed entries for URL
        if art_type == 7:
            url = None
            for item in reversed(art):
                if isinstance(item, list):
                    for sub in item:
                        if isinstance(sub, list) and len(sub) > 2 and isinstance(sub[2], list):
                            for candidate in sub[2]:
                                if isinstance(candidate, str) and candidate.startswith("http"):
                                    url = candidate
                                    break
                        if url:
                            break
                if url:
                    break
            if not url:
                raise ServerError("Infographic URL not found in artifact data")
            return self._download_url(url, out)

        # Slide deck — PDF/PPTX URLs are at the end of art[16]
        if art_type == 8:
            url = None
            if len(art) > 16 and isinstance(art[16], list):
                ext = str(out).lower()
                # Scan art[16] for download URLs
                for item in art[16]:
                    if isinstance(item, str) and item.startswith("http"):
                        if ".pptx" in ext and "pptx" in item:
                            url = item
                            break
                        elif ".pdf" in ext and "pdf" in item.lower():
                            url = item
                            break
                        elif not url:
                            url = item  # First URL as fallback
            if not url:
                raise ServerError("Slide deck URL not found in artifact data")
            return self._download_url(url, out)

        # Data table — complex nested structure at art[18]
        if art_type == 9:
            if len(art) > 18:
                raw_data = art[18]
                # Parse using the same approach as the reference implementation
                # Structure: raw_data[0][0][0][0][4][2] = rows array
                headers, rows = _parse_data_table(raw_data)
                with out.open("w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    if headers:
                        writer.writerow(headers)
                    writer.writerows(rows)
                return str(out)
            raise ServerError("Data table content not found")

        # Quiz/Flashcards — fetch interactive HTML, extract app data
        if art_type == 4:
            result = self._call(
                "v9rmvd",  # GET_INTERACTIVE_HTML
                [artifact_id],
                source_path=f"/notebook/{notebook_id}",
            )
            # Response: result[0][9][0] = HTML content with embedded quiz data
            html_content = None
            if result and isinstance(result, list) and len(result) > 0:
                data = result[0]
                if isinstance(data, list) and len(data) > 9 and data[9]:
                    html_content = data[9][0] if isinstance(data[9], list) and data[9] else data[9]
            if html_content and isinstance(html_content, str):
                # Extract JSON from data-app-data attribute
                import re
                m = re.search(r'data-app-data="([^"]*)"', html_content)
                if m:
                    import html as html_mod
                    app_data = html_mod.unescape(m.group(1))
                    out.write_text(app_data, encoding="utf-8")
                else:
                    out.write_text(html_content, encoding="utf-8")
            else:
                out.write_text(json.dumps(result, indent=2, ensure_ascii=False) if result else "{}", encoding="utf-8")
            return str(out)

        raise ServerError(f"Download not supported for artifact type {art_type}")

    def _download_url(self, url: str, output_path) -> str:
        """Download a URL to a file using domain-aware cookies.

        Media downloads go to usercontent.google.com which needs cookies with
        proper domain info — the flat dict approach doesn't work for cross-domain.
        """
        from .auth import AUTH_DIR
        state_file = AUTH_DIR / "playwright-state.json"
        cookies = httpx.Cookies()

        if state_file.exists():
            state = json.loads(state_file.read_text(encoding="utf-8"))
            for c in state.get("cookies", []):
                domain = c.get("domain", "")
                name = c.get("name", "")
                value = c.get("value", "")
                if ("google" in domain or "usercontent" in domain) and name and value:
                    cookies.set(name, value, domain=domain)
        else:
            # Fallback to flat cookies
            self._ensure_auth()
            for k, v in (self._cookies or {}).items():
                cookies.set(k, v)

        resp = httpx.get(
            url,
            cookies=cookies,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            follow_redirects=True,
            timeout=120.0,
        )
        if resp.status_code != 200:
            raise ServerError(f"Download failed: HTTP {resp.status_code}")
        output_path.write_bytes(resp.content)
        return str(output_path)

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


def _parse_generation_result(result, type_name: str) -> Artifact:
    """Parse CREATE_ARTIFACT (R7cb6c) response into an Artifact.

    Response structure: [[artifact_id, title, date?, None, status_code], ...]
    The artifact data is at result[0].
    """
    if not result or not isinstance(result, list):
        return Artifact(id="", artifact_type=type_name, content="Generation triggered — check artifacts list")

    # Result is nested: result[0] is the artifact data array
    artifact_data = result[0] if isinstance(result[0], list) else result
    artifact_id = artifact_data[0] if len(artifact_data) > 0 else ""
    status_code = artifact_data[4] if len(artifact_data) > 4 else None

    status_names = {1: "in_progress", 2: "pending", 3: "completed", 4: "failed"}
    status = status_names.get(status_code, "pending") if status_code else "pending"

    if artifact_id:
        return Artifact(
            id=str(artifact_id),
            artifact_type=type_name,
            content=f"Generation {status} (artifact_id={artifact_id})",
        )

    return Artifact(id="", artifact_type=type_name, content="Generation triggered — check artifacts list")


def _extract_source_id_from_add(result) -> Optional[str]:
    """Extract source ID from an izAoDd (ADD_SOURCE) response.

    The response structure varies but typically contains the source ID
    nested inside arrays. Try common patterns.
    """
    if not result or not isinstance(result, list):
        return None
    try:
        # Pattern 1: [[source_id, ...], ...]
        if isinstance(result[0], list) and len(result[0]) > 0:
            candidate = result[0][0]
            if isinstance(candidate, str):
                return candidate
            # Pattern 2: [[[source_id]], ...]
            if isinstance(candidate, list) and len(candidate) > 0:
                if isinstance(candidate[0], str):
                    return candidate[0]
                if isinstance(candidate[0], list) and len(candidate[0]) > 0:
                    return str(candidate[0][0])
        # Pattern 3: [source_id, ...]
        if isinstance(result[0], str):
            return result[0]
    except (IndexError, TypeError):
        pass
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

    The response uses the batchexecute chunked format with )]}' prefix.
    Each chunk contains wrb.fr entries where item[2] is a JSON string with
    the answer at inner_data[0][0].

    Each chunk contains wrb.fr entries where item[2] is a JSON string with
    the answer at inner_data[0][0].
    """
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="replace")
    else:
        text = data

    # Strip anti-XSSI prefix
    if text.startswith(")]}'"):
        text = text[4:].lstrip("\n")

    # Parse chunked response: alternating length-hint lines and JSON lines
    lines = text.strip().split("\n")
    best_answer = ""

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Try as length-hint number line
        try:
            int(line)
            i += 1
            if i < len(lines):
                answer = _extract_answer_from_chunk(lines[i])
                if answer and len(answer) > len(best_answer):
                    best_answer = answer
            i += 1
        except ValueError:
            # Not a number — try as JSON directly
            answer = _extract_answer_from_chunk(line)
            if answer and len(answer) > len(best_answer):
                best_answer = answer
            i += 1

    return best_answer


def _extract_answer_from_chunk(json_str: str) -> Optional[str]:
    """Extract answer text from a single wrb.fr response chunk.

    Structure: [[wrb.fr, rpc_id, inner_json_string, ...]]
    inner_json parses to: [[answer_text, null, [conv_id, ...], ...]]
    """
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(data, list):
        return None

    for item in data:
        if not isinstance(item, list) or len(item) < 3:
            continue
        if item[0] != "wrb.fr":
            continue

        inner_json = item[2]
        if not isinstance(inner_json, str):
            continue

        try:
            inner_data = json.loads(inner_json)
            if isinstance(inner_data, list) and len(inner_data) > 0:
                first = inner_data[0]
                if isinstance(first, list) and len(first) > 0:
                    text = first[0]
                    if isinstance(text, str) and text:
                        return text
        except (json.JSONDecodeError, ValueError):
            continue

    return None


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


def _extract_cell_text(cell) -> str:
    """Recursively extract text from a nested data table cell."""
    if isinstance(cell, str):
        return cell
    if isinstance(cell, int):
        return ""
    if isinstance(cell, list):
        return "".join(text for item in cell if (text := _extract_cell_text(item)))
    return ""


def _parse_data_table(raw_data) -> tuple:
    """Parse rich-text data table into (headers, rows).

    Data tables have deeply nested structure:
    raw_data[0][0][0][0][4][2] = rows array
    Each row: [start_pos, end_pos, [cell_array]]
    """
    try:
        rows_array = raw_data[0][0][0][0][4][2]
        if not rows_array:
            return [], []

        headers = []
        rows = []
        for i, row_section in enumerate(rows_array):
            if not isinstance(row_section, list) or len(row_section) < 3:
                continue
            cell_array = row_section[2]
            if not isinstance(cell_array, list):
                continue
            row_values = [_extract_cell_text(cell) for cell in cell_array]
            if i == 0:
                headers = row_values
            else:
                rows.append(row_values)
        return headers, rows
    except (IndexError, TypeError, KeyError):
        return [], []
