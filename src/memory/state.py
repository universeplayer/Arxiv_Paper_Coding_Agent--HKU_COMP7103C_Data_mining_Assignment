"""Shared project memory for coordinating agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

Message = dict[str, str]


@dataclass(slots=True)
class MemoryEntry:
    """Single memory unit recorded by an agent."""

    agent: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ProjectMemory:
    """Lightweight memory buffer used across agents."""

    def __init__(self) -> None:
        self.entries: list[MemoryEntry] = []
        self.artifacts: dict[str, Path] = {}
        self.metrics: dict[str, Any] = {}

    def add(self, agent: str, content: str) -> None:
        self.entries.append(MemoryEntry(agent=agent, content=content))

    def last_messages(self, limit: int = 6) -> list[Message]:
        recent = self.entries[-limit:]
        return [
            {"role": "system", "content": f"[{entry.agent}] {entry.content}"}
            for entry in recent
        ]

    def remember_artifact(self, name: str, path: Path) -> None:
        self.artifacts[name] = path

    def get_artifact(self, name: str) -> Path | None:
        return self.artifacts.get(name)

    def set_metric(self, key: str, value: Any) -> None:
        self.metrics[key] = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [entry.__dict__ for entry in self.entries],
            "artifacts": {k: str(v) for k, v in self.artifacts.items()},
            "metrics": self.metrics,
        }

