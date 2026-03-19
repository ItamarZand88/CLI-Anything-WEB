"""Output formatting for cli-web-github (JSON and human-readable tables)."""

from __future__ import annotations

import json
import sys
from typing import Any


def _safe(text: str, width: int = 0) -> str:
    """Truncate text to width and replace un-encodable characters."""
    if width:
        text = text[:width]
    encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding)


def print_json(data: Any) -> None:
    """Print data as formatted JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def print_error_json(error: Exception) -> None:
    """Print an error as JSON."""
    from cli_web.gh_trending.core.exceptions import AppError

    if isinstance(error, AppError):
        print_json(error.to_dict())
    else:
        print_json({"error": True, "code": "UNKNOWN_ERROR", "message": str(error)})


def print_repos_table(repos: list) -> None:
    """Print repos as a human-readable table."""
    if not repos:
        print("No trending repositories found.")
        return

    # Column widths
    col_rank = 4
    col_repo = 40
    col_lang = 14
    col_stars = 8
    col_today = 12

    header = (
        f"{'#':<{col_rank}} "
        f"{'Repository':<{col_repo}} "
        f"{'Language':<{col_lang}} "
        f"{'Stars':>{col_stars}} "
        f"{'Today':>{col_today}}"
    )
    print(header)
    print("-" * len(header))

    for repo in repos:
        lang = _safe(repo.language or "", col_lang)
        repo_name = _safe(repo.full_name, col_repo)
        print(
            f"{repo.rank:<{col_rank}} "
            f"{repo_name:<{col_repo}} "
            f"{lang:<{col_lang}} "
            f"{repo.stars:>{col_stars},} "
            f"{repo.stars_today:>{col_today},}"
        )


def print_developers_table(developers: list) -> None:
    """Print developers as a human-readable table."""
    if not developers:
        print("No trending developers found.")
        return

    col_rank = 4
    col_login = 20
    col_name = 25
    col_repo = 40

    header = (
        f"{'#':<{col_rank}} "
        f"{'Login':<{col_login}} "
        f"{'Name':<{col_name}} "
        f"{'Popular Repo':<{col_repo}}"
    )
    print(header)
    print("-" * len(header))

    for dev in developers:
        name = _safe(dev.name or "", col_name)
        login = _safe(dev.login, col_login)
        repo = _safe(dev.popular_repo or "", col_repo)
        print(
            f"{dev.rank:<{col_rank}} "
            f"{login:<{col_login}} "
            f"{name:<{col_name}} "
            f"{repo:<{col_repo}}"
        )
