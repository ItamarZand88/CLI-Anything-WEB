"""Enforce Anthropic skill-authoring rules across every skill in the repo.

Rules from the official skill best practices + Claude Code skills reference
(see skills/standards/references/skill-authoring.md):
- frontmatter present; only known field names (hyphenated spellings)
- name: lowercase/numbers/hyphens, <= 64 chars
- description: required, third person, <= 1024 chars, no XML tags
- description + when_to_use combined <= 1536 chars (listing truncation cap)
- body <= 500 lines
- reference files linked from SKILL.md must exist (one level deep)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

KNOWN_FIELDS = {
    "name",
    "description",
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "allowed-tools",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "hooks",
    "paths",
    "shell",
    # agentskills.io open-standard optional metadata
    "version",
    "license",
}

FIRST_PERSON_RE = re.compile(r"\b(I can|I will|I'll help)\b", re.I)
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")


def _all_skill_files() -> list[Path]:
    return sorted(REPO_ROOT.glob(".claude/skills/*/SKILL.md")) + sorted(
        REPO_ROOT.glob("cli-anything-web-plugin/skills/*/SKILL.md")
    )


def _parse(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    assert m, f"{path}: missing YAML frontmatter"
    fields: dict[str, str] = {}
    current_key = None
    for line in m.group(1).splitlines():
        if line.startswith((" ", "\t")) and current_key:
            fields[current_key] += " " + line.strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            current_key = key.strip()
            fields[current_key] = value.strip().lstrip(">|").strip()
    return fields, text[m.end() :]


SKILLS = _all_skill_files()


def test_skills_discovered():
    assert len(SKILLS) >= 25, f"expected the full skill set, found {len(SKILLS)}"


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_frontmatter_fields_are_known(path: Path):
    fields, _ = _parse(path)
    unknown = set(fields) - KNOWN_FIELDS
    assert not unknown, (
        f"{path.parent.name}: unknown frontmatter fields {sorted(unknown)} — "
        "misspelled fields are silently ignored by Claude Code"
    )


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_name_is_valid(path: Path):
    fields, _ = _parse(path)
    name = fields.get("name", path.parent.name)
    assert NAME_RE.fullmatch(name), f"{path.parent.name}: invalid name {name!r}"


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_description_quality(path: Path):
    fields, _ = _parse(path)
    desc = fields.get("description", "")
    assert desc, f"{path.parent.name}: missing description"
    assert len(desc) <= 1024, f"{path.parent.name}: description {len(desc)} chars > 1024"
    assert (
        "<" not in desc
        or ">" not in desc.replace("->", "").replace("=>", "")
        or not re.search(r"<[a-zA-Z][^>]*>", desc)
    ), f"{path.parent.name}: description contains XML tags"
    assert not FIRST_PERSON_RE.search(desc), f"{path.parent.name}: description must be third person"
    combined = desc + fields.get("when_to_use", "")
    assert len(combined) <= 1536, (
        f"{path.parent.name}: description+when_to_use {len(combined)} chars > 1536 listing cap"
    )


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_body_within_limit(path: Path):
    _, body = _parse(path)
    lines = len(body.splitlines())
    assert lines <= 500, (
        f"{path.parent.name}: body {lines} lines > 500 — split into reference files"
    )


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_local_reference_links_exist(path: Path):
    """Files linked from SKILL.md must exist (progressive disclosure integrity)."""
    _, body = _parse(path)
    for match in re.finditer(r"\[[^\]]*\]\((?!https?://|#)([^)]+)\)", body):
        target = match.group(1).split("#")[0].strip()
        if not target:
            continue
        resolved = (path.parent / target).resolve()
        assert resolved.exists(), f"{path.parent.name}: broken reference link {target!r}"


# ── Reference-file rules (progressive disclosure) ───────────────────────────

REFERENCE_FILES = sorted(
    REPO_ROOT.glob("cli-anything-web-plugin/skills/*/references/*.md")
) + sorted(REPO_ROOT.glob("cli-anything-web-plugin/skills/shared/*.md"))


def test_reference_files_discovered():
    assert len(REFERENCE_FILES) >= 15


@pytest.mark.parametrize("path", REFERENCE_FILES, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_long_reference_files_have_toc(path: Path):
    """References >100 lines need a table of contents (partial-read safety)."""
    text = path.read_text(encoding="utf-8")
    if len(text.splitlines()) <= 100:
        pytest.skip("under 100 lines")
    head = "\n".join(text.splitlines()[:30]).lower()
    assert "## contents" in head, f"{path.name}: >100 lines but no '## Contents' TOC near the top"


@pytest.mark.parametrize("path", REFERENCE_FILES, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_references_stay_one_level_deep(path: Path):
    """Reference files must not link to other reference files (nested chains)."""
    if path.parent.name == "shared":
        pytest.skip("shared specs are linked from many places by design")
    text = path.read_text(encoding="utf-8")
    nested = re.findall(r"\]\((?:\./)?references/[^)]+\)|`references/[^`]+\.md`", text)
    assert not nested, (
        f"{path.name}: links to other references {nested} — keep chains one level deep"
    )
