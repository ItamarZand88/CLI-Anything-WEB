"""Typed model for the pipeline phase state (``phase-state.json``).

Mirrors the schema produced by ``cli-anything-web-plugin/scripts/phase-state.py``
exactly, so fleet tooling can reason about pipeline progress without
re-parsing ad-hoc dicts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Phase(str, Enum):
    CAPTURE = "capture"
    METHODOLOGY = "methodology"
    TESTING = "testing"
    STANDARDS = "standards"

    @classmethod
    def ordered(cls) -> list[Phase]:
        return [cls.CAPTURE, cls.METHODOLOGY, cls.TESTING, cls.STANDARDS]


class PhaseStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


@dataclass
class PhaseInfo:
    status: PhaseStatus = PhaseStatus.PENDING
    completed_at: str | None = None
    failed_at: str | None = None
    output: str | None = None
    notes: str | None = None
    error: str | None = None
    error_type: str | None = None

    _OPTIONAL = ("completed_at", "failed_at", "output", "notes", "error", "error_type")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PhaseInfo:
        return cls(
            status=PhaseStatus(raw.get("status", "pending")),
            **{k: raw.get(k) for k in cls._OPTIONAL},
        )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"status": self.status.value}
        for key in self._OPTIONAL:
            val = getattr(self, key)
            if val is not None:
                d[key] = val
        return d


@dataclass
class PipelineState:
    app_dir: str = ""
    created_at: str = ""
    phases: dict[Phase, PhaseInfo] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for phase in Phase.ordered():
            self.phases.setdefault(phase, PhaseInfo())

    @classmethod
    def load(cls, path: Path) -> PipelineState:
        raw = json.loads(path.read_text(encoding="utf-8"))
        phases = {
            Phase(name): PhaseInfo.from_dict(info)
            for name, info in raw.get("phases", {}).items()
            if name in Phase._value2member_map_
        }
        extra = {k: v for k, v in raw.items() if k not in ("app_dir", "created_at", "phases")}
        return cls(
            app_dir=raw.get("app_dir", ""),
            created_at=raw.get("created_at", ""),
            phases=phases,
            extra=extra,
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_dir": self.app_dir,
            "created_at": self.created_at,
            "phases": {p.value: info.to_dict() for p, info in self.phases.items()},
            **self.extra,
        }

    def next_phase(self) -> Phase | None:
        """First phase that is not DONE, in pipeline order."""
        for phase in Phase.ordered():
            if self.phases[phase].status is not PhaseStatus.DONE:
                return phase
        return None
