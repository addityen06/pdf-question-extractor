#!/usr/bin/env python3
"""
Export CSVs Only
===============================
Extracts all `.csv` files from `textPapers/` into `textPapersCSV/`
preserving the exact course-code directory structure with only CSV files.

Usage:
    /Users/adhithyanm.a/Desktop/Papers/.venv/bin/python scripts/export_csvs.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def export_csvs(
    source_dir: Path | str = PROJECT_ROOT / "textPapers",
    target_dir: Path | str = PROJECT_ROOT / "textPapersCSV"
) -> int:
    source_path = Path(source_dir)
    target_path = Path(target_dir)

    if not source_path.exists():
        print(f"Source directory does not exist: {source_path}")
        return 0

    target_path.mkdir(parents=True, exist_ok=True)
    count = 0

    for csv_file in sorted(source_path.glob("*/*.csv")):
        course_code = csv_file.parent.name
        course_target_dir = target_path / course_code
        course_target_dir.mkdir(parents=True, exist_ok=True)
        dest_file = course_target_dir / csv_file.name
        shutil.copy2(csv_file, dest_file)
        count += 1

    print(f"Successfully exported {count} CSV files to {target_path}")
    return count


if __name__ == "__main__":
    export_csvs()
