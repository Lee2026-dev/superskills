from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class SkillRecord:
    name: str
    path: str
    source_root: str
    skill_md_path: str
    last_modified: str
    skill_md_hash: str
    current_version: str = "unknown"
    latest_version: str = "unknown"
    is_symlink: bool = False
    has_conflict: bool = False
    error: str | None = None


@dataclass
class ConflictRecord:
    name: str
    count: int
    paths: list[str]


@dataclass
class Summary:
    total_skills: int = 0
    conflict_names: int = 0
    scanned_dirs: int = 0
    duration_ms: int = 0


@dataclass
class ScanResult:
    skills: list[SkillRecord] = field(default_factory=list)
    conflicts: list[ConflictRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)


def scan_result_to_dict(result: ScanResult, scan_roots: list[str]) -> dict:
    return {
        "schema_version": "1.1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "scan_roots": scan_roots,
        "settings": {
            "recursive": True,
            "follow_symlinks": True,
            "ignored_dirs": [".git", "node_modules", "__pycache__", ".venv"],
        },
        "summary": asdict(result.summary),
        "skills": [asdict(item) for item in result.skills],
        "conflicts": [asdict(item) for item in result.conflicts],
    }
