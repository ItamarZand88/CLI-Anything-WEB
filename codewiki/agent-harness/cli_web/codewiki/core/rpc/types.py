"""RPC method IDs and constants for Code Wiki batchexecute API."""


class RPCMethod:
    """Batchexecute RPC method identifiers."""

    FEATURED_REPOS = "nm8Fsb"
    WIKI_PAGE = "VSX6ub"
    SEARCH_REPOS = "vyWDAf"
    CHAT = "EgIxfe"


BATCHEXECUTE_URL = "https://codewiki.google/_/BoqAngularSdlcAgentsUi/data/batchexecute"

BASE_URL = "https://codewiki.google"

DEFAULT_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "x-same-domain": "1",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
}
