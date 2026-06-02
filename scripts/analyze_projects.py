#!/usr/bin/env python3
"""Analyze the sample hotel transfer/lease project data."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECTS_CSV = ROOT_DIR / "data_sample" / "hotel_projects_sample.csv"


def parse_float(value: str) -> float:
    return float(value.strip() or 0)


def parse_int(value: str) -> int:
    return int(float(value.strip() or 0))


def is_unknown(value: str) -> bool:
    return value.strip().lower() in {"待确认", "未知", "不明", "需核验", "unknown", "tbc", "pending", ""}


def main() -> None:
    with PROJECTS_CSV.open(newline="", encoding="utf-8") as csv_file:
        projects = list(csv.DictReader(csv_file))

    city_counts = Counter(project["city"] for project in projects)
    district_counts = Counter(project["district"] for project in projects)
    total_rooms = sum(parse_int(project["room_count"]) for project in projects)
    total_bright_rooms = sum(parse_int(project["bright_room_count"]) for project in projects)
    average_monthly_rent = sum(parse_float(project["monthly_rent"]) for project in projects) / len(projects)
    average_transfer_fee = sum(parse_float(project["transfer_fee"]) for project in projects) / len(projects)
    average_remaining_lease = (
        sum(parse_float(project["lease_years_remaining"]) for project in projects) / len(projects)
    )
    unclear_license_count = sum(
        1
        for project in projects
        if any(
            is_unknown(project[field])
            for field in ("license_status", "fire_safety_status", "special_industry_license_status")
        )
    )
    short_lease_count = sum(
        1 for project in projects if parse_float(project["lease_years_remaining"]) < 3
    )
    no_landlord_consent_count = sum(
        1 for project in projects if project["landlord_written_consent"].strip() != "是"
    )
    unlocked_commission_count = sum(
        1 for project in projects if project["commission_clause_locked"].strip() != "是"
    )

    print(f"Loaded {len(projects)} hotel transfer/lease projects from {PROJECTS_CSV.relative_to(ROOT_DIR)}")
    print(f"Total rooms: {total_rooms}")
    print(f"Bright room ratio: {total_bright_rooms / total_rooms:.1%}")
    print(f"Average monthly rent: {average_monthly_rent:,.0f}")
    print(f"Average transfer fee: {average_transfer_fee:,.0f}")
    print(f"Average remaining lease years: {average_remaining_lease:.1f}")
    print(f"Projects with any unclear license/fire/special-industry item: {unclear_license_count}")
    print(f"Projects with lease years remaining below 3: {short_lease_count}")
    print(f"Projects without clear landlord written consent: {no_landlord_consent_count}")
    print(f"Projects with unlocked commission clauses: {unlocked_commission_count}")
    print("Projects by city:")
    for city, count in sorted(city_counts.items()):
        print(f"- {city}: {count}")
    print("Projects by district:")
    for district, count in sorted(district_counts.items()):
        print(f"- {district}: {count}")


if __name__ == "__main__":
    main()
