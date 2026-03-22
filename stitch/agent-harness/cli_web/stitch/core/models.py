"""Data models and response parsers for Stitch."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Project:
    id: str  # numeric ID extracted from resource_name
    resource_name: str  # "projects/<id>"
    title: Optional[str] = None
    created_at: Optional[float] = None  # epoch seconds
    modified_at: Optional[float] = None
    status: int = 0
    thumbnail_url: Optional[str] = None
    theme_mode: Optional[int] = None  # 1=light, 2=dark
    owner: bool = True


@dataclass
class Screen:
    id: str
    name: str = ""
    description: str = ""
    resource_name: str = ""
    thumbnail_url: Optional[str] = None
    html_url: Optional[str] = None
    agent_name: str = ""
    width: int = 0
    height: int = 0


@dataclass
class Session:
    id: str
    resource_name: str
    prompt: str = ""
    status: Optional[int] = None  # None=pending, 1=started, 2=completed
    explanation: str = ""
    screens: list = field(default_factory=list)
    timestamp: Optional[float] = None


@dataclass
class User:
    id: str
    name: str = ""
    avatar_url: Optional[str] = None


def _safe_get(data, index, default=None):
    """Safely index into a list, returning default if out of bounds or None."""
    try:
        if data is None:
            return default
        val = data[index]
        return val if val is not None else default
    except (IndexError, TypeError, KeyError):
        return default


def parse_project(raw: list) -> Optional[Project]:
    """Parse a project entry from batchexecute response.

    Response structure:
        [0] = resource_name "projects/<id>"
        [1] = title
        [2] = type (2)
        [3] = created timestamp [seconds, nanoseconds]
        [4] = modified timestamp [seconds, nanoseconds]
        [5] = status (4 = ready)
        [6] = thumbnail [file_resource, null, image_url]
        [7] = owner flag (1)
        [8] = theme mode
    """
    if not raw or not isinstance(raw, list):
        return None
    try:
        resource_name = _safe_get(raw, 0, "")
        if not resource_name:
            return None

        # Extract numeric ID from "projects/<id>"
        project_id = resource_name.split("/")[-1] if "/" in str(resource_name) else str(resource_name)

        title = _safe_get(raw, 1)

        # Timestamps: [seconds, nanoseconds]
        created_raw = _safe_get(raw, 3)
        created_at = float(created_raw[0]) if created_raw and isinstance(created_raw, list) and len(created_raw) > 0 else None

        modified_raw = _safe_get(raw, 4)
        modified_at = float(modified_raw[0]) if modified_raw and isinstance(modified_raw, list) and len(modified_raw) > 0 else None

        status = _safe_get(raw, 5, 0)

        # Thumbnail: [file_resource, null, image_url]
        thumb_raw = _safe_get(raw, 6)
        thumbnail_url = None
        if thumb_raw and isinstance(thumb_raw, list) and len(thumb_raw) > 2:
            thumbnail_url = _safe_get(thumb_raw, 2)

        owner_flag = _safe_get(raw, 7, 0)
        theme_mode = _safe_get(raw, 8)

        return Project(
            id=project_id,
            resource_name=resource_name,
            title=title,
            created_at=created_at,
            modified_at=modified_at,
            status=status if isinstance(status, int) else 0,
            thumbnail_url=thumbnail_url,
            theme_mode=theme_mode,
            owner=bool(owner_flag),
        )
    except Exception:
        return None


def parse_screen(raw: list) -> Optional[Screen]:
    """Parse a screen entry from batchexecute response.

    Response structure:
        [0] = thumbnail [file_resource, null, thumbnail_url]
        [1] = html_file [file_resource, null, download_url, null, null, "text/html"]
        [4] = screen_id
        [5] = agent_name
        [6] = width
        [7] = height
        [8] = screen_name
        [9] = description
        [10] = screen_resource_name
    """
    if not raw or not isinstance(raw, list):
        return None
    try:
        screen_id = _safe_get(raw, 4)
        if not screen_id:
            return None

        # Thumbnail URL
        thumb_raw = _safe_get(raw, 0)
        thumbnail_url = None
        if thumb_raw and isinstance(thumb_raw, list) and len(thumb_raw) > 2:
            thumbnail_url = _safe_get(thumb_raw, 2)

        # HTML download URL
        html_raw = _safe_get(raw, 1)
        html_url = None
        if html_raw and isinstance(html_raw, list) and len(html_raw) > 2:
            html_url = _safe_get(html_raw, 2)

        return Screen(
            id=str(screen_id),
            name=_safe_get(raw, 8, "") or "",
            description=_safe_get(raw, 9, "") or "",
            resource_name=_safe_get(raw, 10, "") or "",
            thumbnail_url=thumbnail_url,
            html_url=html_url,
            agent_name=_safe_get(raw, 5, "") or "",
            width=_safe_get(raw, 6, 0) or 0,
            height=_safe_get(raw, 7, 0) or 0,
        )
    except Exception:
        return None


def parse_session(raw: list) -> Optional[Session]:
    """Parse a session entry from batchexecute response.

    Response structure (from traffic analysis):
        [0] = session resource_name (e.g., "projects/<pid>/sessions/<sid>")
        [2] = status (None=pending, 1=started, 2=completed)
        [3] = prompt info: [prompt_text, ...]
        [4] = results array (screens + AI explanation)
        [5] = timestamp [seconds, ...]
    """
    if not raw or not isinstance(raw, list):
        return None
    try:
        resource_name = _safe_get(raw, 0)
        if not resource_name or not isinstance(resource_name, str):
            return None

        # Extract session ID from resource name
        session_id = resource_name.split("/")[-1] if "/" in str(resource_name) else str(resource_name)

        status = _safe_get(raw, 2)

        # Prompt is in [3][0]
        prompt_info = _safe_get(raw, 3)
        prompt = ""
        if isinstance(prompt_info, list) and len(prompt_info) > 0:
            prompt = str(prompt_info[0]) if prompt_info[0] else ""
        elif isinstance(prompt_info, str):
            prompt = prompt_info

        # Results/explanation in [4]
        results = _safe_get(raw, 4)
        explanation = ""
        screens = []
        if isinstance(results, list):
            # Try to find explanation text and screens within results
            for item in results:
                if isinstance(item, str) and len(item) > 10:
                    explanation = item
                elif isinstance(item, list):
                    for sub in item:
                        if isinstance(sub, list):
                            screen = parse_screen(sub)
                            if screen:
                                screens.append(screen)

        # Timestamp in [5]
        timestamp = _safe_get(raw, 5)
        if isinstance(timestamp, list) and len(timestamp) > 0:
            timestamp = float(timestamp[0])
        elif not isinstance(timestamp, (int, float)):
            timestamp = None

        return Session(
            id=session_id,
            resource_name=str(resource_name),
            prompt=prompt,
            status=status if isinstance(status, int) else None,
            explanation=explanation,
            screens=screens,
            timestamp=timestamp,
        )
    except Exception:
        return None
