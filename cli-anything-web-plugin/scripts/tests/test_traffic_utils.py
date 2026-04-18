"""Tests for traffic_utils.py — shared noise/static/header helpers."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import traffic_utils  # noqa: E402


def test_is_noise_google_analytics():
    assert traffic_utils.is_noise_url("https://google-analytics.com/collect") is True


def test_is_noise_facebook_tracking():
    assert traffic_utils.is_noise_url("https://facebook.com/tr?id=1") is True


def test_is_noise_datadog():
    assert traffic_utils.is_noise_url("https://browser-intake-datadoghq.com/api/v2/rum") is True


def test_is_noise_rejects_real_api():
    assert traffic_utils.is_noise_url("https://api.example.com/v1/users") is False
    assert traffic_utils.is_noise_url("https://example.com/graphql") is False


def test_is_static_asset_by_extension():
    assert traffic_utils.is_static_asset("https://cdn.example.com/app.js") is True
    assert traffic_utils.is_static_asset("https://cdn.example.com/style.css") is True
    assert traffic_utils.is_static_asset("https://cdn.example.com/logo.png") is True


def test_is_static_asset_strips_query_and_fragment():
    assert traffic_utils.is_static_asset("https://cdn.example.com/app.js?v=123") is True
    assert traffic_utils.is_static_asset("https://cdn.example.com/app.js#section") is True


def test_is_static_asset_rejects_api():
    assert traffic_utils.is_static_asset("https://api.example.com/v1/users") is False


def test_is_static_asset_default_preserves_media_api_endpoints():
    """Music-streaming APIs like /songs/123.mp3 must NOT be filtered by default."""
    assert traffic_utils.is_static_asset("https://api.music.com/songs/123.mp3") is False
    assert traffic_utils.is_static_asset("https://api.example.com/videos/1.mp4") is False


def test_is_static_asset_include_media_filters_media():
    """With include_media=True (real-time capture), media IS filtered."""
    assert traffic_utils.is_static_asset("https://cdn.example.com/clip.mp4", include_media=True) is True
    assert traffic_utils.is_static_asset("https://cdn.example.com/audio.mp3", include_media=True) is True


def test_is_noise_url_handles_none():
    assert traffic_utils.is_noise_url(None) is False


def test_is_noise_url_handles_empty_string():
    assert traffic_utils.is_noise_url("") is False


def test_is_static_asset_handles_empty_string():
    assert traffic_utils.is_static_asset("") is False


def test_normalize_headers_dict_pass_through():
    assert traffic_utils.normalize_headers({"A": "1"}) == {"A": "1"}


def test_normalize_headers_list_format():
    playwright = [{"name": "A", "value": "1"}, {"name": "B", "value": "2"}]
    assert traffic_utils.normalize_headers(playwright) == {"A": "1", "B": "2"}


def test_normalize_headers_none_returns_empty():
    assert traffic_utils.normalize_headers(None) == {}


def test_noise_patterns_compiled_once():
    # Sanity: NOISE_PATTERNS must be pre-compiled regex objects, not strings.
    import re
    assert all(isinstance(p, re.Pattern) for p in traffic_utils.NOISE_PATTERNS)
    assert len(traffic_utils.NOISE_PATTERNS) > 20  # merged list is substantial
