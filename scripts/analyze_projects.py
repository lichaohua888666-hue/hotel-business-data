#!/usr/bin/env python3
"""Analyze synthetic hotel project samples without third-party dependencies."""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA_PATH = PROJECT_ROOT / "data_sample" / "hotel_projects_sample.csv"

REQUIRED_FIELDS = [
    "project_id",
    "project_name",
    "city",
    "district",
    "business_area",
    "area_sqm",
    "monthly_rent",
    "monthly_property_fee",
    "room_count",
    "bright_room_count",
    "dark_room_count",
    "transfer_fee",
    "contract_years",
    "rent_payment_terms",
    "is_operating",
    "license_status",
    "fire_safety_status",
    "special_industry_license_status",
    "landlord_written_consent",
    "commission_risk",
    "current_stage",
    "next_action",
]


def read_money_or_count(row: dict[str, str], field_name: str) -> Decimal:
    """Read a numeric CSV field as Decimal and raise a clear error if invalid."""
    raw_value = row.get(field_name, "").strip()
    try:
        return Decimal(raw_value)
    except InvalidOperation as exc:
        project_id = row.get("project_id", "未知项目")
        raise ValueError(f"{project_id} 的 {field_name} 不是有效数字：{raw_value}") from exc


def calculate_daily_room_rent_cost(row: dict[str, str]) -> Decimal:
    """Calculate (monthly rent + monthly property fee) / room count / 30."""
    monthly_rent = read_money_or_count(row, "monthly_rent")
    monthly_property_fee = read_money_or_count(row, "monthly_property_fee")
    room_count = read_money_or_count(row, "room_count")
    if room_count <= 0:
        project_id = row.get("project_id", "未知项目")
        raise ValueError(f"{project_id} 的 room_count 必须大于 0")

    return ((monthly_rent + monthly_property_fee) / room_count / Decimal("30")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def judge_rent_pressure(daily_room_rent_cost: Decimal) -> str:
    if daily_room_rent_cost <= Decimal("35"):
        return "租金压力低"
    if daily_room_rent_cost <= Decimal("55"):
        return "租金压力中"
    return "租金压力高"


def judge_license_fire_risk(row: dict[str, str]) -> str:
    risk_fields = [
        "license_status",
        "fire_safety_status",
        "special_industry_license_status",
    ]
    if any(row.get(field_name, "").strip() == "不明" for field_name in risk_fields):
        return "风险中"
    return "风险低"


def judge_commission_risk(row: dict[str, str]) -> str:
    commission_risk = row.get("commission_risk", "").strip()
    if commission_risk != "低":
        return f"需要谨慎推进（当前：{commission_risk or '未填写'}）"
    return "低"


def should_prioritize(
    rent_pressure: str,
    license_fire_risk: str,
    commission_risk_judgement: str,
    row: dict[str, str],
) -> str:
    landlord_written_consent = row.get("landlord_written_consent", "").strip()
    if (
        rent_pressure != "租金压力高"
        and license_fire_risk == "风险低"
        and commission_risk_judgement == "低"
        and landlord_written_consent == "是"
    ):
        return "是"
    return "否"


def validate_header(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("样例数据为空，未读取到 CSV 表头")

    missing_fields = [field_name for field_name in REQUIRED_FIELDS if field_name not in fieldnames]
    if missing_fields:
        raise ValueError("样例数据缺少必填字段：" + "、".join(missing_fields))


def analyze_projects() -> None:
    with SAMPLE_DATA_PATH.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        validate_header(reader.fieldnames)

        for row in reader:
            daily_room_rent_cost = calculate_daily_room_rent_cost(row)
            rent_pressure = judge_rent_pressure(daily_room_rent_cost)
            license_fire_risk = judge_license_fire_risk(row)
            commission_risk_judgement = judge_commission_risk(row)
            prioritize = should_prioritize(
                rent_pressure,
                license_fire_risk,
                commission_risk_judgement,
                row,
            )

            print(f"项目编号：{row['project_id']}")
            print(f"项目名称：{row['project_name']}")
            print(f"单房租金成本：{daily_room_rent_cost} 元/间/天")
            print(f"租金压力判断：{rent_pressure}")
            print(f"证照消防风险：{license_fire_risk}")
            print(f"佣金风险：{commission_risk_judgement}")
            print(f"是否值得优先推进：{prioritize}")
            print(f"下一步动作：{row['next_action']}")
            print("-" * 40)


if __name__ == "__main__":
    analyze_projects()
