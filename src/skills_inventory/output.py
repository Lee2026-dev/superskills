from __future__ import annotations

import json
from pathlib import Path

from .models import ScanResult, scan_result_to_dict


MAX_CELL_WIDTH = 80


def _clip(text: str, max_len: int = MAX_CELL_WIDTH) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    normalized_rows = [[_clip(cell) for cell in row] for row in rows]
    if not normalized_rows:
        normalized_rows = [["(none)"] + [""] * (len(headers) - 1)]

    widths = [len(header) for header in headers]
    for row in normalized_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    sep = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    header_line = "| " + " | ".join(header.ljust(widths[i]) for i, header in enumerate(headers)) + " |"
    row_lines = ["| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " |" for row in normalized_rows]
    return "\n".join([sep, header_line, sep, *row_lines, sep])


def print_summary(result: ScanResult) -> None:
    print(
        f"total_skills={result.summary.total_skills} "
        f"conflict_names={result.summary.conflict_names} "
        f"scanned_dirs={result.summary.scanned_dirs} "
        f"duration_ms={result.summary.duration_ms}"
    )
    skill_rows = [
        [
            skill.name,
            skill.current_version,
            skill.latest_version,
            "Yes" if skill.has_conflict else "No",
            skill.source_root,
            skill.path,
        ]
        for skill in sorted(result.skills, key=lambda item: (item.name, item.path))
    ]
    print("skills:")
    print(
        _render_table(
            ["Name", "Current Version", "Latest Version", "Conflict", "Source Root", "Path"],
            skill_rows,
        )
    )

    conflict_rows = [
        [item.name, str(item.count), "; ".join(item.paths)]
        for item in sorted(result.conflicts, key=lambda entry: entry.name)
    ]
    print("conflicts:")
    print(_render_table(["Name", "Count", "Paths"], conflict_rows))


def write_json(result: ScanResult, output_path: Path, scan_roots: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = scan_result_to_dict(result, scan_roots=scan_roots)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
