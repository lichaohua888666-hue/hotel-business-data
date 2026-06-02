#!/usr/bin/env python3
"""Minimal environment check for the hotel-business-data workspace."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_PATHS = [
    "README.md",
    "AGENTS.md",
    "requirements.txt",
    "scripts/test_env.py",
    ".gitignore",
    "data_sample",
    "output",
]

REQUIRED_MODULES: list[str] = []
SAMPLE_FILE = Path("data_sample/hotel_bookings_sample.csv")
OUTPUT_FILE = Path("output/env_check.json")
FORBIDDEN_COLUMNS = {"phone", "phone_number", "customer_phone", "commission", "commission_amount"}


def require_paths(repo_root: Path) -> list[str]:
    missing = [path for path in REQUIRED_PATHS if not (repo_root / path).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required paths: {', '.join(missing)}")
    return REQUIRED_PATHS


def require_modules() -> dict[str, str]:
    """Return versions for required third-party modules.

    The minimal runnable check intentionally has no third-party dependencies so it
    can pass in restricted Codex cloud environments.
    """
    return {}


def validate_sample(repo_root: Path) -> dict[str, object]:
    import csv

    sample_path = repo_root / SAMPLE_FILE
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample file not found: {sample_path}")

    with sample_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        forbidden_found = sorted(FORBIDDEN_COLUMNS.intersection({column.lower() for column in fieldnames}))
        if forbidden_found:
            raise ValueError(f"Forbidden sensitive columns found in sample data: {forbidden_found}")

        required_columns = {"booking_id", "hotel_code", "stay_month", "room_nights", "room_revenue_usd"}
        missing_columns = sorted(required_columns.difference(fieldnames))
        if missing_columns:
            raise ValueError(f"Sample data is missing required columns: {missing_columns}")

        rows = list(reader)

    total_room_nights = sum(int(row["room_nights"]) for row in rows)
    total_room_revenue = sum(float(row["room_revenue_usd"]) for row in rows)

    return {
        "sample_file": str(SAMPLE_FILE),
        "rows": len(rows),
        "total_room_nights": total_room_nights,
        "total_room_revenue_usd": round(total_room_revenue, 2),
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    checked_paths = require_paths(repo_root)
    module_versions = require_modules()
    sample_summary = validate_sample(repo_root)

    result = {
        "status": "ok",
        "python": sys.version.split()[0],
        "checked_paths": checked_paths,
        "modules": module_versions,
        "sample_summary": sample_summary,
    }

    output_path = repo_root / OUTPUT_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
