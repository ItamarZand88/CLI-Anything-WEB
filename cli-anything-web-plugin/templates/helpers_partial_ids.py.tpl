

def resolve_partial_id(partial: str, items: list[dict], key: str = "id") -> dict:
    """Resolve a partial ID prefix to a single item.

    Raises ${AppName}Error if zero or multiple matches.
    """
    from ..core.exceptions import ${AppName}Error

    matches = [item for item in items if str(item.get(key, "")).startswith(partial)]
    if len(matches) == 0:
        raise ${AppName}Error(f"No item found matching '{partial}'")
    if len(matches) > 1:
        ids = [str(m.get(key, "")) for m in matches[:5]]
        raise ${AppName}Error(f"Ambiguous ID '{partial}', matches: {', '.join(ids)}")
    return matches[0]
