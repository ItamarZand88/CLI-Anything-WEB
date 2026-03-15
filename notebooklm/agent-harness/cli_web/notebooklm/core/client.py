"""HTTP client for Google's batchexecute RPC protocol used by NotebookLM."""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

import requests

from cli_web.notebooklm.core.auth import load_cookies, build_cookie_header
from cli_web.notebooklm.core.session import (
    SessionParams,
    extract_session_params,
    save_session,
    load_session,
)

BASE_URL = "https://notebooklm.google.com"
BATCHEXECUTE_PATH = "/_/LabsTailwindUi/data/batchexecute"
STREAM_PATH = (
    "/_/LabsTailwindUi/data/"
    "google.internal.labs.tailwind.orchestration.v1."
    "LabsTailwindOrchestrationService/GenerateFreeFormStreamed"
)

# Incremented per-request within a session
_reqid_counter = 100000


def _next_reqid() -> int:
    """Return an incrementing request ID."""
    global _reqid_counter
    _reqid_counter += 1
    return _reqid_counter


class NotebookLMClient:
    """Low-level HTTP client for NotebookLM's batchexecute API."""

    def __init__(self, cookies: dict[str, str] | None = None):
        """Initialize client.

        Args:
            cookies: Dict of Google auth cookies. If None, loads from disk.
        """
        self.cookies = cookies or load_cookies()
        self.session_params: SessionParams | None = None
        self._http = requests.Session()
        self._http.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
        })
        self._http.headers["Cookie"] = build_cookie_header(self.cookies)

    # ── Session bootstrapping ──────────────────────────────────────────

    def ensure_session(self) -> SessionParams:
        """Ensure we have valid session params (CSRF, sid, bl).

        Tries cached session first, then fetches from the page.
        """
        if self.session_params:
            return self.session_params

        # Try disk cache
        cached = load_session()
        if cached:
            self.session_params = cached
            return cached

        return self.refresh_session()

    def refresh_session(self) -> SessionParams:
        """Fetch the main page and extract session parameters."""
        resp = self._http.get(f"{BASE_URL}/", allow_redirects=True)
        resp.raise_for_status()
        params = extract_session_params(resp.text)
        self.session_params = params
        save_session(params)
        return params

    # ── Core batchexecute call ─────────────────────────────────────────

    def rpc(
        self,
        rpc_id: str,
        payload: Any,
        source_path: str = "/",
    ) -> Any:
        """Make a batchexecute RPC call.

        Args:
            rpc_id: The RPC function ID (e.g. "wXbhsf").
            payload: Python object to serialize as the RPC payload.
            source_path: The source-path query parameter.

        Returns:
            Parsed inner JSON data from the response.

        Raises:
            requests.HTTPError: On HTTP-level failures.
            ValueError: On response parsing failures.
        """
        sp = self.ensure_session()

        # Build the f.req payload: [[["rpc_id","json_payload",null,"generic"]]]
        inner = json.dumps(payload, separators=(",", ":"))
        freq = json.dumps(
            [[[rpc_id, inner, None, "generic"]]],
            separators=(",", ":"),
        )

        body = urllib.parse.urlencode({"f.req": freq, "at": sp.at}) + "&"

        params = {
            "rpcids": rpc_id,
            "source-path": source_path,
            "bl": sp.bl,
            "f.sid": sp.f_sid,
            "hl": "en",
            "_reqid": str(_next_reqid()),
            "rt": "c",
        }

        url = f"{BASE_URL}{BATCHEXECUTE_PATH}"
        resp = self._http.post(url, data=body, params=params)
        resp.raise_for_status()
        return self._parse_batchexecute(resp.text)

    # ── Streaming query ────────────────────────────────────────────────

    def query_stream(
        self,
        notebook_id: str,
        query: str,
        source_ids: list[str] | None = None,
        history: list[dict] | None = None,
    ) -> str:
        """Send a chat query and return the assembled response text.

        Args:
            notebook_id: UUID of the notebook.
            query: The user's query text.
            source_ids: Optional list of source IDs to scope the query.
            history: Optional conversation history.

        Returns:
            The assembled markdown response string.
        """
        sp = self.ensure_session()

        sources = source_ids or []
        hist = history or []

        # Build the nested payload for GenerateFreeFormStreamed
        freq_inner = json.dumps(
            [sources, query, hist, notebook_id],
            separators=(",", ":"),
        )
        freq = json.dumps(
            [[["GenerateFreeFormStreamed", freq_inner, None, "generic"]]],
            separators=(",", ":"),
        )

        body = urllib.parse.urlencode({"f.req": freq, "at": sp.at}) + "&"

        params = {
            "bl": sp.bl,
            "f.sid": sp.f_sid,
            "hl": "en",
            "_reqid": str(_next_reqid()),
            "rt": "c",
        }

        headers = {
            "x-goog-ext-353267353-jspb": "[null,null,null,282611]",
        }

        url = f"{BASE_URL}{STREAM_PATH}"
        resp = self._http.post(
            url, data=body, params=params, headers=headers, stream=True,
        )
        resp.raise_for_status()

        # Assemble streamed chunks
        return self._parse_stream_response(resp.text)

    # ── Response parsing ───────────────────────────────────────────────

    @staticmethod
    def _parse_batchexecute(raw: str) -> Any:
        """Parse a batchexecute response.

        The format is:
            )]}'\n
            <length>\n
            [["wrb.fr","rpc_id","<inner_json_string>", ...], ...]

        We strip the security prefix, parse the outer array, then
        double-parse the inner JSON string.
        """
        # Strip )]}' prefix
        text = raw
        if text.startswith(")]}'"):
            text = text[4:]
        text = text.strip()

        # The response may have multiple length-prefixed chunks.
        # We find the first valid JSON array.
        chunks = _extract_chunks(text)
        if not chunks:
            raise ValueError(f"Could not parse batchexecute response")

        # Find the data chunk (the one with the RPC result)
        for chunk in chunks:
            try:
                outer = json.loads(chunk)
            except json.JSONDecodeError:
                continue

            if not isinstance(outer, list):
                continue

            for entry in outer:
                if (
                    isinstance(entry, list)
                    and len(entry) >= 3
                    and isinstance(entry[2], str)
                ):
                    try:
                        return json.loads(entry[2])
                    except json.JSONDecodeError:
                        continue

        raise ValueError("No valid inner JSON found in batchexecute response")

    @staticmethod
    def _parse_stream_response(raw: str) -> str:
        """Parse a streaming response and assemble the final text."""
        text = raw
        if text.startswith(")]}'"):
            text = text[4:]

        chunks = _extract_chunks(text.strip())
        assembled = []

        for chunk in chunks:
            try:
                outer = json.loads(chunk)
            except json.JSONDecodeError:
                continue

            if not isinstance(outer, list):
                continue

            for entry in outer:
                if not isinstance(entry, list) or len(entry) < 3:
                    continue
                inner_str = entry[2] if isinstance(entry[2], str) else None
                if not inner_str:
                    continue
                try:
                    inner = json.loads(inner_str)
                except json.JSONDecodeError:
                    continue

                # Navigate the nested structure to find text chunks
                text_part = _extract_text_from_inner(inner)
                if text_part:
                    assembled.append(text_part)

        return "".join(assembled)


def _extract_chunks(text: str) -> list[str]:
    """Extract length-prefixed JSON chunks from batchexecute response body.

    Format is: <decimal_length>\n<json_of_that_length>\n...
    """
    chunks = []
    pos = 0
    while pos < len(text):
        # Skip whitespace
        while pos < len(text) and text[pos] in (" ", "\t", "\r", "\n"):
            pos += 1
        if pos >= len(text):
            break

        # Read length
        length_start = pos
        while pos < len(text) and text[pos].isdigit():
            pos += 1
        if pos == length_start:
            break

        chunk_len = int(text[length_start:pos])

        # Skip the newline after the length
        if pos < len(text) and text[pos] == "\n":
            pos += 1

        # Read chunk
        chunk = text[pos : pos + chunk_len]
        chunks.append(chunk)
        pos += chunk_len

    return chunks


def _extract_text_from_inner(data: Any, depth: int = 0) -> str:
    """Recursively extract text content from nested response structures."""
    if depth > 15:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        # Heuristic: the first non-null string at a reasonable depth is text
        for item in data:
            if isinstance(item, str) and len(item) > 1:
                return item
            if isinstance(item, list):
                result = _extract_text_from_inner(item, depth + 1)
                if result:
                    return result
    return ""
