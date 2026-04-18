"""Shared traffic-analysis helpers for capture + analysis scripts.

Merged from the previous independent implementations in mitmproxy-capture.py
(compiled-regex noise filter) and analyze-traffic.py (substring noise filter).
The compiled-regex approach is ~10x faster on large traces and is used here.

Consumers:
    - parse-trace.py (static-asset filtering)
    - analyze-traffic.py (noise filtering + header normalization)
    - mitmproxy-capture.py (real-time noise filtering)
"""
from __future__ import annotations

import re

# File extensions treated as static assets (not API traffic).
STATIC_EXTENSIONS: frozenset[str] = frozenset((
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".webp", ".avif",
    ".mp4", ".webm", ".mp3", ".ogg",
))

# Noise URL patterns — analytics, tracking, ad networks, CDN endpoints.
# Compiled once at import; cheap to call many times per entry.
#
# Keep organized by category — any new pattern should be added to the right
# section so maintainers can see the full taxonomy at a glance.
NOISE_PATTERNS: list[re.Pattern[str]] = [
    # --- Google analytics / ads ---
    re.compile(r"google-analytics\.com", re.I),
    re.compile(r"analytics\.google\.com", re.I),
    re.compile(r"googletagmanager\.com", re.I),
    re.compile(r"googlesyndication\.com", re.I),
    re.compile(r"googleadservices\.com", re.I),
    re.compile(r"doubleclick\.net", re.I),
    re.compile(r"google\.com/pagead", re.I),
    re.compile(r"google\.com/ads", re.I),
    re.compile(r"www\.google\.co\.", re.I),
    re.compile(r"gstatic\.com", re.I),
    re.compile(r"googleapis\.com/css", re.I),
    re.compile(r"fonts\.googleapis\.com", re.I),
    re.compile(r"fonts\.gstatic\.com", re.I),
    re.compile(r"play\.google\.com/log", re.I),
    re.compile(r"signaler-pa\.clients6", re.I),
    re.compile(r"accounts\.google\.com/gsi/", re.I),
    re.compile(r"apis\.google\.com", re.I),
    re.compile(r"adtrafficquality\.google", re.I),

    # --- Cloudflare ---
    re.compile(r"cdn-cgi/", re.I),
    re.compile(r"cloudflareinsights", re.I),
    re.compile(r"static\.cloudflareinsights", re.I),
    re.compile(r"cdn-cgi/rum", re.I),
    re.compile(r"cdn-cgi/challenge-platform", re.I),

    # --- Social / trackers ---
    re.compile(r"facebook\.net", re.I),
    re.compile(r"facebook\.com/tr", re.I),
    re.compile(r"connect\.facebook", re.I),
    re.compile(r"analytics\.twitter\.com", re.I),
    re.compile(r"ads-twitter\.com", re.I),
    re.compile(r"twitter\.com", re.I),

    # --- Ad networks / programmatic advertising ---
    re.compile(r"taboola\.com", re.I),
    re.compile(r"outbrain\.com", re.I),
    re.compile(r"optable\.co", re.I),
    re.compile(r"admedo\.com", re.I),
    re.compile(r"scorecardresearch\.com", re.I),
    re.compile(r"statcounter\.com", re.I),
    re.compile(r"liftdsp\.com", re.I),
    re.compile(r"bidr\.io", re.I),
    re.compile(r"cnv\.event\.prod", re.I),
    re.compile(r"rubiconproject\.com", re.I),
    re.compile(r"criteo\.com", re.I),
    re.compile(r"adnxs\.com", re.I),
    re.compile(r"adsrvr\.org", re.I),
    re.compile(r"sharethrough\.com", re.I),
    re.compile(r"3lift\.com", re.I),
    re.compile(r"liadm\.com", re.I),
    re.compile(r"id5-sync\.com", re.I),
    re.compile(r"casalemedia\.com", re.I),
    re.compile(r"kargo\.com", re.I),
    re.compile(r"unrulymedia\.com", re.I),
    re.compile(r"lngtd\.com", re.I),
    re.compile(r"creativecdn\.com", re.I),
    re.compile(r"moatads\.com", re.I),
    re.compile(r"amazon-adsystem\.com", re.I),
    re.compile(r"pubmatic\.com", re.I),
    re.compile(r"openx\.net", re.I),
    re.compile(r"indexww\.com", re.I),
    re.compile(r"hadron\.ad\.gt", re.I),

    # --- Monitoring / analytics SDKs ---
    re.compile(r"segment\.io", re.I),
    re.compile(r"segment\.com/v1", re.I),
    re.compile(r"segment\.prod", re.I),
    re.compile(r"amplitude\.com", re.I),
    re.compile(r"mixpanel\.com", re.I),
    re.compile(r"hotjar\.com", re.I),
    re.compile(r"clarity\.ms", re.I),
    re.compile(r"sentry\.io/api", re.I),
    re.compile(r"datadoghq\.com", re.I),
    re.compile(r"rum-http-intake", re.I),
    re.compile(r"browser-intake-datadoghq", re.I),
    re.compile(r"newrelic\.com", re.I),
    re.compile(r"nr-data\.net", re.I),
    re.compile(r"fullstory\.com", re.I),

    # --- CRM / marketing automation ---
    re.compile(r"hubspot\.com", re.I),
    re.compile(r"hscollectedforms\.net", re.I),
    re.compile(r"hsforms\.com", re.I),
    re.compile(r"cookiebot\.com", re.I),
    re.compile(r"cookielaw\.org", re.I),
    re.compile(r"onetrust\.com", re.I),
    re.compile(r"intercom\.io", re.I),
    re.compile(r"crisp\.chat", re.I),
    re.compile(r"zendesk\.com", re.I),
    re.compile(r"/ht/event", re.I),
    re.compile(r"/hubspot", re.I),

    # --- Fonts / CDN ---
    re.compile(r"fontawesome\.com", re.I),

    # --- GitHub internal ---
    re.compile(r"avatars\.githubusercontent\.com", re.I),
    re.compile(r"collector\.github\.com", re.I),
    re.compile(r"api\.github\.com/_private", re.I),

    # --- Generic beacon / pixel / rum ---
    re.compile(r"/beacon", re.I),
    re.compile(r"/pixel", re.I),
    re.compile(r"/collect\b", re.I),
    re.compile(r"/rum", re.I),
    re.compile(r"/manifest\.json", re.I),

    # --- Site-specific tracking (non-API endpoints) ---
    re.compile(r"slinksuggestion\.com", re.I),
    re.compile(r"drainpaste\.com", re.I),
    re.compile(r"e\.producthunt\.com", re.I),
    re.compile(r"t\.producthunt\.com", re.I),
]


def is_noise_url(url: str) -> bool:
    """Return True if a URL matches any noise pattern (ads/tracking/CDN)."""
    return any(p.search(url) for p in NOISE_PATTERNS)


def is_static_asset(url: str) -> bool:
    """Return True if a URL points to a static asset by file extension."""
    path = url.split("?")[0].split("#")[0]
    return any(path.endswith(ext) for ext in STATIC_EXTENSIONS)


def normalize_headers(headers) -> dict:
    """Normalize headers to flat {name: value} dict.

    Accepts:
        - dict (mitmproxy, already flat)
        - list of {name, value} dicts (playwright trace format)
        - None (returns {})
    """
    if isinstance(headers, dict):
        return headers
    if isinstance(headers, list):
        return {
            h.get("name", ""): h.get("value", "")
            for h in headers
            if isinstance(h, dict)
        }
    return {}
