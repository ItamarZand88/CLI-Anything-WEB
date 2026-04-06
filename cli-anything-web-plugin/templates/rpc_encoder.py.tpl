"""Encode RPC requests for Google batchexecute.

Builds the f.req form body expected by /_/SERVICE/data/batchexecute.
"""
from __future__ import annotations

import json

from .types import RPCMethod


def encode_rpc(
    method: RPCMethod,
    params: list,
    *,
    csrf_token: str | None = None,
) -> dict:
    """Encode an RPC call into a batchexecute form body.

    Returns a dict suitable for httpx data= parameter.
    """
    rpc_id = method.value[0]
    inner = json.dumps(params, separators=(",", ":"))
    req_body = json.dumps([[
        [rpc_id, inner, None, "generic"],
    ]], separators=(",", ":"))
    body = {"f.req": req_body}
    if csrf_token:
        body["at"] = csrf_token
    return body
