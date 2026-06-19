"""HTTP client for YouTube InnerTube API."""

from __future__ import annotations

import httpx

from .exceptions import (
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    ServerError,
    YouTubeError,
)
from .models import (
    format_channel,
    format_video_detail,
    format_video_from_renderer,
)

INNERTUBE_URL = "https://www.youtube.com/youtubei/v1"
INNERTUBE_CONTEXT = {
    "client": {
        "clientName": "WEB",
        "clientVersion": "2.20260326.01.00",
        "hl": "en",
        "gl": "US",
    }
}


class YouTubeClient:
    """Client for YouTube's InnerTube API."""

    def __init__(self):
        self._session = httpx.Client(
            timeout=15.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            follow_redirects=True,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._session.close()

    def close(self):
        self._session.close()

    # ── Internal ──────────────────────────────────────────────

    def _post(self, endpoint: str, body: dict) -> dict:
        """POST to InnerTube API with context."""
        url = f"{INNERTUBE_URL}/{endpoint}?prettyPrint=false"
        payload = {"context": INNERTUBE_CONTEXT, **body}
        try:
            resp = self._session.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}") from exc
        except Exception as exc:
            raise NetworkError(f"Request failed: {exc}") from exc
        return self._handle_response(resp, endpoint)

    def _handle_response(self, resp: httpx.Response, endpoint: str = "") -> dict:
        if resp.status_code == 404:
            raise NotFoundError(f"Not found: {endpoint}")
        if resp.status_code == 429:
            retry = resp.headers.get("retry-after")
            raise RateLimitError(
                retry_after=float(retry) if retry else None,
            )
        if resp.status_code >= 500:
            raise ServerError(
                f"YouTube server error: HTTP {resp.status_code}",
                status_code=resp.status_code,
            )
        if resp.status_code >= 400:
            raise YouTubeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            return resp.json()
        except Exception as exc:
            raise ParseError(f"Failed to parse response: {exc}") from exc

    # ── Search ────────────────────────────────────────────────

    def search(self, query: str, limit: int = 20) -> dict:
        """Search YouTube videos."""
        resp = self._post("search", {"query": query})

        contents = (
            resp.get("contents", {})
            .get("twoColumnSearchResultsRenderer", {})
            .get("primaryContents", {})
            .get("sectionListRenderer", {})
            .get("contents", [])
        )

        videos = []
        for section in contents:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                renderer = item.get("videoRenderer")
                if renderer:
                    videos.append(format_video_from_renderer(renderer))
                    if len(videos) >= limit:
                        break
            if len(videos) >= limit:
                break

        estimated = resp.get("estimatedResults", "0")

        return {
            "query": query,
            "estimated_results": int(estimated),
            "videos": videos,
        }

    # ── Video detail ──────────────────────────────────────────

    def video_detail(self, video_id: str) -> dict:
        """Get video details via player endpoint."""
        resp = self._post("player", {"videoId": video_id})
        video_details = resp.get("videoDetails")
        if not video_details:
            raise NotFoundError(f"Video not found: {video_id}")
        microformat = resp.get("microformat")
        return format_video_detail(video_details, microformat)

    # ── Transcripts ───────────────────────────────────────────

    def _caption_tracks(self, video_id: str) -> tuple[list[dict], str]:
        """Return (caption_tracks, video_title) from the player response."""
        resp = self._post("player", {"videoId": video_id})
        details = resp.get("videoDetails")
        if not details:
            raise NotFoundError(f"Video not found: {video_id}")
        tracks = (
            resp.get("captions", {})
            .get("playerCaptionsTracklistRenderer", {})
            .get("captionTracks", [])
        )
        return tracks, details.get("title", "")

    @staticmethod
    def _track_label(track: dict) -> str:
        name = track.get("name", {})
        if "simpleText" in name:
            return name["simpleText"]
        return "".join(r.get("text", "") for r in name.get("runs", []))

    @staticmethod
    def _select_track(tracks: list[dict], languages: list[str] | None) -> dict:
        """Pick a caption track by language priority, else manual, else first."""
        if languages:
            for lang in languages:
                lang_l = lang.lower()
                for track in tracks:
                    if track.get("languageCode", "").lower() == lang_l:
                        return track
            available = ", ".join(sorted({t.get("languageCode", "") for t in tracks}))
            raise NotFoundError(f"No transcript for languages {languages}. Available: {available}")
        for track in tracks:  # prefer a human-authored track over auto-generated
            if track.get("kind") != "asr":
                return track
        return tracks[0]

    @staticmethod
    def _parse_json3(payload: str) -> list[dict]:
        """Parse YouTube timedtext json3 into [{text, start, duration}]."""
        import json as _json

        try:
            data = _json.loads(payload)
        except _json.JSONDecodeError as exc:
            raise ParseError(f"Failed to parse transcript: {exc}") from exc
        segments = []
        for event in data.get("events", []):
            segs = event.get("segs")
            if not segs:
                continue
            text = "".join(s.get("utf8", "") for s in segs).strip()
            if not text:
                continue
            segments.append(
                {
                    "text": text,
                    "start": round(event.get("tStartMs", 0) / 1000.0, 3),
                    "duration": round(event.get("dDurationMs", 0) / 1000.0, 3),
                }
            )
        return segments

    def list_transcripts(self, video_id: str) -> dict:
        """List available caption tracks for a video."""
        tracks, title = self._caption_tracks(video_id)
        return {
            "video_id": video_id,
            "title": title,
            "transcripts": [
                {
                    "language_code": t.get("languageCode", ""),
                    "name": self._track_label(t),
                    "kind": "auto" if t.get("kind") == "asr" else "manual",
                    "translatable": bool(t.get("isTranslatable")),
                }
                for t in tracks
            ],
        }

    def transcript(
        self,
        video_id: str,
        languages: list[str] | None = None,
        translate: str | None = None,
    ) -> dict:
        """Fetch a video transcript as timestamped segments plus full text.

        languages: preferred language codes in priority order (e.g. ["en", "en-US"]);
                   falls back to a human-authored track, then the first available.
        translate: target language code — uses YouTube's caption translation.
        """
        tracks, title = self._caption_tracks(video_id)
        if not tracks:
            raise NotFoundError(f"No transcripts available for video: {video_id}")

        track = self._select_track(tracks, languages)
        base_url = track.get("baseUrl", "")
        if not base_url:
            raise ParseError(f"Caption track has no URL for video: {video_id}")

        url = base_url + ("&" if "?" in base_url else "?") + "fmt=json3"
        if translate:
            url += f"&tlang={translate}"

        try:
            resp = self._session.get(url)
        except Exception as exc:
            raise NetworkError(f"Failed to fetch transcript: {exc}") from exc
        if resp.status_code >= 400:
            raise YouTubeError(f"HTTP {resp.status_code} fetching transcript")

        segments = self._parse_json3(resp.text)
        return {
            "video_id": video_id,
            "title": title,
            "language_code": translate or track.get("languageCode", ""),
            "kind": "auto" if track.get("kind") == "asr" else "manual",
            "is_translated": bool(translate),
            "segment_count": len(segments),
            "segments": segments,
            "text": " ".join(s["text"] for s in segments).strip(),
        }

    # ── Trending ──────────────────────────────────────────────

    def trending(self, category: str = "now") -> list[dict]:
        """Get trending/popular videos via search with sort by view count.

        YouTube's trending page requires auth for non-logged-in users,
        so we use the search API with popular sort filters as a proxy.
        """
        # Map categories to search queries that surface popular content
        queries = {
            "now": "",  # empty query with sort=viewCount returns popular recent videos
            "music": "music",
            "gaming": "gaming",
            "movies": "movies",
        }
        query = queries.get(category, category)

        # Use search with empty/broad query — returns popular videos
        resp = self._post(
            "search",
            {
                "query": query if query else "trending",
                "params": "CAMSAhAB",  # sort by upload date, filter videos only
            },
        )

        contents = (
            resp.get("contents", {})
            .get("twoColumnSearchResultsRenderer", {})
            .get("primaryContents", {})
            .get("sectionListRenderer", {})
            .get("contents", [])
        )

        videos = []
        for section in contents:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                renderer = item.get("videoRenderer")
                if renderer:
                    videos.append(format_video_from_renderer(renderer))

        return videos

    # ── Channel ───────────────────────────────────────────────

    def channel(self, handle: str) -> dict:
        """Get channel info via browse endpoint.

        Accepts @handle, channel ID (UC...), or /c/name format.
        """
        # For @handles, scrape the channel page HTML to get ytInitialData
        # This is more reliable than the browse API which needs an API key
        import json as _json

        clean = handle.lstrip("@")
        if handle.startswith("UC"):
            channel_url = f"https://www.youtube.com/channel/{handle}"
        else:
            channel_url = f"https://www.youtube.com/@{clean}"

        try:
            page_resp = self._session.get(channel_url)
        except Exception as exc:
            raise NetworkError(f"Failed to fetch channel: {exc}") from exc

        if page_resp.status_code == 404:
            raise NotFoundError(f"Channel not found: {handle}")

        text = page_resp.text
        marker = "var ytInitialData = "
        idx = text.find(marker)
        if idx < 0:
            raise ParseError(f"Could not find channel data for: {handle}")

        start = idx + len(marker)
        end = text.find(";</script>", start)
        if end < 0:
            end = text.find(";\n", start)

        try:
            resp = _json.loads(text[start:end])
        except _json.JSONDecodeError as exc:
            raise ParseError(f"Failed to parse channel data: {exc}") from exc
        header = resp.get("header", {})
        metadata = resp.get("metadata", {}).get("channelMetadataRenderer", {})
        result = format_channel(header)
        if "channel_id" in result and not result["channel_id"]:
            result["channel_id"] = metadata.get("externalId", "")
        if not result.get("url"):
            result["url"] = metadata.get("channelUrl", channel_url)

        # Extract recent videos from tabs
        tabs = resp.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
        recent_videos = []
        for tab in tabs:
            tab_content = tab.get("tabRenderer", {}).get("content", {})
            sections = tab_content.get("sectionListRenderer", {}).get(
                "contents", []
            ) or tab_content.get("richGridRenderer", {}).get("contents", [])
            for section in sections[:10]:
                # richItemRenderer wraps videoRenderer in newer layouts
                rich = section.get("richItemRenderer", {}).get("content", {})
                renderer = rich.get("videoRenderer") or section.get("videoRenderer")
                if renderer:
                    recent_videos.append(format_video_from_renderer(renderer))
            if recent_videos:
                break

        result["recent_videos"] = recent_videos[:10]
        return result
