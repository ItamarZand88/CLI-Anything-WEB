"""Response models for NotebookLM API data."""

from cli_web.notebooklm.core.rpc.types import (
    ARTIFACT_TYPE_LABELS,
    SOURCE_TYPE_LABELS,
)


def parse_timestamp(ts):
    """Convert [seconds, nanos] timestamp to ISO string."""
    if not ts or not isinstance(ts, list) or len(ts) < 1:
        return None
    from datetime import datetime, timezone
    try:
        secs = ts[0]
        return datetime.fromtimestamp(secs, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def parse_source(raw) -> dict:
    """Parse a source entry from notebook data."""
    if not raw or not isinstance(raw, list):
        return {}

    source_ids = raw[0] if len(raw) > 0 else []
    title = raw[1] if len(raw) > 1 else ""
    meta = raw[2] if len(raw) > 2 else []

    # source_ids can be a list of UUIDs or sometimes an int/other
    if isinstance(source_ids, list) and source_ids:
        source_id = source_ids[0]
    else:
        source_id = str(source_ids) if source_ids else None
    if not isinstance(meta, list):
        meta = []
    word_count = meta[1] if len(meta) > 1 else None
    created_ts = parse_timestamp(meta[2]) if len(meta) > 2 else None
    source_type = meta[4] if len(meta) > 4 else None
    source_url = None
    if len(meta) > 7 and isinstance(meta[7], list) and meta[7]:
        source_url = meta[7][0]

    return {
        "id": source_id,
        "title": title or "(untitled)",
        "word_count": word_count,
        "type": SOURCE_TYPE_LABELS.get(source_type, f"Unknown ({source_type})"),
        "type_code": source_type,
        "created": created_ts,
        "url": source_url,
    }


def parse_notebook(raw) -> dict:
    """Parse a notebook entry from list/get response."""
    if not raw or not isinstance(raw, list):
        return {}

    title = raw[0] if len(raw) > 0 else ""
    sources_raw = raw[1] if len(raw) > 1 and raw[1] else []
    notebook_id = raw[2] if len(raw) > 2 else None
    emoji = raw[3] if len(raw) > 3 else ""
    metadata = raw[5] if len(raw) > 5 and raw[5] else []

    sources = [parse_source(s) for s in sources_raw]

    last_modified = None
    created = None
    if metadata and len(metadata) > 5:
        last_modified = parse_timestamp(metadata[5])
    if metadata and len(metadata) > 8:
        created = parse_timestamp(metadata[8])

    return {
        "id": notebook_id,
        "title": title or "(untitled)",
        "emoji": emoji or "",
        "source_count": len(sources),
        "sources": sources,
        "last_modified": last_modified,
        "created": created,
    }


def parse_artifact(raw) -> dict:
    """Parse a studio artifact entry."""
    if not raw or not isinstance(raw, list):
        return {}

    artifact_id = raw[0] if len(raw) > 0 else None
    title = raw[1] if len(raw) > 1 else ""
    artifact_type = raw[2] if len(raw) > 2 else None
    source_refs_raw = raw[3] if len(raw) > 3 else []
    status = raw[4] if len(raw) > 4 else None

    # Extract media URL if present
    media_info = raw[6] if len(raw) > 6 and raw[6] else None
    audio_info = raw[6] if len(raw) > 6 else None
    video_info = raw[8] if len(raw) > 8 and raw[8] else None

    media_url = None
    if audio_info and isinstance(audio_info, list) and len(audio_info) > 2:
        media_url = audio_info[2]
    elif video_info and isinstance(video_info, list) and len(video_info) > 1:
        media_url = video_info[1]

    source_ids = []
    if source_refs_raw:
        for ref in source_refs_raw:
            if isinstance(ref, list) and len(ref) > 0 and isinstance(ref[0], list):
                source_ids.append(ref[0][0] if ref[0] else None)

    created_ts = None
    if len(raw) > 10 and raw[10]:
        created_ts = parse_timestamp(raw[10])
    elif len(raw) > 16 and raw[16]:
        created_ts = parse_timestamp(raw[16])

    return {
        "id": artifact_id,
        "title": title or "(untitled)",
        "type": ARTIFACT_TYPE_LABELS.get(artifact_type, f"Unknown ({artifact_type})"),
        "type_code": artifact_type,
        "source_ids": source_ids,
        "status": status,
        "media_url": media_url,
        "created": created_ts,
    }


def parse_artifact_content(raw) -> dict:
    """Extract full content from an artifact based on its type.

    Args:
        raw: The full artifact array from the gArtLc response.

    Returns:
        Dict with artifact metadata and type-specific content fields.
    """
    if not raw or not isinstance(raw, list):
        return {}

    artifact_id = raw[0] if len(raw) > 0 else None
    title = raw[1] if len(raw) > 1 else ""
    type_code = raw[2] if len(raw) > 2 else None
    type_label = ARTIFACT_TYPE_LABELS.get(type_code, f"Unknown ({type_code})")

    result = {
        "id": artifact_id,
        "title": title or "(untitled)",
        "type": type_label,
        "type_code": type_code,
    }

    def _safe_get(arr, idx, default=None):
        if arr and isinstance(arr, list) and len(arr) > idx:
            return arr[idx]
        return default

    def _parse_duration(dur):
        if dur and isinstance(dur, list) and len(dur) >= 1:
            secs = dur[0] or 0
            nanos = dur[1] if len(dur) > 1 and dur[1] else 0
            return round(secs + nanos / 1e9, 2)
        return None

    def _parse_formats(fmt_array):
        formats = []
        if fmt_array and isinstance(fmt_array, list):
            for f in fmt_array:
                if isinstance(f, list) and len(f) >= 1:
                    formats.append({
                        "url": _safe_get(f, 0),
                        "format_id": _safe_get(f, 1),
                        "mime": _safe_get(f, 2),
                    })
        return formats

    # Audio (type_code=1): content at raw[6]
    if type_code == 1:
        audio = _safe_get(raw, 6)
        if audio and isinstance(audio, list):
            result["media_url"] = _safe_get(audio, 2)
            result["media_url_alt"] = _safe_get(audio, 3)
            result["formats"] = _parse_formats(_safe_get(audio, 5))
            result["duration_seconds"] = _parse_duration(_safe_get(audio, 6))
        else:
            result["media_url"] = None
            result["formats"] = []
            result["duration_seconds"] = None

    # Video (type_code=3): content at raw[8]
    elif type_code == 3:
        video = _safe_get(raw, 8)
        if video and isinstance(video, list):
            result["media_url"] = _safe_get(video, 1)
            result["media_url_alt"] = _safe_get(video, 3)
            result["formats"] = _parse_formats(_safe_get(video, 4))
            result["duration_seconds"] = _parse_duration(_safe_get(video, 5))
        else:
            result["media_url"] = None
            result["formats"] = []
            result["duration_seconds"] = None

    # Presentation (type_code=8): content at raw[16]
    elif type_code == 8:
        pres = _safe_get(raw, 16)
        slides = []
        if pres and isinstance(pres, list):
            result["presentation_title"] = _safe_get(pres, 1)
            slides_raw = _safe_get(pres, 2)
            if slides_raw and isinstance(slides_raw, list):
                for s in slides_raw:
                    if not isinstance(s, list):
                        continue
                    img_tuple = _safe_get(s, 0)
                    slide = {
                        "image_url": _safe_get(img_tuple, 0) if isinstance(img_tuple, list) else None,
                        "width": _safe_get(img_tuple, 1) if isinstance(img_tuple, list) else None,
                        "height": _safe_get(img_tuple, 2) if isinstance(img_tuple, list) else None,
                        "description": _safe_get(s, 1),
                        "text": _safe_get(s, 2),
                    }
                    slides.append(slide)
        result["slides"] = slides

    # Quiz (type_code=4): content at raw[9] and raw[17]
    elif type_code == 4:
        quiz_config = _safe_get(raw, 9)
        quiz_state = _safe_get(raw, 17)
        result["quiz_config"] = quiz_config if quiz_config else {}
        result["quiz_state"] = quiz_state if quiz_state else {}

    return result


def parse_chat_message(raw) -> dict:
    """Parse a chat message from history."""
    if not raw or not isinstance(raw, list):
        return {}

    msg_id = raw[0] if len(raw) > 0 else None
    timestamp = parse_timestamp(raw[1]) if len(raw) > 1 else None
    role_code = raw[2] if len(raw) > 2 else None

    # Extract the text content
    text = ""
    if len(raw) > 4 and raw[4] and isinstance(raw[4], list):
        content = raw[4]
        if len(content) > 0 and isinstance(content[0], list):
            text = content[0][0] if content[0] else ""
        elif len(content) > 0 and isinstance(content[0], str):
            text = content[0]

    return {
        "id": msg_id,
        "timestamp": timestamp,
        "role": "assistant" if role_code == 2 else "user",
        "text": text,
    }
