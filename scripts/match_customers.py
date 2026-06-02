#!/usr/bin/env python3
"""Match Chongqing hotel transfer/lease projects to customer requirements.

The scoring mirrors how a hotel site-selection advisor usually screens a deal:
location fit and room-count efficiency are only useful when the entry cost,
remaining lease term, certificates, landlord consent, and commission clause can
support a safe transaction. It intentionally uses only Python's standard
library, including csv for data loading.
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

DEFAULT_RENT_PAYMENT_TERMS = (2, 3)
SHORT_LEASE_YEARS = 3


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
    project_name: str
    city: str
    district: str
    business_area: str
    area_sqm: float
    monthly_rent: float
    monthly_property_fee: float
    room_count: int
    bright_room_count: int
    dark_room_count: int
    transfer_fee: float
    contract_years: float
    lease_years_remaining: float
    rent_payment_terms: RentPaymentTerms
    is_operating: str
    license_status: str
    fire_safety_status: str
    special_industry_license_status: str
    landlord_written_consent: str
    commission_clause_locked: str
    current_stage: str
    next_action: str

    @property
    def first_rent_payment_cost(self) -> float:
        return self.monthly_rent * self.rent_payment_terms.upfront_months

    @property
    def reserve_fund(self) -> float:
        """Simple reserve required by the user: monthly rent multiplied by 2."""
        return self.monthly_rent * 2

    @property
    def estimated_entry_cost(self) -> float:
        return self.transfer_fee + self.first_rent_payment_cost + self.reserve_fund

    @property
    def single_room_rent_cost(self) -> float:
        if self.room_count <= 0:
            return 0
        return (self.monthly_rent + self.monthly_property_fee) / self.room_count / 30


@dataclass(frozen=True)
class CustomerRequirement:
    customer_id: str
    preferred_city: str
    preferred_districts: set[str]
    preferred_business_areas: set[str]
    min_budget: float
    max_budget: float
    min_room_count: int
    max_room_count: int
    max_single_room_rent_cost: float
    accepts_transfer_fee: bool
    max_transfer_fee: float
    accepts_unknown_license_risk: bool
    accepts_medium_commission_risk: bool
    current_stage: str
    next_action: str


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
    return normalize_status(value) in {"是", "yes", "y", "true", "1", "齐全", "合格", "已锁定"}


def is_no(value: str) -> bool:
    return normalize_status(value) in {"否", "no", "n", "false", "0", "不", "未", "缺失", "不合格"}


def is_unknown(value: str) -> bool:
    return normalize_status(value) in {"待确认", "未知", "不明", "需核验", "unknown", "tbc", "pending", ""}


def parse_bool(value: str) -> bool:
    return is_yes(value)


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
    """Load hotel transfer/lease projects from a CSV file."""
    with path.open(newline="", encoding="utf-8") as csv_file:
        return [
            HotelProject(
                project_id=row["project_id"],
                project_name=row["project_name"],
                city=row["city"],
                district=row["district"],
                business_area=row["business_area"],
                area_sqm=parse_float(row["area_sqm"]),
                monthly_rent=parse_float(row["monthly_rent"]),
                monthly_property_fee=parse_float(row["monthly_property_fee"]),
                room_count=parse_int(row["room_count"]),
                bright_room_count=parse_int(row["bright_room_count"]),
                dark_room_count=parse_int(row["dark_room_count"]),
                transfer_fee=parse_float(row["transfer_fee"]),
                contract_years=parse_float(row["contract_years"]),
                lease_years_remaining=parse_float(row["lease_years_remaining"]),
                rent_payment_terms=parse_rent_payment_terms(row["rent_payment_terms"]),
                is_operating=normalize_status(row["is_operating"]),
                license_status=normalize_status(row["license_status"]),
                fire_safety_status=normalize_status(row["fire_safety_status"]),
                special_industry_license_status=normalize_status(row["special_industry_license_status"]),
                landlord_written_consent=normalize_status(row["landlord_written_consent"]),
                commission_clause_locked=normalize_status(row["commission_clause_locked"]),
                current_stage=row["current_stage"].strip(),
                next_action=row["next_action"].strip(),
            )
            for row in csv.DictReader(csv_file)
        ]


def load_customers(path: Path = CUSTOMERS_CSV) -> list[CustomerRequirement]:
    """Load customer requirements from a CSV file."""
    with path.open(newline="", encoding="utf-8") as csv_file:
        return [
            CustomerRequirement(
                customer_id=row["customer_id"],
                preferred_city=row["preferred_city"],
                preferred_districts=split_tokens(row["preferred_districts"]),
                preferred_business_areas=split_tokens(row["preferred_business_areas"]),
                min_budget=parse_float(row["min_budget"]),
                max_budget=parse_float(row["max_budget"]),
                min_room_count=parse_int(row["min_room_count"]),
                max_room_count=parse_int(row["max_room_count"]),
                max_single_room_rent_cost=parse_float(row["max_single_room_rent_cost"]),
                accepts_transfer_fee=parse_bool(row["accepts_transfer_fee"]),
                max_transfer_fee=parse_float(row["max_transfer_fee"]),
                accepts_unknown_license_risk=parse_bool(row["accepts_unknown_license_risk"]),
                accepts_medium_commission_risk=parse_bool(row["accepts_medium_commission_risk"]),
                current_stage=row["current_stage"].strip(),
                next_action=row["next_action"].strip(),
            )
            for row in csv.DictReader(csv_file)
        ]


def collect_due_diligence(
    customer: CustomerRequirement, project: HotelProject
) -> tuple[list[str], list[str]]:
    """Return risk warnings and missing due-diligence items for a project/customer pair."""
    risk_warnings: list[str] = []
    missing_items: list[str] = []

    if project.lease_years_remaining < SHORT_LEASE_YEARS:
        risk_warnings.append("剩余租期低于3年，续约落地和装修摊销周期存在压力")

    for field_name, status in (
        ("证照状态", project.license_status),
        ("消防状态", project.fire_safety_status),
        ("特行状态", project.special_industry_license_status),
    ):
        if is_unknown(status):
            missing_items.append(f"{field_name}不明，需补原件、主管部门口径或整改评估")
        elif is_no(status):
            risk_warnings.append(f"{field_name}为{status}，交易结构或开业合规存在重大不确定性")

    if missing_items and not customer.accepts_unknown_license_risk:
        risk_warnings.append("客户不接受证照/消防/特行不明风险，需先补齐尽调再推荐")

    if not is_yes(project.landlord_written_consent):
        risk_warnings.append("业主未书面同意，转让、转租或重签落地存在关键障碍")

    if not is_yes(project.commission_clause_locked):
        risk_warnings.append("佣金条款未锁死，需先确认居间费触发条件和支付节点")
        if not customer.accepts_medium_commission_risk:
            risk_warnings.append("客户不接受中等佣金风险，未锁佣前不宜进入深度谈判")

    return risk_warnings, missing_items


def recommendation_level(
    score: int,
    over_budget: bool,
    risk_count: int,
    missing_count: int,
    strong_fit_with_unclear_risk: bool,
) -> str:
    """Convert score and gating risks into advisor-style project priority."""
    if over_budget or score < 40:
        return "D"
    if risk_count >= 5 or missing_count >= 3 or score < 60:
        return "C"
    if strong_fit_with_unclear_risk or risk_count or missing_count or score < 82:
        return "B"
    return "A"


def next_action(level: str, over_budget: bool, missing_count: int, risk_count: int) -> str:
    if over_budget:
        return "暂不推荐；除非转让费、押付或客户预算结构调整，否则不进入带看"
    if level == "A":
        return "优先推荐；安排现场踏勘，同时复核租约、证照、消防、特行和业主书面同意"
    if missing_count:
        return "可作为备选；先补齐证照、消防、特行等尽调缺失项，再决定是否约谈"
    if risk_count:
        return "谨慎推进；先把租期、业主同意和佣金条款形成书面确认"
    return "可跟进；结合客户阶段复核经营流水、租金递增和改造预算"


def score_match(customer: CustomerRequirement, project: HotelProject) -> MatchResult | None:
    """Score a project for a customer, or return None when city does not match."""
    if project.city.lower() != customer.preferred_city.lower():
        return None

    score = 20
    matched_reasons: list[str] = ["城市匹配"]
    risk_warnings, missing_items = collect_due_diligence(customer, project)

    district_matched = project.district.lower() in customer.preferred_districts
    business_area_matched = project.business_area.lower() in customer.preferred_business_areas
    room_count_matched = customer.min_room_count <= project.room_count <= customer.max_room_count

    if district_matched:
        score += 16
        matched_reasons.append("区域匹配")
    else:
        score -= 6
        risk_warnings.append(f"区域{project.district}不在客户首选区域内")

    if business_area_matched:
        score += 14
        matched_reasons.append("商圈匹配")
    else:
        score -= 4
        risk_warnings.append(f"商圈{project.business_area}不在客户首选商圈内")

    if room_count_matched:
        score += 16
        matched_reasons.append("房间数符合客户区间")
    else:
        score -= 12
        risk_warnings.append(
            f"房间数{project.room_count}不在客户需求区间{customer.min_room_count}-{customer.max_room_count}"
        )

    if project.single_room_rent_cost <= customer.max_single_room_rent_cost:
        score += 16
        matched_reasons.append(
            "单房租金成本低于客户上限:"
            f"{format_money(project.single_room_rent_cost)} <= {format_money(customer.max_single_room_rent_cost)}"
        )
    else:
        score -= 12
        risk_warnings.append(
            "单房租金成本超过客户上限:"
            f"{format_money(project.single_room_rent_cost)} > {format_money(customer.max_single_room_rent_cost)}"
        )

    transfer_fee_ok = project.transfer_fee == 0 or (
        customer.accepts_transfer_fee and project.transfer_fee <= customer.max_transfer_fee
    )
    if transfer_fee_ok:
        score += 12
        if project.transfer_fee == 0:
            matched_reasons.append("无转让费，符合直租/低接手成本偏好")
        else:
            matched_reasons.append("转让费在客户接受范围内")
    else:
        score -= 18
        risk_warnings.append(
            "转让费不在客户接受范围:"
            f"项目{format_money(project.transfer_fee)}，客户上限{format_money(customer.max_transfer_fee)}"
        )

    over_budget = project.estimated_entry_cost > customer.max_budget
    if over_budget:
        score -= 35
        risk_warnings.append(
            "估算接手成本超过客户max_budget:"
            f"{format_money(project.estimated_entry_cost)} > {format_money(customer.max_budget)}"
        )
    elif project.estimated_entry_cost < customer.min_budget:
        score += 4
        matched_reasons.append("估算接手成本低于客户最低预算，可保留议价和改造空间")
    else:
        score += 14
        matched_reasons.append("估算接手成本落在客户预算区间")

    if project.rent_payment_terms.upfront_months >= 8:
        score -= 6
        risk_warnings.append(
            "押付压力较高:"
            f"押{project.rent_payment_terms.deposit_months}付{project.rent_payment_terms.payment_months}，"
            f"首期租金押付成本{format_money(project.first_rent_payment_cost)}"
        )
    else:
        score += 4
        matched_reasons.append("押付方式相对温和")

    if is_yes(project.is_operating):
        score += 3
        matched_reasons.append("项目仍在营业，可现场核验客流和交接状态")

    strong_fit_with_unclear_risk = (
        district_matched
        and business_area_matched
        and room_count_matched
        and (risk_warnings or missing_items)
    )
    score -= min(24, len(risk_warnings) * 4 + len(missing_items) * 3)
    total_score = max(0, min(100, score))
    level = recommendation_level(
        total_score, over_budget, len(risk_warnings), len(missing_items), strong_fit_with_unclear_risk
    )

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
