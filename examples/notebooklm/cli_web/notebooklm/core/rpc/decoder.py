"""Response decoding for NotebookLM batchexecute protocol."""

import json


_decoder = json.JSONDecoder()


def decode_response(raw_text: str) -> list:
    """Decode a batchexecute response.

    The response format is:
    )]}'
    <length>
    [["wrb.fr","<rpcid>","<json_string>",null,null,null,"generic"]]
    <length>
    ...

    Note: length prefixes are in bytes (UTF-8) but we work with character
    strings. We use json.JSONDecoder.raw_decode to find each complete JSON
    array regardless of the byte/char length mismatch.

    Args:
        raw_text: The raw response text from batchexecute.

    Returns:
        List of decoded response envelopes.
    """
    text = raw_text

    # Strip the anti-XSSI prefix
    if text.startswith(")]}'"):
        text = text[4:]

    results = []
    idx = 0

    while idx < len(text):
        # Skip to next '[' (start of JSON array)
        next_bracket = text.find("[", idx)
        if next_bracket == -1:
            break

        # Try to decode a complete JSON value starting here
        try:
            obj, end_idx = _decoder.raw_decode(text, next_bracket)
            results.append(obj)
            idx = end_idx
        except json.JSONDecodeError:
            # Skip past this bracket and try the next one
            idx = next_bracket + 1

    return results


def extract_rpc_data(envelopes: list, rpc_id: str) -> str | None:
    """Extract the JSON data string for a specific RPC method from decoded envelopes.

    Args:
        envelopes: Decoded response envelopes from decode_response().
        rpc_id: The RPC method ID to extract.

    Returns:
        The inner JSON data string, or None if not found.
    """
    for envelope in envelopes:
        if not isinstance(envelope, list):
            continue
        for item in envelope:
            if not isinstance(item, list):
                continue
            if len(item) >= 3 and item[0] == "wrb.fr" and item[1] == rpc_id:
                return item[2]
    return None


def parse_rpc_result(envelopes: list, rpc_id: str):
    """Extract and parse the result data for a specific RPC method.

    Args:
        envelopes: Decoded response envelopes from decode_response().
        rpc_id: The RPC method ID to extract.

    Returns:
        Parsed Python object from the inner JSON, or None.
    """
    data_str = extract_rpc_data(envelopes, rpc_id)
    if data_str is None:
        return None
    try:
        return json.loads(data_str)
    except (json.JSONDecodeError, TypeError):
        return None
