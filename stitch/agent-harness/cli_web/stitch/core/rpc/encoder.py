"""Request encoder for Google batchexecute RPC protocol."""
import json
import urllib.parse
from .types import BATCHEXECUTE_URL


def encode_request(rpc_id: str, params: list, csrf_token: str) -> str:
    """Encode an RPC request into batchexecute form-encoded body.

    Args:
        rpc_id: The RPC method ID (e.g., "A7f2qf")
        params: The parameter list for the RPC call
        csrf_token: The SNlM0e CSRF token

    Returns:
        URL-encoded form body string
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
        rpc_id: The RPC method ID
        session_id: The FdrFJe session ID
        build_label: The cfb2h build label
        source_path: The source-path parameter
        req_id: Request ID counter
        lang: Language code

    Returns:
        Full batchexecute URL with query string
    """
    params = {
        "rpcids": rpc_id,
        "source-path": source_path,
        "f.sid": session_id,
        "hl": lang,
        "_reqid": str(req_id),
        "rt": "c",
    }
    if build_label:
        params["bl"] = build_label
    return f"{BATCHEXECUTE_URL}?{urllib.parse.urlencode(params)}"
