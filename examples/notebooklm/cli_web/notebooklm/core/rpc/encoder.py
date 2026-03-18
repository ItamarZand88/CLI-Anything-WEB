"""Request encoding for NotebookLM batchexecute protocol."""

import json
import urllib.parse


def encode_request(rpc_id: str, params: list | str, at_token: str) -> str:
    """Encode a batchexecute request body.

    Args:
        rpc_id: The RPC method ID (e.g., 'wXbhsf').
        params: The inner parameter array/string for this RPC method.
        at_token: The CSRF token from WIZ_global_data.

    Returns:
        URL-encoded form body string.
    """
    if isinstance(params, list):
        params_json = json.dumps(params, separators=(",", ":"))
    else:
        params_json = params

    outer = [[
        [rpc_id, params_json, None, "generic"]
    ]]
    f_req = json.dumps(outer, separators=(",", ":"))

    body_parts = {
        "f.req": f_req,
        "at": at_token,
        "": "",  # trailing ampersand
    }

    return urllib.parse.urlencode(body_parts, quote_via=urllib.parse.quote)


def build_query_params(
    rpc_id: str,
    source_path: str,
    bl: str,
    fsid: str,
    hl: str = "en",
    reqid: int = 100000,
) -> dict:
    """Build the query string parameters for a batchexecute request.

    Args:
        rpc_id: The RPC method ID.
        source_path: Current page path (e.g., '/' or '/notebook/<id>').
        bl: Build label from WIZ_global_data.
        fsid: Session ID from WIZ_global_data.
        hl: UI language code.
        reqid: Request counter (auto-incremented).

    Returns:
        Dict of query parameters.
    """
    return {
        "rpcids": rpc_id,
        "source-path": source_path,
        "bl": bl,
        "f.sid": fsid,
        "hl": hl,
        "_reqid": str(reqid),
        "rt": "c",
    }
