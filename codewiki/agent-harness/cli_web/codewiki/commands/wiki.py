"""Wiki command group — get wiki pages and sections for a repository."""

from __future__ import annotations

import re
from pathlib import Path

import click

from ..core.client import CodeWikiClient
from ..core.exceptions import NotFoundError
from ..utils.helpers import handle_errors
from ..utils.output import print_json


# Indent prefix per heading level (level 1 = no indent, level 2 = 2 spaces, etc.)
def _indent(level: int) -> str:
    if level <= 1:
        return ""
    return "  " * (level - 1)


def _heading(level: int, title: str) -> str:
    """Return a markdown-style heading for a given level."""
    hashes = "#" * max(1, level + 1)
    return f"{hashes} {title}"


def _truncate(text: str, width: int = 50) -> str:
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


@click.group("wiki")
def wiki_group():
    """Get wiki pages and sections for a GitHub repository."""


@wiki_group.command("get")
@click.argument("repo")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def wiki_get(repo: str, as_json: bool) -> None:
    """Get full wiki content for a repo (e.g. excalidraw/excalidraw)."""
    with handle_errors(json_mode=as_json):
        client = CodeWikiClient()
        try:
            wiki = client.get_wiki(repo)
        finally:
            client.close()

        if as_json:
            print_json({"success": True, "data": wiki.to_dict()})
        else:
            commit = wiki.repo.commit_hash or "unknown"
            click.echo(f"\n{wiki.repo.slug}  @{commit}\n")
            for section in wiki.sections:
                heading = _heading(section.level, section.title)
                click.echo(heading)
                if section.content:
                    click.echo(section.content)
                click.echo()


@wiki_group.command("sections")
@click.argument("repo")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def wiki_sections(repo: str, as_json: bool) -> None:
    """List wiki sections / table of contents for a repo."""
    with handle_errors(json_mode=as_json):
        client = CodeWikiClient()
        try:
            wiki = client.get_wiki(repo)
        finally:
            client.close()

        if as_json:
            print_json({"success": True, "data": [s.to_dict() for s in wiki.sections]})
        else:
            click.echo(f"\n{wiki.repo.slug} — {len(wiki.sections)} sections\n")

            col_title = 45
            col_desc = 52

            header = f"  {'Section':<{col_title}}  {'Description':<{col_desc}}"
            click.echo(header)
            click.echo("  " + "-" * (col_title + col_desc + 2))

            for section in wiki.sections:
                indent = _indent(section.level)
                display_title = indent + section.title
                display_desc = _truncate(section.description, 50) if section.description else ""
                click.echo(f"  {display_title:<{col_title}}  {display_desc:<{col_desc}}")

            click.echo()


@wiki_group.command("section")
@click.argument("repo")
@click.argument("title")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def wiki_section(repo: str, title: str, as_json: bool) -> None:
    """Get content of a specific section by title (case-insensitive partial match)."""
    with handle_errors(json_mode=as_json):
        client = CodeWikiClient()
        try:
            wiki = client.get_wiki(repo)
        finally:
            client.close()

        query = title.lower()
        matches = [s for s in wiki.sections if query in s.title.lower()]

        if not matches:
            raise NotFoundError(f"No section matching '{title}' in {repo}")

        if len(matches) > 1:
            candidates = [s.title for s in matches]
            if as_json:
                print_json(
                    {
                        "error": True,
                        "code": "AMBIGUOUS_MATCH",
                        "message": f"Multiple sections match '{title}'",
                        "candidates": candidates,
                    }
                )
            else:
                click.echo(
                    f"Multiple sections match '{title}'. Please be more specific:\n", err=True
                )
                for s in matches:
                    click.echo(f"  {_indent(s.level)}{s.title}", err=True)
            raise SystemExit(1)

        section = matches[0]

        if as_json:
            print_json({"success": True, "data": section.to_dict()})
        else:
            heading = _heading(section.level, section.title)
            click.echo(f"\n{heading}\n")
            if section.description:
                click.echo(section.description)
                click.echo()
            if section.content:
                click.echo(section.content)
            click.echo()


def _slugify(text: str) -> str:
    """Convert a section title to a safe filename slug."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80] or "untitled"


@wiki_group.command("download")
@click.argument("repo")
@click.option(
    "--output", "-o", default=None, help="Output directory (default: <org>-<repo>-wiki/)."
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def wiki_download(repo: str, output: str | None, as_json: bool) -> None:
    """Download full wiki as organized markdown files into a folder."""
    with handle_errors(json_mode=as_json):
        client = CodeWikiClient()
        try:
            wiki = client.get_wiki(repo)
        finally:
            client.close()

        if not wiki.sections:
            raise NotFoundError(f"No wiki content found for {repo}")

        # Determine output directory
        if output:
            out_dir = Path(output)
        else:
            safe_name = repo.replace("/", "-")
            out_dir = Path(f"{safe_name}-wiki")

        out_dir.mkdir(parents=True, exist_ok=True)

        # Determine chapter split level: use level 1 if there are multiple,
        # otherwise split at level 2 (common for wikis with a single overview root)
        level_1_count = sum(1 for s in wiki.sections if s.level == 1)
        split_level = 1 if level_1_count > 1 else 2

        # Group sections into chapters at the split level
        chapters: list[tuple[int, str, list]] = []  # (index, title, sections)
        current_chapter_title = None
        current_sections: list = []
        chapter_idx = 0

        for sec in wiki.sections:
            if sec.level <= split_level:
                if current_chapter_title is not None:
                    chapters.append((chapter_idx, current_chapter_title, current_sections))
                    chapter_idx += 1
                current_chapter_title = sec.title
                current_sections = [sec]
            else:
                current_sections.append(sec)

        if current_chapter_title is not None:
            chapters.append((chapter_idx, current_chapter_title, current_sections))

        # Write index.md
        index_lines = [
            f"# {wiki.repo.slug}",
            "",
            f"Commit: `{wiki.repo.commit_hash or 'unknown'}`",
            f"Sections: {len(wiki.sections)}",
            "",
            "## Table of Contents",
            "",
        ]
        files_written = []

        for idx, chapter_title, sections in chapters:
            filename = f"{idx:02d}-{_slugify(chapter_title)}.md"
            index_lines.append(f"{idx + 1}. [{chapter_title}]({filename})")
            files_written.append(filename)

            # Write chapter file
            chapter_path = out_dir / filename
            lines = []
            for sec in sections:
                heading = "#" * max(1, sec.level)
                lines.append(f"{heading} {sec.title}")
                lines.append("")
                if sec.description and sec.description != sec.content:
                    lines.append(f"*{sec.description}*")
                    lines.append("")
                if sec.content:
                    lines.append(sec.content)
                    lines.append("")

            chapter_path.write_text("\n".join(lines), encoding="utf-8")

        index_path = out_dir / "index.md"
        index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
        files_written.insert(0, "index.md")

        if as_json:
            print_json(
                {
                    "success": True,
                    "data": {
                        "repo": repo,
                        "output_dir": str(out_dir),
                        "files": files_written,
                        "chapters": len(chapters),
                        "total_sections": len(wiki.sections),
                    },
                }
            )
        else:
            click.echo(f"\nDownloaded wiki for {wiki.repo.slug} to {out_dir}/")
            click.echo(f"  {len(chapters)} chapters, {len(wiki.sections)} sections\n")
            click.echo("  Files:")
            for f in files_written:
                click.echo(f"    {f}")
            click.echo()
