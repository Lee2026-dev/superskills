from __future__ import annotations

import json
from pathlib import Path

from .models import ScanResult, scan_result_to_dict


def print_summary(result: ScanResult) -> None:
    print(
        f"total_skills={result.summary.total_skills} "
        f"conflict_names={result.summary.conflict_names} "
        f"scanned_dirs={result.summary.scanned_dirs} "
        f"duration_ms={result.summary.duration_ms}"
    )
    print("skills:")
    if result.skills:
        for skill in sorted(result.skills, key=lambda item: (item.name, item.path)):
            print(
                f"- {skill.name} | conflict={skill.has_conflict} "
                f"| source={skill.source_root} | path={skill.path}"
            )
    else:
        print("- (none)")

    if result.conflicts:
        print("conflicts:")
        for item in result.conflicts:
            joined_paths = "; ".join(item.paths)
            print(f"- {item.name} ({item.count}): {joined_paths}")


def write_json(result: ScanResult, output_path: Path, scan_roots: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = scan_result_to_dict(result, scan_roots=scan_roots)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
