from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict


DEFAULT_CACHE_DIR = Path("~/.agents").expanduser()
DEFAULT_CACHE_FILE = DEFAULT_CACHE_DIR / "superskills_cache.json"

class CacheManager:
    def __init__(self, cache_file: Path | None = None):
        self.cache_file = cache_file or DEFAULT_CACHE_FILE
        self.data: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.data = {}

    def save(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def get(self, path: str) -> Dict[str, Any] | None:
        return self.data.get(path)

    def set(self, path: str, metadata: Dict[str, Any]) -> None:
        self.data[path] = metadata

    def is_git_fetch_expired(self, path: str, ttl_seconds: int = 600) -> bool:
        entry = self.get(path)
        if not entry:
            return True
        last_fetch = entry.get("last_git_fetch_ts", 0)
        return (time.time() - last_fetch) > ttl_seconds
