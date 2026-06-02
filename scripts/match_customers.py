#!/usr/bin/env python3
"""Match hotel acquisition projects to customer requirements.

The script models a lightweight version of how hotel site-selection advisors
screen transfer projects: first estimate entry pressure, then combine location,
room-count fit, rent efficiency, and due-diligence risks into a recommendation
level. It intentionally uses only Python's standard library.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECTS_CSV = ROOT_DIR / "data_sample" / "hotel_projects_sample.csv"
CUSTOMERS_CSV = ROOT_DIR / "data_sample" / "customer_requirements_sample.csv"

HIGH_PAYMENT_MONTHS = 8
LOW_RENT_COST_PER_ROOM = 2_500
MEDIUM_RENT_COST_PER_ROOM = 4_000
DEFAULT_RENT_PAYMENT_TERMS = (2, 3)


@dataclass(frozen=True)
class RentPaymentTerms:
    deposit_months: int
    payment_months: int

    @property
    def upfront_months(self) -> int:
        return self.deposit_months + self.payment_months


@dataclass(frozen=True)
class HotelProject:
    project_id: str
    hotel_name: str
    city: str
    district: str
    business_area: str
    room_count: int
    transfer_fee: float
    monthly_rent: float
    rent_payment_terms: RentPaymentTerms
    business_tags: set[str]
    lease_years_remaining: float
    can_renew_contract: str
    landlord_written_consent: str
    license_transferable: str
    fire_safety_clear: str
    special_license_clear: str
    hidden_debt_risk: str
    employee_settlement_risk: str
    commission_clause_locked: str

    @property
    def first_rent_payment_cost(self) -> float:
        return self.monthly_rent * self.rent_payment_terms.upfront_months

    @property
    def reserve_fund(self) -> float:
        """A simple reserve for handover buffer, minor fixes, and working capital."""
        return max(self.monthly_rent * 2, self.transfer_fee * 0.05, 100_000)

    @property
    def estimated_entry_cost(self) -> float:
        return self.transfer_fee + self.first_rent_payment_cost + self.reserve_fund

    @property
    def single_room_rent_cost(self) -> float:
        if self.room_count <= 0:
            return 0
        return self.monthly_rent / self.room_count


@dataclass(frozen=True)
class CustomerRequirement:
    customer_id: str
    target_city: str
    preferred_districts: set[str]
    preferred_business_areas: set[str]
    min_rooms: int
    max_rooms: int
    max_budget: float
    required_business_tags: set[str]


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


def parse_float(value: str) -> float:
    return float(value.strip() or 0)


def parse_int(value: str) -> int:
    return int(float(value.strip() or 0))


def normalize_status(value: str) -> str:
    return value.strip().lower() or "待确认"


def is_yes(value: str) -> bool:
    return normalize_status(value) in {"是", "yes", "y", "true", "1", "clear", "locked"}


def is_no(value: str) -> bool:
    return normalize_status(value) in {"否", "no", "n", "false", "0", "不", "未"}


def is_unknown(value: str) -> bool:
    return normalize_status(value) in {"待确认", "未知", "不明", "unknown", "tbc", "pending", ""}


def parse_rent_payment_terms(value: str) -> RentPaymentTerms:
    """Parse terms such as 押2付3, 押1付3, or 押3付6."""
    match = re.search(r"押\s*(\d+)\s*付\s*(\d+)", value or "")
    if not match:
        deposit_months, payment_months = DEFAULT_RENT_PAYMENT_TERMS
        return RentPaymentTerms(deposit_months=deposit_months, payment_months=payment_months)
    return RentPaymentTerms(deposit_months=int(match.group(1)), payment_months=int(match.group(2)))


def format_money(value: float) -> str:
    return f"{value:,.0f}"


def load_projects(path: Path = PROJECTS_CSV) -> list[HotelProject]:
    """Load hotel projects from a CSV file."""
    with path.open(newline="", encoding="utf-8") as csv_file:
        return [
            HotelProject(
                project_id=row["project_id"],
                hotel_name=row["hotel_name"],
                city=row["city"],
                district=row["district"],
                business_area=row["business_area"],
                room_count=parse_int(row["room_count"]),
                transfer_fee=parse_float(row["transfer_fee"]),
                monthly_rent=parse_float(row["monthly_rent"]),
                rent_payment_terms=parse_rent_payment_terms(row["rent_payment_terms"]),
                business_tags=split_tokens(row["business_tags"]),
                lease_years_remaining=parse_float(row["lease_years_remaining"]),
                can_renew_contract=normalize_status(row["can_renew_contract"]),
                landlord_written_consent=normalize_status(row["landlord_written_consent"]),
                license_transferable=normalize_status(row["license_transferable"]),
                fire_safety_clear=normalize_status(row["fire_safety_clear"]),
                special_license_clear=normalize_status(row["special_license_clear"]),
                hidden_debt_risk=normalize_status(row["hidden_debt_risk"]),
                employee_settlement_risk=normalize_status(row["employee_settlement_risk"]),
                commission_clause_locked=normalize_status(row["commission_clause_locked"]),
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
                preferred_districts=split_tokens(row["preferred_districts"]),
                preferred_business_areas=split_tokens(row["preferred_business_areas"]),
                min_rooms=parse_int(row["min_rooms"]),
                max_rooms=parse_int(row["max_rooms"]),
                max_budget=parse_float(row["max_budget"]),
                required_business_tags=split_tokens(row["required_business_tags"]),
            )
            for row in csv.DictReader(csv_file)
        ]


def collect_due_diligence(project: HotelProject) -> tuple[list[str], list[str]]:
    """Return risk warnings and missing due-diligence items for a project."""
    risk_warnings: list[str] = []
    missing_items: list[str] = []

    if project.lease_years_remaining < 3:
        risk_warnings.append("剩余租期低于3年，续约或摊销周期存在压力")

    if not is_yes(project.landlord_written_consent):
        risk_warnings.append("业主未提供明确书面同意，转让落地存在关键障碍")

    if not is_yes(project.commission_clause_locked):
        risk_warnings.append("佣金条款未锁死，需先确认居间费触发条件和支付节点")

    if is_yes(project.hidden_debt_risk) or project.hidden_debt_risk in {"中", "高", "待确认"}:
        risk_warnings.append(f"隐性债务风险为{project.hidden_debt_risk}，需核验欠款和担保")

    if project.employee_settlement_risk in {"中", "高", "待确认"}:
        risk_warnings.append(f"员工安置风险为{project.employee_settlement_risk}，需确认补偿和留用方案")

    if is_no(project.can_renew_contract):
        risk_warnings.append("合同不可续签，后续经营年限受限")
    elif is_unknown(project.can_renew_contract):
        missing_items.append("续签条件待确认")

    if is_unknown(project.license_transferable):
        missing_items.append("证照是否可延续待确认")
    elif is_no(project.license_transferable):
        risk_warnings.append("证照不可延续，需重新办证或调整交易结构")

    if is_unknown(project.fire_safety_clear):
        missing_items.append("消防合规状态待确认")
    elif is_no(project.fire_safety_clear):
        risk_warnings.append("消防不明确或不通过，需整改评估")

    if is_unknown(project.special_license_clear):
        missing_items.append("特行许可状态待确认")
    elif is_no(project.special_license_clear):
        risk_warnings.append("特行许可不明确或不可延续，需先核验主管部门口径")

    return risk_warnings, missing_items


def recommendation_level(score: int, over_budget: bool, risk_count: int, missing_count: int) -> str:
    """Convert score and gating risks into advisor-style project priority."""
    if over_budget:
        return "D"
    if risk_count >= 4 or missing_count >= 3 or score < 45:
        return "C"
    if risk_count or missing_count or score < 80:
        return "B"
    return "A"


def next_action(level: str, over_budget: bool, missing_count: int, risk_count: int) -> str:
    if over_budget:
        return "暂不推荐；除非价格、押付或预算结构调整，否则不进入带看"
    if level == "A":
        return "优先推荐；安排现场踏勘并同步推进业主、租约、证照原件核验"
    if missing_count:
        return "可跟进；先补齐证照、消防、特行、续签等尽调材料后再约谈"
    if risk_count:
        return "谨慎推进；先处理关键风险点并形成书面确认"
    return "可跟进；复核经营流水和租金递增条款"


def score_match(customer: CustomerRequirement, project: HotelProject) -> MatchResult | None:
    """Score a project for a customer, or return None when city does not match."""
    if project.city.lower() != customer.target_city.lower():
        return None

    score = 20
    matched_reasons: list[str] = ["城市匹配"]
    risk_warnings, missing_items = collect_due_diligence(project)

    if project.district.lower() in customer.preferred_districts:
        score += 15
        matched_reasons.append("区域匹配")
    else:
        score += 5
        matched_reasons.append("同城但非首选区域")

    if project.business_area.lower() in customer.preferred_business_areas:
        score += 10
        matched_reasons.append("商圈匹配")

    matched_tags = customer.required_business_tags & project.business_tags
    if matched_tags:
        score += min(15, len(matched_tags) * 8)
        matched_reasons.append("业务标签匹配:" + "/".join(sorted(matched_tags)))

    if customer.min_rooms <= project.room_count <= customer.max_rooms:
        score += 15
        matched_reasons.append("房间数落在需求区间")
    else:
        score -= 10
        risk_warnings.append(
            f"房间数{project.room_count}不在客户需求区间{customer.min_rooms}-{customer.max_rooms}"
        )

    over_budget = project.estimated_entry_cost > customer.max_budget
    if over_budget:
        score -= 35
        risk_warnings.append(
            "估算接手成本超过客户预算："
            f"{format_money(project.estimated_entry_cost)} > {format_money(customer.max_budget)}"
        )
    else:
        score += 20
        matched_reasons.append("估算接手成本在预算内")

    if project.rent_payment_terms.upfront_months >= HIGH_PAYMENT_MONTHS:
        score -= 8
        risk_warnings.append(
            "押付压力较高："
            f"押{project.rent_payment_terms.deposit_months}付{project.rent_payment_terms.payment_months}"
            f"需首期租金押付{format_money(project.first_rent_payment_cost)}"
        )
    else:
        score += 5
        matched_reasons.append("押付方式相对温和")

    if project.single_room_rent_cost <= LOW_RENT_COST_PER_ROOM:
        score += 15
        matched_reasons.append("单房租金成本低")
    elif project.single_room_rent_cost <= MEDIUM_RENT_COST_PER_ROOM:
        score += 8
        matched_reasons.append("单房租金成本可控")
    else:
        score -= 8
        risk_warnings.append(
            f"单房租金成本偏高：{format_money(project.single_room_rent_cost)}/间/月"
        )

    score -= min(20, len(risk_warnings) * 4 + len(missing_items) * 3)
    total_score = max(0, min(100, score))
    level = recommendation_level(total_score, over_budget, len(risk_warnings), len(missing_items))

    return MatchResult(
        customer_id=customer.customer_id,
        project_id=project.project_id,
        total_score=total_score,
        recommendation_level=level,
        estimated_entry_cost=project.estimated_entry_cost,
        single_room_rent_cost=project.single_room_rent_cost,
        matched_reasons=tuple(matched_reasons),
        risk_warnings=tuple(risk_warnings),
        missing_due_diligence_items=tuple(missing_items),
        recommended_next_action=next_action(level, over_budget, len(missing_items), len(risk_warnings)),
    )


def match_customers(
    customers: Iterable[CustomerRequirement], projects: Iterable[HotelProject]
) -> list[MatchResult]:
    """Return ranked customer-to-project matches."""
    customers_list = list(customers)
    projects_list = list(projects)

    results = [
        result
        for customer in customers_list
        for project in projects_list
        if (result := score_match(customer, project)) is not None
    ]
    return sorted(
        results,
        key=lambda result: (
            result.customer_id,
            result.recommendation_level,
            -result.total_score,
            result.estimated_entry_cost,
        ),
    )


def validate_projects_iterator_support() -> None:
    """Verify one-shot project iterators are reusable across multiple customers."""
    customers = load_customers()
    projects = load_projects()

    expected_pairs = [(result.customer_id, result.project_id) for result in match_customers(customers, projects)]
    iterator_pairs = [
        (result.customer_id, result.project_id) for result in match_customers(customers, iter(load_projects()))
    ]

    if len(customers) < 2:
        raise AssertionError("iterator validation requires multiple customers")

    if iterator_pairs != expected_pairs:
        raise AssertionError(
            "projects iterator produced incomplete matches: "
            f"expected {expected_pairs}, got {iterator_pairs}"
        )


def print_result(result: MatchResult) -> None:
    print(
        f"- customer_id={result.customer_id}; "
        f"project_id={result.project_id}; "
        f"total_score={result.total_score}; "
        f"recommendation_level={result.recommendation_level}; "
        f"estimated_entry_cost={format_money(result.estimated_entry_cost)}; "
        f"single_room_rent_cost={format_money(result.single_room_rent_cost)}; "
        f"matched_reasons={' | '.join(result.matched_reasons) or '无'}; "
        f"risk_warnings={' | '.join(result.risk_warnings) or '无'}; "
        f"missing_due_diligence_items={' | '.join(result.missing_due_diligence_items) or '无'}; "
        f"recommended_next_action={result.recommended_next_action}"
    )


def main() -> None:
    validate_projects_iterator_support()

    projects = load_projects()
    customers = load_customers()
    results = match_customers(customers, projects)

    print(f"Loaded {len(projects)} hotel projects from {PROJECTS_CSV.relative_to(ROOT_DIR)}")
    print(f"Loaded {len(customers)} customer requirements from {CUSTOMERS_CSV.relative_to(ROOT_DIR)}")
    print("\nCustomer matches:")

    if not results:
        print("- No matches found.")
        return

    current_customer_id = ""
    for result in results:
        if result.customer_id != current_customer_id:
            current_customer_id = result.customer_id
            print(f"\n{current_customer_id}:")
        print_result(result)


if __name__ == "__main__":
    main()
