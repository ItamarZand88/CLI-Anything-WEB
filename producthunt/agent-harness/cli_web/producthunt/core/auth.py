"""Auth module for cli-web-producthunt.

Product Hunt HTML scraping requires no authentication -- curl_cffi with
Chrome TLS impersonation bypasses Cloudflare without cookies or tokens.
"""


def get_auth_status() -> dict:
    """Return auth status.  Always configured since no auth is needed."""
    return {"configured": True, "message": "No auth required (HTML scraping)"}
