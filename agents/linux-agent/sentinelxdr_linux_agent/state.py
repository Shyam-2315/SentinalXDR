from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


class StateStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.data: dict[str, Any] = {"log_offsets": {}, "cron_mtimes": {}}

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as state_file:
                loaded = json.load(state_file)
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Unable to load state file %s: %s", self.path, exc)
            return
        if isinstance(loaded, dict):
            self.data["log_offsets"] = loaded.get("log_offsets", {})
            self.data["cron_mtimes"] = loaded.get("cron_mtimes", {})

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as state_file:
                json.dump(self.data, state_file, indent=2, sort_keys=True)
        except OSError as exc:
            LOGGER.warning("Unable to save state file %s: %s", self.path, exc)

    def get_log_offset(self, path: str) -> dict[str, int] | None:
        value = self.data.get("log_offsets", {}).get(path)
        if not isinstance(value, dict):
            return None
        try:
            return {"inode": int(value["inode"]), "offset": int(value["offset"])}
        except (KeyError, TypeError, ValueError):
            return None

    def set_log_offset(self, path: str, inode: int, offset: int) -> None:
        self.data.setdefault("log_offsets", {})[path] = {"inode": inode, "offset": offset}

    def get_cron_mtime(self, path: str) -> float | None:
        value = self.data.get("cron_mtimes", {}).get(path)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def set_cron_mtime(self, path: str, mtime: float) -> None:
        self.data.setdefault("cron_mtimes", {})[path] = mtime
