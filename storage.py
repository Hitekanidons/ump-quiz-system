
"""JSON persistence layer for the quiz system."""
from __future__ import annotations

import json
import threading
import tempfile
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "users": [],
    "modules": [],
    "quizzes": [],
    "attempts": [],
}


class DataStore:
    """A simple JSON-backed store with atomic writes and a process-wide lock."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.paths = {name: self.base_dir / f"{name}.json" for name in DEFAULTS}

        # Ensure every JSON file exists, even on the very first run.
        for name, default_value in DEFAULTS.items():
            if not self.paths[name].exists():
                self.save(name, default_value)

    def load(self, name: str) -> Any:
        """Load a collection from disk. If the file is missing, return its default."""
        path = self.paths[name]
        with self._lock:
            if not path.exists():
                return DEFAULTS[name]
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)

    def save(self, name: str, data: Any) -> None:
        """Atomically save a collection to disk so data is not partially written."""
        path = self.paths[name]
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=path.stem + "_", suffix=".tmp", dir=str(path.parent))
            temp_path = Path(temp_name)
            try:
                with open(fd, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
                temp_path.replace(path)
            finally:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass

    def reset_all(self) -> None:
        """Clear all data files. Used only for testing."""
        for name, default_value in DEFAULTS.items():
            self.save(name, default_value)
