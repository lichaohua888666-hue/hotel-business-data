#!/usr/bin/env python3
"""Analyze the sample hotel acquisition project data."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECTS_CSV = ROOT_DIR / "data_sample" / "hotel_projects_sample.csv"


def parse_float(value: str) -> float:
    return float(value.strip() or 0)


def main() -> None:
    with PROJECTS_CSV.open(newline="", encoding="utf-8") as csv_file:
        projects = list(csv.DictReader(csv_file))

    city_counts = Counter(project["city"] for project in projects)
    total_rooms = sum(int(project["room_count"]) for project in projects)
    average_monthly_rent = sum(parse_float(project["monthly_rent"]) for project in projects) / len(projects)
    average_transfer_fee = sum(parse_float(project["transfer_fee"]) for project in projects) / len(projects)
    unclear_fire_count = sum(1 for project in projects if project["fire_safety_clear"].strip() == "待确认")
    unlocked_commission_count = sum(
        1 for project in projects if project["commission_clause_locked"].strip() != "是"
    )

    print(f"Loaded {len(projects)} hotel projects from {PROJECTS_CSV.relative_to(ROOT_DIR)}")
    print(f"Total rooms: {total_rooms}")
    print(f"Average monthly rent: {average_monthly_rent:,.0f}")
    print(f"Average transfer fee: {average_transfer_fee:,.0f}")
    print(f"Projects with unclear fire safety: {unclear_fire_count}")
    print(f"Projects with unlocked commission clauses: {unlocked_commission_count}")
    print("Projects by city:")
    for city, count in sorted(city_counts.items()):
        print(f"- {city}: {count}")


if __name__ == "__main__":
    main()
