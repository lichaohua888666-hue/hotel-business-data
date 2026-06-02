#!/usr/bin/env python3
"""Match hotel transfer projects to anonymized customer requirements.

The matcher uses only Python's standard-library ``csv`` module. It models a
hotel site-selection consultant's first-pass judgment: commercial fit is scored,
but budget pressure, rent payment pressure, lease/legal uncertainty, and deal
execution risks can cap or block recommendations.
"""

from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECTS_CSV = ROOT_DIR / "data_sample" / "hotel_projects_sample.csv"
CUSTOMERS_CSV = ROOT_DIR / "data_sample" / "customer_requirements_sample.csv"
WORKING_CAPITAL_MONTHS = 1
HIGH_RENT_PAYMENT_MONTHS = 6


@dataclass(frozen=True)
class HotelProject:
    project_id: str
    project_name: str
    city: str
    district: str
    business_area: str
    hotel_type: str
    room_count: int
    monthly_rent: float
    transfer_fee: float
    rent_payment_terms: str
    amenities: set[str]
    meeting_space_sqm: int
    lease_years_remaining: float
    can_renew_contract: str
    landlord_written_consent: str
    license_transferable: str
    fire_safety_clear: str
    special_license_clear: str
    hidden_debt_risk: str
    employee_settlement_risk: str
    commission_clause_locked: str


@dataclass(frozen=True)
class CustomerRequirement:
    customer_id: str
    target_city: str
    target_districts: set[str]
    target_business_areas: set[str]
    min_rooms: int
    max_rooms: int
    preferred_hotel_types: set[str]
    max_budget: float
    required_amenities: set[str]
    needs_meeting_space_sqm: int
    risk_tolerance: str


@dataclass(frozen=True)
class MatchResult:
    customer_id: str
    project_id: str
    total_score: int
    recommendation_level: str
    estimated_entry_cost: float
    single_room_rent_cost: float
    matched_reasons: tuple[str, ...]
    risk_warnings: tuple[str, ...]
    missing_due_diligence_items: tuple[str, ...]
    recommended_next_action: str


def split_tokens(value: str) -> set[str]:
    """Return normalized tokens from a semicolon-delimited string."""
    return {item.strip().lower() for item in value.split(";") if item.strip()}


def normalize_flag(value: str) -> str:
    """Normalize yes/no/unclear flags while keeping sample data human-readable."""
    return value.strip().lower() or "unclear"


def parse_boolish(value: str) -> bool | None:
    """Return True, False, or None for common due-diligence status values."""
    normalized = normalize_flag(value)
    if normalized in {"yes", "y", "true", "clear", "locked", "low", "no_risk"}:
        return True
    if normalized in {"no", "n", "false", "not_clear", "unlocked", "high"}:
        return False
    return None


def parse_rent_payment_terms(value: str) -> tuple[int, int]:
    """Parse terms such as 押2付3 into deposit months and payment months."""
    match = re.search(r"押\s*(\d+)\s*付\s*(\d+)", value)
    if not match:
        return 0, 0
    return int(match.group(1)), int(match.group(2))


def calculate_initial_rent_cost(project: HotelProject) -> float:
    """Calculate upfront rent deposit/payment cost from monthly rent and terms."""
    deposit_months, payment_months = parse_rent_payment_terms(project.rent_payment_terms)
    return project.monthly_rent * (deposit_months + payment_months)


def calculate_estimated_entry_cost(project: HotelProject) -> float:
    """Estimate total takeover pressure: transfer fee, upfront rent, reserve."""
    simple_reserve = project.monthly_rent * WORKING_CAPITAL_MONTHS
    return project.transfer_fee + calculate_initial_rent_cost(project) + simple_reserve


def load_projects(path: Path = PROJECTS_CSV) -> list[HotelProject]:
    """Load hotel projects from a CSV file."""
    with path.open(newline="", encoding="utf-8") as csv_file:
        return [
            HotelProject(
                project_id=row["project_id"],
                project_name=row["project_name"],
                city=row["city"],
                district=row["district"],
                business_area=row["business_area"],
                hotel_type=row["hotel_type"].strip().lower(),
                room_count=int(row["room_count"]),
                monthly_rent=float(row["monthly_rent"]),
                transfer_fee=float(row["transfer_fee"]),
                rent_payment_terms=row["rent_payment_terms"],
                amenities=split_tokens(row["amenities"]),
                meeting_space_sqm=int(row["meeting_space_sqm"]),
                lease_years_remaining=float(row["lease_years_remaining"]),
                can_renew_contract=normalize_flag(row["can_renew_contract"]),
                landlord_written_consent=normalize_flag(row["landlord_written_consent"]),
                license_transferable=normalize_flag(row["license_transferable"]),
                fire_safety_clear=normalize_flag(row["fire_safety_clear"]),
                special_license_clear=normalize_flag(row["special_license_clear"]),
                hidden_debt_risk=normalize_flag(row["hidden_debt_risk"]),
                employee_settlement_risk=normalize_flag(row["employee_settlement_risk"]),
                commission_clause_locked=normalize_flag(row["commission_clause_locked"]),
            )
            for row in csv.DictReader(csv_file)
        ]


def load_customers(path: Path = CUSTOMERS_CSV) -> list[CustomerRequirement]:
    """Load customer requirements from a CSV file."""
    with path.open(newline="", encoding="utf-8") as csv_file:
        return [
            CustomerRequirement(
                customer_id=row["customer_id"],
                target_city=row["target_city"],
                target_districts=split_tokens(row["target_districts"]),
                target_business_areas=split_tokens(row["target_business_areas"]),
                min_rooms=int(row["min_rooms"]),
                max_rooms=int(row["max_rooms"]),
                preferred_hotel_types=split_tokens(row["preferred_hotel_types"]),
                max_budget=float(row["max_budget"]),
                required_amenities=split_tokens(row["required_amenities"]),
                needs_meeting_space_sqm=int(row["needs_meeting_space_sqm"]),
                risk_tolerance=row["risk_tolerance"].strip().lower(),
            )
            for row in csv.DictReader(csv_file)
        ]


def collect_project_risks(project: HotelProject) -> tuple[list[str], list[str]]:
    """Collect risk warnings and missing due-diligence items for a project."""
    risk_warnings: list[str] = []
    missing_items: list[str] = []

    if project.lease_years_remaining < 3:
        risk_warnings.append("remaining lease is below 3 years")
    if parse_boolish(project.landlord_written_consent) is not True:
        risk_warnings.append("landlord written consent is not confirmed")
    if parse_boolish(project.can_renew_contract) is not True:
        missing_items.append("contract renewal terms")
    if parse_boolish(project.license_transferable) is not True:
        missing_items.append("license continuity or transferability")
    if parse_boolish(project.fire_safety_clear) is not True:
        missing_items.append("fire-safety compliance status")
    if parse_boolish(project.special_license_clear) is not True:
        missing_items.append("special hotel/public-security license status")
    if project.hidden_debt_risk in {"medium", "high", "yes"}:
        risk_warnings.append(f"hidden debt risk is {project.hidden_debt_risk}")
    if project.employee_settlement_risk in {"medium", "high", "yes"}:
        risk_warnings.append(f"employee settlement risk is {project.employee_settlement_risk}")
    if parse_boolish(project.commission_clause_locked) is not True:
        risk_warnings.append("commission clause is not locked")

    return risk_warnings, missing_items


def level_from_score(score: int) -> str:
    """Map score to A-D project priority level."""
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 50:
        return "C"
    return "D"


def cap_level(level: str, cap: str) -> str:
    """Cap recommendation priority so unresolved risk cannot still receive A."""
    order = {"A": 4, "B": 3, "C": 2, "D": 1}
    return level if order[level] <= order[cap] else cap


def next_action(level: str, warnings: list[str], missing_items: list[str]) -> str:
    """Generate a practical next action for the consultant."""
    if level == "D":
        return "Do not recommend now; revisit only if budget or key risks change"
    if missing_items:
        return "Start focused due diligence before arranging customer inspection"
    if warnings:
        return "Negotiate risk remedies and written confirmations before inspection"
    if level == "A":
        return "Prioritize recommendation and arrange site inspection"
    return "Keep warm and compare against alternative projects"


def score_match(customer: CustomerRequirement, project: HotelProject) -> MatchResult | None:
    """Score a project for a customer, keeping commercially close but risky deals visible."""
    if project.city.lower() != customer.target_city.lower():
        return None

    reasons: list[str] = ["same target city"]
    risk_warnings, missing_items = collect_project_risks(project)
    score = 35

    if project.district.lower() in customer.target_districts:
        score += 12
        reasons.append("district matches")
    else:
        score -= 8
        risk_warnings.append("district is outside preferred scope")

    if project.business_area.lower() in customer.target_business_areas:
        score += 12
        reasons.append("business area matches")
    else:
        score -= 5

    if project.hotel_type in customer.preferred_hotel_types:
        score += 8
        reasons.append("hotel type matches")

    if customer.min_rooms <= project.room_count <= customer.max_rooms:
        score += 12
        reasons.append("room count is within target range")
    else:
        score -= 12
        risk_warnings.append("room count is outside target range")

    missing_amenities = customer.required_amenities - project.amenities
    if missing_amenities:
        score -= 10
        risk_warnings.append("missing required amenities: " + ", ".join(sorted(missing_amenities)))
    else:
        score += 8
        reasons.append("required amenities available")

    if project.meeting_space_sqm >= customer.needs_meeting_space_sqm:
        score += 5
        reasons.append("meeting space meets requirement")
    else:
        score -= 6
        risk_warnings.append("meeting space is below requirement")

    single_room_rent_cost = project.monthly_rent / project.room_count
    if single_room_rent_cost <= 3000:
        score += 8
        reasons.append("single-room rent cost is attractive")
    elif single_room_rent_cost <= 4500:
        score += 3
        reasons.append("single-room rent cost is acceptable")
    else:
        score -= 8
        risk_warnings.append("single-room rent cost is high")

    deposit_months, payment_months = parse_rent_payment_terms(project.rent_payment_terms)
    if deposit_months + payment_months >= HIGH_RENT_PAYMENT_MONTHS:
        score -= 6
        risk_warnings.append(
            f"high upfront rent pressure from {project.rent_payment_terms}"
        )

    estimated_entry_cost = calculate_estimated_entry_cost(project)
    if estimated_entry_cost > customer.max_budget:
        score -= 30
        risk_warnings.append("estimated entry cost exceeds customer max budget")

    score -= min(len(missing_items) * 6, 18)
    score -= min(len(risk_warnings) * 4, 20)
    total_score = max(0, min(100, score))
    level = level_from_score(total_score)

    if estimated_entry_cost > customer.max_budget:
        level = "D"
    elif missing_items or risk_warnings:
        level = cap_level(level, "B")
        if len(missing_items) + len(risk_warnings) >= 4:
            level = cap_level(level, "C")

    return MatchResult(
        customer_id=customer.customer_id,
        project_id=project.project_id,
        total_score=total_score,
        recommendation_level=level,
        estimated_entry_cost=estimated_entry_cost,
        single_room_rent_cost=single_room_rent_cost,
        matched_reasons=tuple(reasons),
        risk_warnings=tuple(risk_warnings),
        missing_due_diligence_items=tuple(missing_items),
        recommended_next_action=next_action(level, risk_warnings, missing_items),
    )


def match_customers(
    customers: Iterable[CustomerRequirement], projects: Iterable[HotelProject]
) -> list[MatchResult]:
    """Return ranked customer-to-project matches."""
    project_list = list(projects)
    results = [
        score_match(customer, project)
        for customer in customers
        for project in project_list
        if project.city.lower() == customer.target_city.lower()
    ]
    return sorted(
        (result for result in results if result is not None),
        key=lambda result: (
            result.customer_id,
            result.recommendation_level,
            -result.total_score,
            result.estimated_entry_cost,
        ),
    )


def format_money(value: float) -> str:
    """Format CNY money values without exposing any real transaction data."""
    return f"{value:.0f}"


def main() -> None:
    projects = load_projects()
    customers = load_customers()
    results = match_customers(customers, projects)

    print(f"Loaded {len(projects)} hotel projects from {PROJECTS_CSV.relative_to(ROOT_DIR)}")
    print(f"Loaded {len(customers)} customer requirements from {CUSTOMERS_CSV.relative_to(ROOT_DIR)}")
    print("\nCustomer project matches:")

    if not results:
        print("- No same-city project candidates found.")
        return

    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=[
            "customer_id",
            "project_id",
            "total_score",
            "recommendation_level",
            "estimated_entry_cost",
            "single_room_rent_cost",
            "matched_reasons",
            "risk_warnings",
            "missing_due_diligence_items",
            "recommended_next_action",
        ],
    )
    writer.writeheader()
    for result in results:
        writer.writerow(
            {
                "customer_id": result.customer_id,
                "project_id": result.project_id,
                "total_score": result.total_score,
                "recommendation_level": result.recommendation_level,
                "estimated_entry_cost": format_money(result.estimated_entry_cost),
                "single_room_rent_cost": format_money(result.single_room_rent_cost),
                "matched_reasons": "; ".join(result.matched_reasons),
                "risk_warnings": "; ".join(result.risk_warnings) or "none",
                "missing_due_diligence_items": "; ".join(result.missing_due_diligence_items) or "none",
                "recommended_next_action": result.recommended_next_action,
            }
        )


if __name__ == "__main__":
    main()
