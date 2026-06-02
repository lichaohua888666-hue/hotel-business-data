#!/usr/bin/env python3
"""Analyze the anonymized sample hotel project data."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECTS_CSV = ROOT_DIR / "data_sample" / "hotel_projects_sample.csv"


def parse_terms(value: str) -> tuple[int, int]:
    """Parse a rent term like 押2付3 without third-party dependencies."""
    compact = value.replace(" ", "")
    if "押" not in compact or "付" not in compact:
        return 0, 0
    deposit_text = compact.split("押", 1)[1].split("付", 1)[0]
    payment_text = compact.split("付", 1)[1]
    return int(deposit_text), int(payment_text)


def main() -> None:
    with PROJECTS_CSV.open(newline="", encoding="utf-8") as csv_file:
        projects = list(csv.DictReader(csv_file))

    city_counts = Counter(project["city"] for project in projects)
    total_rooms = sum(int(project["room_count"]) for project in projects)
    average_monthly_rent = sum(float(project["monthly_rent"]) for project in projects) / len(projects)
    average_single_room_rent = sum(
        float(project["monthly_rent"]) / int(project["room_count"]) for project in projects
    ) / len(projects)
    high_pressure_count = sum(
        1
        for project in projects
        if sum(parse_terms(project["rent_payment_terms"])) >= 6
    )

    print(f"Loaded {len(projects)} hotel projects from {PROJECTS_CSV.relative_to(ROOT_DIR)}")
    print(f"Total rooms: {total_rooms}")
    print(f"Average monthly rent: CNY {average_monthly_rent:.0f}")
    print(f"Average single-room rent cost: CNY {average_single_room_rent:.0f}")
    print(f"High upfront rent-pressure projects: {high_pressure_count}")
    print("Projects by city:")
    for city, count in sorted(city_counts.items()):
        print(f"- {city}: {count}")


if __name__ == "__main__":
    main()
