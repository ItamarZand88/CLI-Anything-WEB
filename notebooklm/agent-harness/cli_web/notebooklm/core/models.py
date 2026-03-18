"""Data models for NotebookLM CLI."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Notebook:
    id: str
    title: str
    emoji: str = "📓"
    created_at: Optional[int] = None  # Unix timestamp
    updated_at: Optional[int] = None  # Unix timestamp
    source_count: int = 0
    is_pinned: bool = False

    def display_title(self) -> str:
        return f"{self.emoji} {self.title}" if self.emoji else self.title


@dataclass
class Source:
    id: str
    name: str
    source_type: str = "unknown"  # "url", "text", "pdf"
    url: Optional[str] = None
    char_count: int = 0
    created_at: Optional[int] = None  # Unix timestamp


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str


@dataclass
class Artifact:
    id: str
    artifact_type: str  # "mindmap", "notes", "briefing"
    content: str  # JSON string for mindmap, text for notes
    title: Optional[str] = None


@dataclass
class User:
    email: str
    display_name: str
    avatar_url: Optional[str] = None


@dataclass
class AudioType:
    type_id: int
    name: str
    description: str


def parse_notebook(raw: list) -> Optional[Notebook]:
    """Parse a notebook object from the raw batchexecute response.

    The raw structure from wXbhsf/CCqFvf/rLM1Ne is:
    [
        ["", null, uuid, "", null, [flags...]],
        ["title", sources_list_or_None],  -- optional in some responses
        ...
    ]
    Or for single-notebook responses (rLM1Ne/s0tc2d):
    ["", null, uuid, "", null, [flags...], ...]
    as the top-level entry.
    """
    if not raw or not isinstance(raw, list):
        return None

    try:
        # Single notebook from rLM1Ne/s0tc2d: list starts with "" or uuid
        # List entry from wXbhsf: raw[0] is the header sub-array
        if isinstance(raw[0], list):
            # wXbhsf-style: [[header], [title, sources], ...]
            header = raw[0]
            title_block = raw[1] if len(raw) > 1 else None

            nb_id = header[2] if len(header) > 2 else None
            if not nb_id:
                return None

            flags = header[5] if len(header) > 5 else []
            is_pinned = bool(flags[0]) if flags and isinstance(flags, list) and len(flags) > 0 else False
            created_sec = flags[5][0] if (flags and len(flags) > 5 and isinstance(flags[5], list)) else None
            updated_sec = flags[8][0] if (flags and len(flags) > 8 and isinstance(flags[8], list)) else None
            emoji = header[3] if len(header) > 3 and isinstance(header[3], str) and header[3] else "📓"

            title = ""
            source_count = 0
            if title_block and isinstance(title_block, list):
                title = title_block[0] if title_block[0] else ""
                sources = title_block[1] if len(title_block) > 1 and isinstance(title_block[1], list) else []
                source_count = len(sources)
        else:
            # rLM1Ne-style: [title, sources_list, uuid, emoji?, ...]
            # result[0] = [title_str, [[source1], [source2], ...], notebook_id, ...]
            title = raw[0] if isinstance(raw[0], str) else ""
            sources = raw[1] if len(raw) > 1 and isinstance(raw[1], list) else []
            source_count = len(sources)
            nb_id = raw[2] if len(raw) > 2 and isinstance(raw[2], str) else None
            if not nb_id:
                return None
            emoji = raw[3] if len(raw) > 3 and isinstance(raw[3], str) and raw[3] else "📓"
            flags = raw[5] if len(raw) > 5 and isinstance(raw[5], list) else []
            is_pinned = bool(flags[0]) if flags and isinstance(flags, list) else False
            created_sec = flags[5][0] if (flags and len(flags) > 5 and isinstance(flags[5], list)) else None
            updated_sec = flags[8][0] if (flags and len(flags) > 8 and isinstance(flags[8], list)) else None

        return Notebook(
            id=nb_id,
            title=title,
            emoji=emoji,
            created_at=created_sec,
            updated_at=updated_sec,
            source_count=source_count,
            is_pinned=is_pinned,
        )
    except (IndexError, TypeError):
        return None


def parse_source(raw: list) -> Optional[Source]:
    """Parse a source object from the raw batchexecute response.

    Source structure from izAoDd:
    [[source_id], name, [null, char_count, [ts_sec, ts_ns], [id2, [ts2_sec, ts2_ns]], type_id, null, 1, [urls]], [null, 2]]
    """
    if not raw or not isinstance(raw, list):
        return None
    try:
        id_arr = raw[0]
        src_id = id_arr[0] if isinstance(id_arr, list) else id_arr
        name = raw[1] if len(raw) > 1 else ""
        meta = raw[2] if len(raw) > 2 else []

        char_count = meta[1] if isinstance(meta, list) and len(meta) > 1 else 0
        created_sec = meta[2][0] if (isinstance(meta, list) and len(meta) > 2 and isinstance(meta[2], list)) else None
        type_id = meta[4] if isinstance(meta, list) and len(meta) > 4 else None
        urls = meta[7] if isinstance(meta, list) and len(meta) > 7 and isinstance(meta[7], list) else []

        # type_id: 4=text, 5=url, 11=url (wikipedia), 8=text
        src_type_map = {4: "text", 5: "url", 8: "text", 11: "url"}
        src_type = src_type_map.get(type_id, "unknown")
        url = urls[0] if urls else None

        return Source(
            id=str(src_id),
            name=name,
            source_type=src_type,
            url=url,
            char_count=char_count or 0,
            created_at=created_sec,
        )
    except (IndexError, TypeError):
        return None


def parse_user(raw: list) -> Optional[User]:
    """Parse user info from JFMDGd response.

    Structure: [[[email, 1, [], ["Display Name", "avatar_url"]]], null, 1000]
    """
    if not raw or not isinstance(raw, list):
        return None
    try:
        users = raw[0]
        if not users or not isinstance(users, list):
            return None
        user_entry = users[0]
        email = user_entry[0]
        profile = user_entry[3] if len(user_entry) > 3 else []
        display_name = profile[0] if profile and len(profile) > 0 else ""
        avatar_url = profile[1] if profile and len(profile) > 1 else None
        return User(email=email, display_name=display_name, avatar_url=avatar_url)
    except (IndexError, TypeError):
        return None
