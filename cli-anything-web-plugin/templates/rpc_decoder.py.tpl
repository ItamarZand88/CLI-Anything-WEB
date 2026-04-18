"""Response decoder for Google batchexecute RPC protocol.

Production-parity implementation: handles multi-chunk responses, anti-XSSI
prefix, length-hint lines, and typed ``"er"`` error entries.
"""
from __future__ import annotations

import json
from typing import Any

from ..exceptions import AuthError, RPCError


def strip_prefix(data: "str | bytes") -> str:
    """Remove the anti-XSSI ``)]}'`` prefix from a batchexecute response.

    Returns a decoded ``str``. Batchexecute chunk lengths are JavaScript
    ``String.length`` values (UTF-16 code units / Unicode code points for
    BMP), not UTF-8 byte counts — all subsequent processing must use ``str``,
    not ``bytes``.
    """
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="replace")
    else:
        text = data
    if text.startswith(")]}'"):
        text = text[4:].lstrip("\n")
    return text


def parse_chunks(text: str) -> list[str]:
    """Extract all JSON arrays from a batchexecute response body.

    The body contains JSON arrays interspersed with length-hint numbers.
    Rather than trusting the length hints, use ``json.JSONDecoder.raw_decode``
    to find every JSON array in the stream, skipping numeric lines::

        11927\\n
        [["wrb.fr", "wXbhsf", "..."]]\\n
        59\\n
        [["di", 157], ["af.httprm", ...]]\\n
        27\\n
        [["e", 4, null, null, 12542]]
    """
    chunks: list[str] = []
    decoder = json.JSONDecoder()
    pos = 0
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
                _, end = decoder.raw_decode(text, pos)
                chunks.append(text[pos:end])
                pos = end
                continue
            except json.JSONDecodeError:
                pass
        pos += 1
    return chunks


def extract_result(chunks: list[str], rpc_id: str) -> Any:
    """Find and decode the result for a specific RPC method.

    Raises:
        AuthError: If the response carries an auth-related error code.
        RPCError: If the response carries any other error code or the RPC id
            is not present in any chunk.
    """
    for chunk in chunks:
        try:
            outer = json.loads(chunk)
        except (json.JSONDecodeError, ValueError):
            continue
        for entry in outer:
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            if entry[0] == "er":
                err_code = entry[1] if len(entry) > 1 else None
                if err_code in (7, 9):
                    raise AuthError(
                        f"Auth error (code {err_code}) — run: cli-web-${app_name} auth login"
                    )
                raise RPCError(f"RPC error code {err_code}")
            if entry[0] == "wrb.fr" and entry[1] == rpc_id:
                raw = entry[2]
                if raw is None:
                    return None
                return json.loads(raw)
    raise RPCError(f"RPC result for {rpc_id!r} not found in response")


def decode_response(data: "str | bytes", rpc_id: str) -> Any:
    """Full decode pipeline: strip prefix → parse chunks → extract result."""
    text = strip_prefix(data)
    chunks = parse_chunks(text)
    return extract_result(chunks, rpc_id)
