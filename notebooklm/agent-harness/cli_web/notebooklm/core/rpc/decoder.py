"""Response decoder for Google batchexecute RPC protocol."""
import json
from typing import Any


from ..exceptions import AuthError, RPCError


def strip_prefix(data: "str | bytes") -> str:
    """Remove the anti-XSSI prefix from a batchexecute response.

    Returns a decoded string. The batchexecute chunk lengths are JavaScript
    String.length values (UTF-16 code units / Unicode code points for BMP),
    not UTF-8 byte counts — so all subsequent processing must use str, not bytes.
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

    The response contains JSON arrays interspersed with length-hint numbers.
    Rather than trusting the length hints (which are JS String.length values
    and may span multiple arrays), we use json.JSONDecoder.raw_decode to find
    every JSON array in the stream, skipping numeric lines.

        11927\\n
        [["wrb.fr", "wXbhsf", "..."]]\\n
        59\\n
        [["di", 157], ["af.httprm", ...]]\\n
        27\\n
        [["e", 4, null, null, 12542]]
    """
    chunks = []
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(text):
        ch = text[pos]
        # Skip whitespace
        if ch in " \t\r\n":
            pos += 1
            continue
        # Skip length-hint number lines
        if ch.isdigit():
            while pos < len(text) and text[pos] != "\n":
                pos += 1
            continue
        # Try parsing a JSON value starting here
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

    Args:
        chunks: Parsed response chunks
        rpc_id: The expected RPC method ID

    Returns:
        The decoded result (double-parsed from JSON string)

    Raises:
        RPCError: If an error entry is found
        AuthError: If the error indicates auth failure
        ValueError: If the expected rpc_id is not found in any chunk
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
                # Error entry — check for auth-related codes
                err_code = entry[1] if len(entry) > 1 else None
                if err_code in (7, 9):
                    raise AuthError(f"Auth error (code {err_code}) — run: cli-web-notebooklm auth login")
                raise RPCError(f"RPC error code {err_code}")
            if entry[0] == "wrb.fr" and entry[1] == rpc_id:
                # entry[2] is a JSON string that needs another json.loads()
                raw = entry[2]
                if raw is None:
                    return None
                return json.loads(raw)
    raise ValueError(f"RPC result for '{rpc_id}' not found in response")


def decode_response(data: "str | bytes", rpc_id: str) -> Any:
    """Full decode pipeline: strip prefix → parse chunks → extract result.

    Args:
        data: Raw response body from batchexecute (str or bytes)
        rpc_id: The expected RPC method ID

    Returns:
        The decoded result object
    """
    text = strip_prefix(data)
    chunks = parse_chunks(text)
    return extract_result(chunks, rpc_id)
