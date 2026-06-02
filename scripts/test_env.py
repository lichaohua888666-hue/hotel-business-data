#!/usr/bin/env python3
"""Lightweight environment check for the sample data scripts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ROOT_DIR / "data_sample" / "hotel_projects_sample.csv",
    ROOT_DIR / "data_sample" / "customer_requirements_sample.csv",
    ROOT_DIR / "scripts" / "match_customers.py",
    ROOT_DIR / "scripts" / "analyze_projects.py",
]


def main() -> None:
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version.split()[0]}")
    print("Required files:")

    missing_files = []
    for file_path in REQUIRED_FILES:
        status = "OK" if file_path.exists() else "MISSING"
        print(f"- {file_path.relative_to(ROOT_DIR)}: {status}")
        if status == "MISSING":
            missing_files.append(file_path)

    if missing_files:
        raise SystemExit(1)

    print("Environment check passed.")


if __name__ == "__main__":
    main()
