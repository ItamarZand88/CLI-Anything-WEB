"""Decode batchexecute RPC responses.

Google batchexecute responses have a prefix line (e.g., )]}'\\n) followed
by length-prefixed JSON arrays. This module strips the prefix and parses
the inner payload.
"""
from __future__ import annotations

import json

from ..exceptions import RPCError
from .types import RPCMethod


def decode_response(raw: str, method: RPCMethod) -> list:
    """Decode a batchexecute response and return the inner payload.

    Args:
        raw: The full response text from batchexecute endpoint.
        method: The RPC method that was called (for error context).

    Returns:
        Parsed inner JSON array from the RPC response.

    Raises:
        RPCError: If the response cannot be parsed.
    """
    # Strip the security prefix
    lines = raw.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("[["):
            break
    else:
        raise RPCError(f"Cannot parse batchexecute response for {method.value[0]}")

    try:
        outer = json.loads(lines[i])
    except json.JSONDecodeError as exc:
        raise RPCError(f"JSON decode failed for {method.value[0]}: {exc}")

    # Navigate to inner payload: outer[0][2] contains the JSON string
    try:
        inner_str = outer[0][2]
        if isinstance(inner_str, str):
            return json.loads(inner_str)
        return inner_str
    except (IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RPCError(f"Inner payload extraction failed for {method.value[0]}: {exc}")
