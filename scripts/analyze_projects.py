#!/usr/bin/env python3
"""Analyze the sample hotel project data."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECTS_CSV = ROOT_DIR / "data_sample" / "hotel_projects_sample.csv"


def main() -> None:
    with PROJECTS_CSV.open(newline="", encoding="utf-8") as csv_file:
        projects = list(csv.DictReader(csv_file))

    city_counts = Counter(project["city"] for project in projects)
    total_rooms = sum(int(project["room_count"]) for project in projects)
    average_rate = sum(float(project["average_daily_rate_usd"]) for project in projects) / len(projects)

    print(f"Loaded {len(projects)} hotel projects from {PROJECTS_CSV.relative_to(ROOT_DIR)}")
    print(f"Total rooms: {total_rooms}")
    print(f"Average daily rate: ${average_rate:.2f}")
    print("Projects by city:")
    for city, count in sorted(city_counts.items()):
        print(f"- {city}: {count}")


if __name__ == "__main__":
    main()
