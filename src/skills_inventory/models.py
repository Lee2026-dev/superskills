from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SkillRecord:
    name: str
    path: str
    source_root: str
    skill_md_path: str
    last_modified: str
    skill_md_hash: str
    has_conflict: bool = False
    error: str | None = None


@dataclass(slots=True)
class ConflictRecord:
    name: str
    count: int
    paths: list[str]


@dataclass(slots=True)
class Summary:
    total_skills: int = 0
    conflict_names: int = 0
    scanned_dirs: int = 0
    duration_ms: int = 0


@dataclass(slots=True)
class ScanResult:
    skills: list[SkillRecord] = field(default_factory=list)
    conflicts: list[ConflictRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)
