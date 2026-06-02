#!/usr/bin/env python3
"""Analyze anonymized hotel project sample data with the Python standard library."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECTS_PATH = ROOT_DIR / "data_sample" / "hotel_projects_sample.csv"


def parse_int(value: str) -> int:
    try:
        return int(float((value or "0").strip()))
    except ValueError:
        return 0


def main() -> None:
    with PROJECTS_PATH.open("r", newline="", encoding="utf-8") as csv_file:
        projects = list(csv.DictReader(csv_file))

    city_counts = Counter(project["city"] for project in projects)
    total_rooms = sum(parse_int(project["room_count"]) for project in projects)
    average_room_cost = 0
    if projects:
        average_room_cost = round(
            sum(parse_int(project["single_room_rent_cost"]) for project in projects) / len(projects),
            2,
        )

    print(f"project_count: {len(projects)}")
    print(f"total_rooms: {total_rooms}")
    print(f"average_single_room_rent_cost: {average_room_cost}")
    print("city_distribution:")
    for city, count in sorted(city_counts.items()):
        print(f"- {city}: {count}")


if __name__ == "__main__":
    main()
