#!/usr/bin/env python3
"""Validate that required sample data files are present and readable."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ROOT_DIR / "data_sample" / "hotel_projects_sample.csv",
    ROOT_DIR / "data_sample" / "customer_requirements_sample.csv",
]


def main() -> None:
    for path in REQUIRED_FILES:
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open("r", newline="", encoding="utf-8") as csv_file:
            rows = list(csv.DictReader(csv_file))
        print(f"ok: {path.relative_to(ROOT_DIR)} rows={len(rows)}")


if __name__ == "__main__":
    main()
