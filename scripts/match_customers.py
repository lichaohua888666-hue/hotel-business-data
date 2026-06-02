#!/usr/bin/env python3
"""Match sample hotel projects to sample customer requirements.

The script reads two CSV files from ``data_sample`` and prints ranked matches for
each customer. It intentionally uses only Python's standard library so it can run
in a minimal environment.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECTS_CSV = ROOT_DIR / "data_sample" / "hotel_projects_sample.csv"
CUSTOMERS_CSV = ROOT_DIR / "data_sample" / "customer_requirements_sample.csv"


@dataclass(frozen=True)
class HotelProject:
    project_id: str
    hotel_name: str
    city: str
    country: str
    star_rating: int
    room_count: int
    meeting_space_sqm: int
    amenities: set[str]
    average_daily_rate_usd: float


@dataclass(frozen=True)
class CustomerRequirement:
    customer_id: str
    customer_name: str
    target_city: str
    min_star_rating: int
    min_rooms: int
    needs_meeting_space_sqm: int
    required_amenities: set[str]
    max_average_daily_rate_usd: float


@dataclass(frozen=True)
class MatchResult:
    customer: CustomerRequirement
    project: HotelProject
    score: int
    reasons: tuple[str, ...]


def split_amenities(value: str) -> set[str]:
    """Return normalized amenity tokens from a semicolon-delimited string."""
    return {item.strip().lower() for item in value.split(";") if item.strip()}


def load_projects(path: Path = PROJECTS_CSV) -> list[HotelProject]:
    """Load hotel projects from a CSV file."""
    with path.open(newline="", encoding="utf-8") as csv_file:
        return [
            HotelProject(
                project_id=row["project_id"],
                hotel_name=row["hotel_name"],
                city=row["city"],
                country=row["country"],
                star_rating=int(row["star_rating"]),
                room_count=int(row["room_count"]),
                meeting_space_sqm=int(row["meeting_space_sqm"]),
                amenities=split_amenities(row["amenities"]),
                average_daily_rate_usd=float(row["average_daily_rate_usd"]),
            )
            for row in csv.DictReader(csv_file)
        ]


def load_customers(path: Path = CUSTOMERS_CSV) -> list[CustomerRequirement]:
    """Load customer requirements from a CSV file."""
    with path.open(newline="", encoding="utf-8") as csv_file:
        return [
            CustomerRequirement(
                customer_id=row["customer_id"],
                customer_name=row["customer_name"],
                target_city=row["target_city"],
                min_star_rating=int(row["min_star_rating"]),
                min_rooms=int(row["min_rooms"]),
                needs_meeting_space_sqm=int(row["needs_meeting_space_sqm"]),
                required_amenities=split_amenities(row["required_amenities"]),
                max_average_daily_rate_usd=float(row["max_average_daily_rate_usd"]),
            )
            for row in csv.DictReader(csv_file)
        ]


def score_match(customer: CustomerRequirement, project: HotelProject) -> MatchResult | None:
    """Score a project for a customer, or return None when hard criteria fail."""
    if project.city.lower() != customer.target_city.lower():
        return None

    missing_amenities = customer.required_amenities - project.amenities
    if missing_amenities:
        return None

    reasons: list[str] = ["same city", "required amenities available"]
    score = 40

    if project.star_rating >= customer.min_star_rating:
        score += 15
        reasons.append("star rating meets requirement")
    else:
        return None

    if project.room_count >= customer.min_rooms:
        score += 15
        reasons.append("room count meets requirement")
    else:
        return None

    if project.meeting_space_sqm >= customer.needs_meeting_space_sqm:
        score += 15
        reasons.append("meeting space meets requirement")
    else:
        return None

    if project.average_daily_rate_usd <= customer.max_average_daily_rate_usd:
        score += 15
        reasons.append("rate is within budget")
    else:
        return None

    return MatchResult(customer=customer, project=project, score=score, reasons=tuple(reasons))


def match_customers(
    customers: Iterable[CustomerRequirement], projects: Iterable[HotelProject]
) -> list[MatchResult]:
    """Return ranked customer-to-project matches."""
    projects_list = list(projects)
    customers_list = list(customers)

    results: list[MatchResult] = []
    compared_pairs = 0
    for customer in customers_list:
        for project in projects_list:
            compared_pairs += 1
            result = score_match(customer, project)
            if result is not None:
                results.append(result)

    expected_pairs = len(customers_list) * len(projects_list)
    if compared_pairs != expected_pairs:
        raise RuntimeError(
            "Customer matching did not compare every customer against every project: "
            f"compared {compared_pairs} pairs, expected {expected_pairs}."
        )

    return sorted(
        results,
        key=lambda result: (
            result.customer.customer_id,
            -result.score,
            result.project.average_daily_rate_usd,
        ),
    )


def main() -> None:
    projects = load_projects()
    customers = load_customers()
    results = match_customers(customers, projects)

    print(f"Loaded {len(projects)} hotel projects from {PROJECTS_CSV.relative_to(ROOT_DIR)}")
    print(f"Loaded {len(customers)} customer requirements from {CUSTOMERS_CSV.relative_to(ROOT_DIR)}")
    print("\nCustomer matches:")

    if not results:
        print("- No matches found.")
        return

    for result in results:
        print(
            f"- {result.customer.customer_id} {result.customer.customer_name}: "
            f"{result.project.hotel_name} ({result.project.project_id}) "
            f"score={result.score}; reasons={', '.join(result.reasons)}"
        )


if __name__ == "__main__":
    main()
