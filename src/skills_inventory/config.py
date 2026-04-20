from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path("~/.agents/superskills_config.json")

class ConfigManager:
    DEFAULT_ROOTS = [
        "~/.codex",
        "~/.agents",
        "~/.skills",
        "~/.gemini",
        "~/.hermes",
        "~/.openclaw",
        "~/skills",
    ]
    DEFAULT_IGNORED = [".git", "node_modules", "__pycache__", ".venv"]

    def __init__(self, config_path: Path | None = None):
        self.path = (config_path or DEFAULT_CONFIG_PATH).expanduser()
        self.config: dict[str, Any] = {
            "version": "1.0",
            "scan_roots": list(self.DEFAULT_ROOTS),
            "ignored_dirs": list(self.DEFAULT_IGNORED),
        }
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Merge or overwrite? The user wants to "add" and "ignore", 
                    # but if they have a config file, we respect it as the definitive source.
                    if "scan_roots" in data:
                        self.config["scan_roots"] = data["scan_roots"]
                    if "ignored_dirs" in data:
                        self.config["ignored_dirs"] = data["ignored_dirs"]
        except (json.JSONDecodeError, OSError):
            # Fallback to defaults on error
            pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get_roots(self) -> list[Path]:
        return [Path(p).expanduser() for p in self.config.get("scan_roots", [])]

    def get_ignored(self) -> set[str]:
        return set(self.config.get("ignored_dirs", []))

    def add_root(self, path: str) -> bool:
        roots = self.config.get("scan_roots", [])
        if path not in roots:
            roots.append(path)
            self.config["scan_roots"] = roots
            self.save()
            return True
        return False

    def remove_root(self, path: str) -> bool:
        roots = self.config.get("scan_roots", [])
        if path in roots:
            roots.remove(path)
            self.config["scan_roots"] = roots
            self.save()
            return True
        return False

    def add_ignore(self, name: str) -> bool:
        ignored = self.config.get("ignored_dirs", [])
        if name not in ignored:
            ignored.append(name)
            self.config["ignored_dirs"] = ignored
            self.save()
            return True
        return False

    def remove_ignore(self, name: str) -> bool:
        ignored = self.config.get("ignored_dirs", [])
        if name in ignored:
            ignored.remove(name)
            self.config["ignored_dirs"] = ignored
            self.save()
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return dict(self.config)
