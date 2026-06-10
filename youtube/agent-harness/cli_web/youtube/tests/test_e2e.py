"""End-to-end tests for cli-web-youtube.

These tests make real HTTP requests to YouTube's InnerTube API
(https://www.youtube.com/youtubei/v1) and channel pages. No auth is
required (public API). Tests MUST FAIL (never skip) on network errors —
this CLI has no offline fallback (see HARNESS.md "Tests FAIL on missing auth").

CLI subprocess tests cover the fully installed `cli-web-youtube` entry
point. Set CLI_WEB_FORCE_INSTALLED=1 to require the installed binary
(instead of the `python -m` fallback).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest
from cli_web.youtube.core.client import YouTubeClient

KNOWN_VIDEO_ID = "dQw4w9WgXcQ"  # Rick Astley — Never Gonna Give You Up (stable)
KNOWN_CHANNEL = "@YouTube"  # Official YouTube channel (stable handle)

# ─── Canonical subprocess fixtures (_resolve_cli / _run / _parse_json) ──────


def _resolve_cli(cli_name: str) -> list[str]:
    """Locate the installed CLI binary, or fall back to `python -m ...`.

    If CLI_WEB_FORCE_INSTALLED=1 is set, raise if the binary is not on PATH.
    """
    forced = os.environ.get("CLI_WEB_FORCE_INSTALLED") == "1"
    path = shutil.which(cli_name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if forced:
        raise RuntimeError(
            f"CLI_WEB_FORCE_INSTALLED=1 but '{cli_name}' not found on PATH. "
            "Run `pip install -e .` in agent-harness/ before running subprocess tests."
        )
    # Fallback: module invocation
    module = cli_name.replace("cli-web-", "cli_web.").replace("-", "_")
    return [sys.executable, "-m", module]


def _run(
    cli_cmd: list[str],
    *args: str,
    timeout: float = 60.0,
    stdin: str | None = None,
) -> subprocess.CompletedProcess:
    """Run the CLI with the given args and return the completed process."""
    return subprocess.run(
        [*cli_cmd, *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _parse_json(result: subprocess.CompletedProcess) -> dict:
    """Parse CLI stdout as JSON, failing loudly with stdout/stderr context."""
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"CLI output is not valid JSON ({exc}).\n"
            f"stdout: {result.stdout[:500]!r}\n"
            f"stderr: {result.stderr[:500]!r}"
        )


@pytest.fixture(scope="module")
def cli_cmd():
    return _resolve_cli("cli-web-youtube")


@pytest.fixture(scope="module")
def client():
    with YouTubeClient() as c:
        yield c


# ─── Live API (Python layer) ────────────────────────────────────────────────


@pytest.mark.e2e
class TestLiveSearch:
    """YouTubeClient.search — live InnerTube search endpoint."""

    def test_search_returns_videos(self, client):
        result = client.search("python tutorial", limit=5)
        assert result["query"] == "python tutorial"
        assert result["estimated_results"] > 0, "estimated_results should be positive"
        assert len(result["videos"]) >= 1, "Search returned no videos"

    def test_search_respects_limit(self, client):
        result = client.search("python tutorial", limit=3)
        assert len(result["videos"]) <= 3, "Search exceeded requested limit"

    def test_search_video_fields(self, client):
        result = client.search("python tutorial", limit=5)
        first = result["videos"][0]
        assert first["id"], "First video has no id"
        assert len(first["id"]) == 11, f"video id {first['id']!r} not 11 chars"
        assert first["title"], "First video has no title"
        assert first["url"].startswith("https://www.youtube.com/watch?v="), (
            f"URL looks wrong: {first['url']}"
        )

    def test_search_no_protocol_leakage(self, client):
        result = client.search("python tutorial", limit=5)
        for v in result["videos"]:
            assert "wrb.fr" not in v["title"], "Raw RPC data leaked into title"
            assert "af.httprm" not in v["title"], "Raw RPC data leaked into title"
            assert "videoRenderer" not in v["title"], "Raw renderer JSON leaked into title"


@pytest.mark.e2e
class TestLiveVideoDetail:
    """YouTubeClient.video_detail — live InnerTube player endpoint."""

    def test_video_detail_returns_data(self, client):
        video = client.video_detail(KNOWN_VIDEO_ID)
        assert video["id"] == KNOWN_VIDEO_ID
        assert "Never Gonna Give You Up" in video["title"]
        assert video["channel"], "Video has no channel name"

    def test_video_detail_view_count_numeric(self, client):
        video = client.video_detail(KNOWN_VIDEO_ID)
        assert int(video["views"]) > 1_000_000, "View count suspiciously low"

    def test_video_detail_unknown_id_raises_not_found(self, client):
        from cli_web.youtube.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            client.video_detail("zzzzzzzzzzz")


@pytest.mark.e2e
class TestLiveTrending:
    """YouTubeClient.trending — live popular/trending proxy via search."""

    def test_trending_returns_videos(self, client):
        videos = client.trending(category="now")
        assert len(videos) >= 1, "Trending returned no videos"
        assert videos[0]["id"], "Trending video has no id"

    def test_trending_music_category(self, client):
        videos = client.trending(category="music")
        assert len(videos) >= 1, "Trending music returned no videos"
        for v in videos:
            assert v["title"], f"Trending video {v['id']} has empty title"


@pytest.mark.e2e
class TestLiveChannel:
    """YouTubeClient.channel — live channel page scrape (ytInitialData)."""

    def test_channel_returns_info(self, client):
        result = client.channel(KNOWN_CHANNEL)
        assert result["title"], "Channel has no title"
        assert result["channel_id"].startswith("UC"), (
            f"channel_id looks wrong: {result['channel_id']!r}"
        )

    def test_channel_recent_videos(self, client):
        result = client.channel(KNOWN_CHANNEL)
        assert isinstance(result["recent_videos"], list)
        for v in result["recent_videos"]:
            assert v["id"], "Recent video has no id"


# ─── CLI subprocess tests ───────────────────────────────────────────────────


@pytest.mark.e2e
class TestCLISubprocess:
    """End-to-end subprocess tests using the installed cli-web-youtube binary."""

    def test_help_loads(self, cli_cmd):
        result = _run(cli_cmd, "--help")
        assert result.returncode == 0
        assert "Usage" in result.stdout
        for group in ("search", "video", "trending", "channel"):
            assert group in result.stdout, f"Command group '{group}' missing from --help"

    def test_version_works(self, cli_cmd):
        result = _run(cli_cmd, "--version")
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_repl_exits_cleanly(self, cli_cmd):
        """REPL is the default mode; `exit` must terminate with code 0."""
        result = _run(cli_cmd, stdin="exit\n", timeout=30.0)
        assert result.returncode == 0

    def test_invalid_command_exits_nonzero(self, cli_cmd):
        result = _run(cli_cmd, "definitely-not-a-command")
        assert result.returncode != 0, "Unknown command should exit non-zero"

    def test_search_videos_json(self, cli_cmd):
        result = _run(cli_cmd, "search", "videos", "python tutorial", "--limit", "5", "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = _parse_json(result)
        assert data["query"] == "python tutorial"
        assert len(data["videos"]) >= 1, "Search returned no videos"
        first = data["videos"][0]
        assert "id" in first
        assert "title" in first
        assert len(first["id"]) == 11, "video id not 11 chars"

    def test_search_videos_no_rpc_leak(self, cli_cmd):
        result = _run(cli_cmd, "search", "videos", "python tutorial", "--limit", "5", "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        for flag in ("wrb.fr", "af.httprm"):
            assert flag not in result.stdout, f"Raw protocol data leaked: {flag}"

    def test_video_get_json(self, cli_cmd):
        result = _run(cli_cmd, "video", "get", KNOWN_VIDEO_ID, "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = _parse_json(result)
        assert data["id"] == KNOWN_VIDEO_ID
        assert data["title"], "Video title is empty"
        assert "channel" in data

    def test_video_get_accepts_url(self, cli_cmd):
        url = f"https://www.youtube.com/watch?v={KNOWN_VIDEO_ID}"
        result = _run(cli_cmd, "video", "get", url, "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = _parse_json(result)
        assert data["id"] == KNOWN_VIDEO_ID

    def test_video_get_unknown_id_json_error(self, cli_cmd):
        """Unknown video ID must exit non-zero with a structured JSON error."""
        result = _run(cli_cmd, "video", "get", "zzzzzzzzzzz", "--json")
        assert result.returncode != 0, "Unknown video should exit non-zero"
        data = _parse_json(result)
        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"

    def test_trending_list_json(self, cli_cmd):
        result = _run(cli_cmd, "trending", "list", "--limit", "5", "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = _parse_json(result)
        assert data["category"] == "now"
        assert data["count"] == len(data["videos"])
        assert len(data["videos"]) >= 1, "Trending returned no videos"

    def test_channel_get_json(self, cli_cmd):
        result = _run(cli_cmd, "channel", "get", KNOWN_CHANNEL, "--json")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = _parse_json(result)
        assert data["title"], "Channel has no title"
        assert "recent_videos" in data

    def test_global_json_flag_propagates(self, cli_cmd):
        """`--json` on the root group must apply to subcommands too."""
        result = _run(cli_cmd, "--json", "search", "videos", "python", "--limit", "3")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = _parse_json(result)
        assert "videos" in data

    def test_search_help_subcommand(self, cli_cmd):
        result = _run(cli_cmd, "search", "--help")
        assert result.returncode == 0
        assert "videos" in result.stdout

    def test_video_help_subcommand(self, cli_cmd):
        result = _run(cli_cmd, "video", "--help")
        assert result.returncode == 0
        assert "get" in result.stdout

    def test_trending_help_subcommand(self, cli_cmd):
        result = _run(cli_cmd, "trending", "--help")
        assert result.returncode == 0
        assert "list" in result.stdout

    def test_channel_help_subcommand(self, cli_cmd):
        result = _run(cli_cmd, "channel", "--help")
        assert result.returncode == 0
        assert "get" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
