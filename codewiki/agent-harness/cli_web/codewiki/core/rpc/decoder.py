"""Decode batchexecute RPC responses from Code Wiki."""

from __future__ import annotations

import json
from typing import Any

from ..exceptions import RPCError


def _strip_prefix(raw: bytes | str) -> str:
    """Remove the )]}' anti-XSSI prefix."""
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    if text.startswith(")]}'"):
        text = text[4:]
    return text.lstrip("\n")


def _parse_chunks(text: str) -> list[list]:
    """Extract JSON array chunks from the batchexecute response.

    The response interleaves numeric length hints with JSON arrays.
    We use raw_decode to reliably find array boundaries.
    """
    decoder = json.JSONDecoder()
    chunks: list[list] = []
    pos = 0
    length = len(text)

    while pos < length:
        # Skip whitespace and numeric length lines
        while pos < length and text[pos] in " \t\r\n":
            pos += 1
        if pos >= length:
            break

        # Skip numeric length hints
        if text[pos].isdigit():
            while pos < length and text[pos] not in "\n":
                pos += 1
            continue

        # Try to decode a JSON array
        if text[pos] == "[":
            try:
                obj, end = decoder.raw_decode(text, pos)
                chunks.append(obj)
                pos = end
            except json.JSONDecodeError:
                pos += 1
        else:
            pos += 1

    return chunks


def decode_response(raw: bytes | str, rpc_id: str) -> Any:
    """Decode a batchexecute response and extract the result for rpc_id.

    Returns the parsed inner JSON, or None if the result is null.
    Raises RPCError or AuthError on protocol-level errors.
    """
    text = _strip_prefix(raw)
    chunks = _parse_chunks(text)

    for chunk in chunks:
        if not isinstance(chunk, list) or not chunk:
            continue
        for entry in chunk:
            if not isinstance(entry, list) or len(entry) < 2:
                continue

            # Check for error entries
            if entry[0] == "er" and len(entry) >= 2:
                err_data = entry[1] if len(entry) > 1 else None
                raise RPCError(f"RPC error: {err_data}", code=err_data)

            # Look for the result matching our rpc_id
            if entry[0] == "wrb.fr" and entry[1] == rpc_id:
                raw_result = entry[2] if len(entry) > 2 else None
                if raw_result is None:
                    return None
                # Double-parse: result is a JSON string inside JSON
                return json.loads(raw_result)

    return None
