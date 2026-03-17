"""HTTP client for NotebookLM batchexecute API.

Thin wrapper that handles cookie injection, token management, and
request/response encoding via the rpc/ subpackage.
"""

import json
import time
import urllib.parse

import httpx

from cli_web.notebooklm.core.auth import (
    cookies_to_header,
    fetch_tokens,
    load_cookies,
)
from cli_web.notebooklm.core.rpc.decoder import decode_response, parse_rpc_result
from cli_web.notebooklm.core.rpc.encoder import build_query_params, encode_request
from cli_web.notebooklm.core.rpc.types import BATCHEXECUTE_URL, STREAMING_URL, RpcMethod


class NotebookLMClient:
    """Client for NotebookLM batchexecute API."""

    def __init__(self, cookies: list[dict] | None = None):
        self._cookies = cookies or load_cookies()
        if not self._cookies:
            raise RuntimeError(
                "No auth cookies found. Run: cli-web-notebooklm auth login"
            )
        self._tokens = None
        self._reqid = 100000
        self._http = httpx.Client(timeout=60, follow_redirects=True)

    def _ensure_tokens(self):
        """Lazy-load tokens on first API call."""
        if self._tokens is None:
            self._tokens = fetch_tokens(self._cookies)

    def _next_reqid(self) -> int:
        """Get and increment the request counter."""
        rid = self._reqid
        self._reqid += 100000
        return rid

    def _call_rpc(self, rpc_id: str, params, source_path: str = "/"):
        """Make a batchexecute RPC call.

        Args:
            rpc_id: The RPC method ID.
            params: The inner parameters (list or JSON string).
            source_path: The source-path query param.

        Returns:
            Parsed result from the RPC response.

        Raises:
            RuntimeError: On HTTP errors or missing data.
        """
        self._ensure_tokens()

        query = build_query_params(
            rpc_id=rpc_id,
            source_path=source_path,
            bl=self._tokens["bl"],
            fsid=self._tokens["fsid"],
            hl="en",
            reqid=self._next_reqid(),
        )

        body = encode_request(
            rpc_id=rpc_id,
            params=params,
            at_token=self._tokens["at"],
        )

        headers = {
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "x-same-domain": "1",
            "origin": "https://notebooklm.google.com",
            "referer": f"https://notebooklm.google.com{source_path}",
            "cookie": cookies_to_header(self._cookies),
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
        }

        resp = self._http.post(
            BATCHEXECUTE_URL,
            params=query,
            content=body,
            headers=headers,
        )

        if resp.status_code == 401 or resp.status_code == 403:
            # Try refreshing tokens once
            self._tokens = fetch_tokens(self._cookies)
            body = encode_request(rpc_id, params, self._tokens["at"])
            query["_reqid"] = str(self._next_reqid())
            resp = self._http.post(
                BATCHEXECUTE_URL,
                params=query,
                content=body,
                headers=headers,
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"batchexecute failed: HTTP {resp.status_code} for {rpc_id}"
            )

        envelopes = decode_response(resp.text)
        result = parse_rpc_result(envelopes, rpc_id)
        return result

    # ── Notebook Operations ─────────────────────────────────────────

    def list_notebooks(self):
        """List all user-owned notebooks."""
        params = json.dumps([None, 1, None, [2]], separators=(",", ":"))
        result = self._call_rpc(RpcMethod.LIST_NOTEBOOKS, params)
        # Response is [[nb1, nb2, ...]] — return inner list
        if result and isinstance(result, list) and result[0] and isinstance(result[0], list):
            return result[0]
        return []

    def list_shared_notebooks(self):
        """List shared/team notebooks."""
        params = json.dumps([[2]], separators=(",", ":"))
        result = self._call_rpc(RpcMethod.LIST_SHARED_NOTEBOOKS, params)
        if result and isinstance(result, list) and result[0] and isinstance(result[0], list):
            return result[0]
        return []

    def get_notebook(self, notebook_id: str):
        """Get details for a specific notebook."""
        params = json.dumps([notebook_id, None, [2], None, 0], separators=(",", ":"))
        result = self._call_rpc(
            RpcMethod.GET_NOTEBOOK,
            params,
            source_path=f"/notebook/{notebook_id}",
        )
        # Response is [[notebook_data]] — unwrap
        if result and isinstance(result, list) and result[0] and isinstance(result[0], list):
            return result[0]
        return result

    def get_user_quotas(self):
        """Get user account quotas."""
        params = json.dumps(
            [None, [1, None, None, None, None, None, None, None, None, None, [1]]],
            separators=(",", ":"),
        )
        return self._call_rpc(RpcMethod.GET_USER_QUOTAS, params)

    # ── Source Operations ───────────────────────────────────────────

    def list_sources(self, notebook_id: str):
        """List sources for a notebook (extracted from notebook data)."""
        nb = self.get_notebook(notebook_id)
        if nb and len(nb) > 1 and nb[1]:
            return nb[1]  # Sources array
        return []

    # ── Chat Operations ─────────────────────────────────────────────

    def get_chat_threads(self, notebook_id: str):
        """Get chat thread IDs for a notebook."""
        params = json.dumps([[], None, notebook_id, 20], separators=(",", ":"))
        return self._call_rpc(
            RpcMethod.GET_CHAT_THREADS,
            params,
            source_path=f"/notebook/{notebook_id}",
        )

    def get_chat_history(self, thread_id: str):
        """Get chat messages for a thread."""
        params = json.dumps([[], None, None, thread_id, 20], separators=(",", ":"))
        return self._call_rpc(RpcMethod.GET_CHAT_HISTORY, params)

    def get_summary(self, notebook_id: str):
        """Get notebook summary and suggested questions."""
        params = json.dumps([notebook_id, [2]], separators=(",", ":"))
        return self._call_rpc(
            RpcMethod.GET_SUMMARY,
            params,
            source_path=f"/notebook/{notebook_id}",
        )

    # ── Artifact Operations ─────────────────────────────────────────

    def list_artifacts(self, notebook_id: str):
        """List studio artifacts for a notebook."""
        params = json.dumps(
            [
                [2, None, None, [1, None, None, None, None, None, None, None, None, None, [1]], [[2, 1, 3]]],
                notebook_id,
                'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"',
            ],
            separators=(",", ":"),
        )
        return self._call_rpc(
            RpcMethod.LIST_ARTIFACTS,
            params,
            source_path=f"/notebook/{notebook_id}",
        )

    def get_artifact(self, notebook_id: str, artifact_id: str):
        """Get a specific artifact by ID from the artifacts list."""
        result = self.list_artifacts(notebook_id)
        if not result or not isinstance(result, list):
            return None
        artifacts = result[0] if isinstance(result[0], list) else result
        for art in artifacts:
            if isinstance(art, list) and len(art) > 0 and art[0] == artifact_id:
                return art
        return None

    def get_saved_notes(self, notebook_id: str):
        """Get saved chat notes for a notebook."""
        params = json.dumps([notebook_id, None, None, [2]], separators=(",", ":"))
        return self._call_rpc(
            RpcMethod.GET_SAVED_NOTES,
            params,
            source_path=f"/notebook/{notebook_id}",
        )

    # ── Sharing Operations ──────────────────────────────────────────

    def get_collaborators(self, notebook_id: str):
        """Get sharing info and collaborators for a notebook."""
        params = json.dumps([notebook_id, [2]], separators=(",", ":"))
        return self._call_rpc(
            RpcMethod.GET_COLLABORATORS,
            params,
            source_path=f"/notebook/{notebook_id}",
        )

    # ── Mutation Operations ────────────────────────────────────────

    def create_notebook(self):
        """Create a new empty notebook."""
        params = json.dumps(
            ["", None, None, [2], [1, None, None, None, None, None, None, None, None, None, [1]]],
            separators=(",", ":"),
        )
        return self._call_rpc(RpcMethod.CREATE_NOTEBOOK, params)

    def delete_notebook(self, notebook_id: str):
        """Delete a notebook."""
        params = json.dumps(
            [[notebook_id], [2]],
            separators=(",", ":"),
        )
        return self._call_rpc(RpcMethod.DELETE_NOTEBOOK, params)

    def add_text_source(self, notebook_id: str, title: str, text: str):
        """Add a pasted text source to a notebook."""
        params = json.dumps(
            [
                [[None, [title, text], None, 2, None, None, None, None, None, 1]],
                notebook_id,
                [2],
                [1, None, None, None, None, None, None, None, None, None, [1]],
            ],
            separators=(",", ":"),
        )
        return self._call_rpc(
            RpcMethod.ADD_TEXT_SOURCE,
            params,
            source_path=f"/notebook/{notebook_id}",
        )

    def ask_question(self, notebook_id: str, question: str, source_ids: list[str], thread_id: str):
        """Send a chat question via the streaming endpoint.

        Args:
            notebook_id: The notebook ID.
            question: The question text.
            source_ids: List of source IDs to include as context.
            thread_id: The chat thread ID.

        Returns:
            Dict with 'text' (the final answer) and 'thread_id'.
        """
        self._ensure_tokens()

        source_id_arrays = [[sid] for sid in source_ids]
        inner = json.dumps(
            [
                [source_id_arrays],
                question,
                None,
                [2, None, [1], [1]],
                thread_id,
                None,
                None,
                notebook_id,
                1,
            ],
            separators=(",", ":"),
        )

        f_req = json.dumps([None, inner], separators=(",", ":"))
        body = urllib.parse.urlencode(
            {"f.req": f_req, "at": self._tokens["at"], "": ""},
            quote_via=urllib.parse.quote,
        )

        query = {
            "bl": self._tokens["bl"],
            "f.sid": self._tokens["fsid"],
            "hl": "en",
            "_reqid": str(self._next_reqid()),
            "rt": "c",
        }

        headers = {
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "x-same-domain": "1",
            "x-goog-ext-353267353-jspb": "[null,null,null,282611]",
            "origin": "https://notebooklm.google.com",
            "referer": f"https://notebooklm.google.com/notebook/{notebook_id}",
            "cookie": cookies_to_header(self._cookies),
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
        }

        resp = self._http.post(
            STREAMING_URL,
            params=query,
            content=body,
            headers=headers,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Streaming request failed: HTTP {resp.status_code}"
            )

        # Decode streaming response — same )]}'  format with multiple chunks
        envelopes = decode_response(resp.text)

        # Extract text from the last chunk
        final_text = ""
        for envelope in reversed(envelopes):
            if not isinstance(envelope, list):
                continue
            for item in envelope:
                if not isinstance(item, list) or len(item) < 3:
                    continue
                if item[0] == "wrb.fr" and item[2]:
                    try:
                        inner_data = json.loads(item[2])
                        if isinstance(inner_data, list) and len(inner_data) > 0:
                            if isinstance(inner_data[0], list) and len(inner_data[0]) > 0:
                                final_text = inner_data[0][0]
                            else:
                                final_text = inner_data[0]
                        break
                    except (json.JSONDecodeError, TypeError, IndexError):
                        continue
            if final_text:
                break

        return {"text": final_text, "thread_id": thread_id}

    def create_artifact(self, notebook_id: str, source_ids: list[str], artifact_type: int = 1):
        """Create a studio artifact (audio, video, quiz, or presentation).

        Args:
            notebook_id: The notebook ID.
            source_ids: List of source IDs to include.
            artifact_type: 1=audio, 3=video, 4=quiz, 8=presentation.

        Returns:
            The RPC result.
        """
        source_id_arrays = [[sid] for sid in source_ids]
        params = json.dumps(
            [
                [2, None, None, [1, None, None, None, None, None, None, None, None, None, [1]], [[2, 1, 3]]],
                notebook_id,
                [
                    None,
                    None,
                    artifact_type,
                    [source_id_arrays],
                    None,
                    None,
                    [None, [None, None, None, [source_id_arrays]]],
                ],
            ],
            separators=(",", ":"),
        )
        return self._call_rpc(
            RpcMethod.CREATE_ARTIFACT,
            params,
            source_path=f"/notebook/{notebook_id}",
        )
