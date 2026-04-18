"""Request encoder for Google batchexecute RPC protocol."""
from __future__ import annotations

import json
import urllib.parse

from .types import BATCHEXECUTE_URL


def encode_request(rpc_id: str, params: list, csrf_token: str) -> str:
    """Encode a batchexecute request body.

    Args:
        rpc_id: The RPC method identifier (e.g., ``'wXbhsf'``).
        params: The method parameters as a Python list.
        csrf_token: The CSRF token (``SNlM0e`` from ``WIZ_global_data``).

    Returns:
        URL-encoded form body string ready for POST (``Content-Type:
        application/x-www-form-urlencoded``).
    """
    inner = [rpc_id, json.dumps(params), None, "generic"]
    freq = json.dumps([[inner]])
    return urllib.parse.urlencode({"f.req": freq, "at": csrf_token})


def build_url(
    rpc_id: str,
    session_id: str,
    build_label: str = "",
    source_path: str = "/",
    req_id: int = 100000,
    lang: str = "en",
) -> str:
    """Build the batchexecute URL with query parameters.

    Args:
        rpc_id: The RPC method identifier.
        session_id: The ``f.sid`` value (``FdrFJe`` from ``WIZ_global_data``).
        build_label: The ``bl`` value (``cfb2h``) — optional.
        source_path: The current page context path (sent as ``source-path``).
        req_id: Incrementing request counter; start at 100000.
        lang: Language code (``hl`` param).
    """
    params: dict[str, str] = {
        "rpcids": rpc_id,
        "source-path": source_path,
        "f.sid": session_id,
        "hl": lang,
        "rt": "c",
        "_reqid": str(req_id),
    }
    if build_label:
        params["bl"] = build_label
    return f"{BATCHEXECUTE_URL}?{urllib.parse.urlencode(params)}"
