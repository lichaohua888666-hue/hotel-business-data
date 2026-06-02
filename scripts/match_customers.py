#!/usr/bin/env python3
"""Match anonymized customer requirements with hotel project samples.

The script intentionally uses only Python's standard library and reads sample
CSV files from data_sample/. It does not contain customer names, phone numbers,
WeChat IDs, or real commission details.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECTS_PATH = ROOT_DIR / "data_sample" / "hotel_projects_sample.csv"
CUSTOMERS_PATH = ROOT_DIR / "data_sample" / "customer_requirements_sample.csv"


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(float((value or "").strip()))
    except ValueError:
        return default


def parse_bool(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "是", "接受"}


def parse_multi_value(value: str) -> set[str]:
    return {item.strip() for item in (value or "").split(";") if item.strip()}


def add_score(
    score: int,
    reasons: List[str],
    points: int,
    reason: str,
) -> int:
    reasons.append(f"+{points} {reason}")
    return score + points


def score_match(customer: Dict[str, str], project: Dict[str, str]) -> Tuple[int, List[str], List[str]]:
    score = 0
    reasons: List[str] = []
    warnings: List[str] = []

    if customer["preferred_city"].strip() == project["city"].strip():
        score = add_score(score, reasons, 20, "city matched")

    preferred_districts = parse_multi_value(customer["preferred_districts"])
    if project["district"].strip() in preferred_districts:
        score = add_score(score, reasons, 20, "district matched")

    preferred_business_areas = parse_multi_value(customer["preferred_business_areas"])
    if project["business_area"].strip() in preferred_business_areas:
        score = add_score(score, reasons, 15, "business area matched")

    room_count = parse_int(project["room_count"])
    min_rooms = parse_int(customer["min_room_count"])
    max_rooms = parse_int(customer["max_room_count"])
    if min_rooms <= room_count <= max_rooms:
        score = add_score(score, reasons, 15, "room count within preferred range")

    single_room_rent_cost = parse_int(project["single_room_rent_cost"])
    max_single_room_rent_cost = parse_int(customer["max_single_room_rent_cost"])
    if single_room_rent_cost <= max_single_room_rent_cost:
        score = add_score(score, reasons, 20, "single room rent cost within limit")
    else:
        warnings.append("single room rent cost exceeds customer limit")

    transfer_fee = parse_int(project["transfer_fee"])
    accepts_transfer_fee = parse_bool(customer["accepts_transfer_fee"])
    max_transfer_fee = parse_int(customer["max_transfer_fee"])
    if transfer_fee > 0 and not accepts_transfer_fee:
        score -= 25
        reasons.append("-25 transfer fee not accepted")
        warnings.append("customer does not accept transfer fee")
    elif transfer_fee <= max_transfer_fee:
        score = add_score(score, reasons, 15, "transfer fee within budget")
    else:
        warnings.append("transfer fee exceeds customer budget")

    license_status = project["license_status"].strip().lower()
    accepts_unknown_license_risk = parse_bool(customer["accepts_unknown_license_risk"])
    if license_status == "unknown" and not accepts_unknown_license_risk:
        warnings.append("unknown license risk not accepted")
    else:
        score = add_score(score, reasons, 10, "license risk acceptable")

    commission_risk = project["commission_risk"].strip().lower()
    accepts_medium_commission_risk = parse_bool(customer["accepts_medium_commission_risk"])
    if commission_risk == "medium" and not accepts_medium_commission_risk:
        score -= 30
        reasons.append("-30 medium commission risk not accepted")
        warnings.append("medium commission risk not accepted")
    else:
        score = add_score(score, reasons, 10, "commission risk acceptable")

    return score, reasons, warnings


def recommended_next_action(customer: Dict[str, str], project: Dict[str, str], warnings: Iterable[str]) -> str:
    warning_list = list(warnings)
    if warning_list:
        return f"{customer['next_action']}; review risks for {project['project_id']}"
    return f"{customer['next_action']}; {project['suggested_next_action']}"


def main() -> None:
    projects = read_csv(PROJECTS_PATH)
    customers = read_csv(CUSTOMERS_PATH)

    fieldnames = [
        "customer_id",
        "project_id",
        "total_score",
        "matched_reasons",
        "risk_warnings",
        "recommended_next_action",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    for customer in customers:
        scored_projects = []
        for project in projects:
            score, reasons, warnings = score_match(customer, project)
            scored_projects.append((score, project, reasons, warnings))

        scored_projects.sort(key=lambda item: item[0], reverse=True)
        for score, project, reasons, warnings in scored_projects:
            writer.writerow(
                {
                    "customer_id": customer["customer_id"],
                    "project_id": project["project_id"],
                    "total_score": score,
                    "matched_reasons": "; ".join(reasons) or "no positive match",
                    "risk_warnings": "; ".join(warnings) or "none",
                    "recommended_next_action": recommended_next_action(customer, project, warnings),
                }
            )


if __name__ == "__main__":
    main()
