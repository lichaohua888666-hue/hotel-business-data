#!/usr/bin/env python3
"""Basic environment smoke test for the hotel business data sample project."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA_PATH = PROJECT_ROOT / "data_sample" / "hotel_projects_sample.csv"
ANALYSIS_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "analyze_projects.py"


def main() -> None:
    print(f"Python version: {sys.version.split()[0]}")
    print(f"Sample data exists: {SAMPLE_DATA_PATH.exists()}")
    print(f"Analysis script exists: {ANALYSIS_SCRIPT_PATH.exists()}")

    with SAMPLE_DATA_PATH.open("r", encoding="utf-8", newline="") as csv_file:
        row_count = sum(1 for _ in csv.DictReader(csv_file))

    print(f"Sample project rows: {row_count}")
    if row_count == 0:
        raise SystemExit("No sample project rows found")


if __name__ == "__main__":
    main()
