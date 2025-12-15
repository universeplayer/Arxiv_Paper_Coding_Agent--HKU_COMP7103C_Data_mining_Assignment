"""Utility helpers for loading multiple OpenAI API keys."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class APIKeyRecord:
    """Represents a single key entry parsed from the manifest file."""

    label: str
    key: str


class APIKeyManager:
    """Loads and validates API keys stored in a plaintext manifest."""

    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"API key file not found: {self.path}")
        self.records = self._load()
        if not self.records:
            raise ValueError(f"No valid API keys found in {self.path}")

    def _load(self) -> list[APIKeyRecord]:
        records: list[APIKeyRecord] = []
        for idx, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            key = parts[-1]
            if not key.startswith("sk-"):
                continue
            label = parts[0] if len(parts) > 1 else f"key-{idx}"
            records.append(APIKeyRecord(label=label, key=key))
        return records

    def keys(self) -> list[str]:
        """Return the list of API key strings."""

        return [record.key for record in self.records]

