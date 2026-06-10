"""``api-spec.json`` — the typed intermediate representation per CLI.

Phase 2 of the pipeline produces this machine-readable spec from captured
traffic (instead of prose alone). Everything downstream derives from it:
client method stubs, command skeletons, REPL help, the gap analyzer, and
the traffic-fidelity review (which becomes a deterministic spec-vs-traffic
diff with provenance links into ``raw-traffic.json``).

Format: JSON (stdlib-parseable everywhere — devkit has no dependencies).

Schema (version 1)::

    {
      "spec_version": 1,
      "app": "hackernews",
      "protocol": "rest",
      "auth": {"type": "cookie", "required_cookies": ["user"]},
      "endpoints": [
        {
          "id": "search_stories",
          "method": "GET",
          "url": "https://hn.algolia.com/api/v1/search",
          "params": {"query": {"type": "str", "required": true}},
          "evidence": "raw-traffic.json#42"
        }
      ],
      "commands": [
        {"name": "search stories", "endpoint": "search_stories"}
      ]
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SPEC_VERSION = 1
SPEC_FILENAME = "api-spec.json"

_VALID_PROTOCOLS = {"rest", "graphql", "html-scraping", "batchexecute", "browser"}
_VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}
_VALID_AUTH = {"none", "cookie", "api-key", "google_sso", "browser"}


def validate_spec(raw: dict[str, Any]) -> list[str]:
    """Return a list of problems (empty == valid)."""
    problems: list[str] = []

    if raw.get("spec_version") != SPEC_VERSION:
        problems.append(f"spec_version must be {SPEC_VERSION}, got {raw.get('spec_version')!r}")
    if not raw.get("app"):
        problems.append("missing 'app'")
    if raw.get("protocol") not in _VALID_PROTOCOLS:
        problems.append(f"protocol must be one of {sorted(_VALID_PROTOCOLS)}")

    auth = raw.get("auth")
    if not isinstance(auth, dict) or auth.get("type") not in _VALID_AUTH:
        problems.append(f"auth.type must be one of {sorted(_VALID_AUTH)}")

    endpoint_ids: set[str] = set()
    endpoints = raw.get("endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        problems.append("endpoints must be a non-empty list")
        endpoints = []
    for i, ep in enumerate(endpoints):
        where = f"endpoints[{i}]"
        if not isinstance(ep, dict):
            problems.append(f"{where}: not an object")
            continue
        ep_id = ep.get("id")
        if not ep_id:
            problems.append(f"{where}: missing id")
        elif ep_id in endpoint_ids:
            problems.append(f"{where}: duplicate id {ep_id!r}")
        else:
            endpoint_ids.add(ep_id)
        if ep.get("method") not in _VALID_METHODS:
            problems.append(f"{where}: invalid method {ep.get('method')!r}")
        if not ep.get("url"):
            problems.append(f"{where}: missing url")
        if not ep.get("evidence"):
            problems.append(
                f"{where}: missing evidence — every endpoint must cite its captured "
                "traffic entry (raw-traffic.json#<index>); never invent endpoints"
            )

    for i, cmd in enumerate(raw.get("commands", [])):
        where = f"commands[{i}]"
        if not isinstance(cmd, dict) or not cmd.get("name"):
            problems.append(f"{where}: missing name")
            continue
        endpoint_ref = cmd.get("endpoint")
        if endpoint_ref and endpoint_ref not in endpoint_ids:
            problems.append(f"{where}: references unknown endpoint {endpoint_ref!r}")

    return problems


def validate_file(path: Path) -> list[str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: unreadable: {exc}"]
    if not isinstance(raw, dict):
        return [f"{path}: spec must be a JSON object"]
    return validate_spec(raw)
