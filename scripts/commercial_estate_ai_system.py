#!/usr/bin/env python3
"""AI-style operating console for commercial real-estate brokers.

The system uses the existing hotel transfer/lease inventory as a commercial
property vertical. It combines customer-project matching, risk triage, deal
stage guidance, and task generation into one broker-facing command line report.
It is deliberately dependency-free so teams can run it before connecting a CRM,
LLM API, or BI dashboard.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Iterable

from match_customers import (
    CustomerRequirement,
    HotelProject,
    MatchResult,
    format_money,
    load_customers,
    load_projects,
    match_customers,
)

HIGH_PRIORITY_LEVELS = {"A", "B"}


@dataclass(frozen=True)
class BrokerTask:
    """A concrete next action a broker can execute in the CRM."""

    priority: int
    owner_role: str
    customer_id: str
    project_id: str
    task_type: str
    action: str
    reason: str


@dataclass(frozen=True)
class PropertyInsight:
    """Portfolio-level guidance for one listed commercial property."""

    project_id: str
    project_name: str
    marketability_score: int
    listing_health: str
    target_customer_ids: tuple[str, ...]
    key_selling_points: tuple[str, ...]
    blockers: tuple[str, ...]
    next_action: str


@dataclass(frozen=True)
class AiSystemReport:
    """Serializable output for the broker AI console."""

    inventory_summary: dict[str, object]
    customer_recommendations: dict[str, list[dict[str, object]]]
    property_insights: list[PropertyInsight]
    broker_tasks: list[BrokerTask]


def build_inventory_summary(projects: Iterable[HotelProject]) -> dict[str, object]:
    """Return high-level market statistics for quick morning standups."""
    projects_list = list(projects)
    district_counts = Counter(project.district for project in projects_list)
    total_rooms = sum(project.room_count for project in projects_list)
    total_bright_rooms = sum(project.bright_room_count for project in projects_list)
    average_entry_cost = (
        sum(project.estimated_entry_cost for project in projects_list) / len(projects_list)
        if projects_list
        else 0
    )
    no_transfer_fee_count = sum(1 for project in projects_list if project.transfer_fee == 0)
    operating_count = sum(1 for project in projects_list if project.is_operating in {"是", "yes", "true", "1"})

    return {
        "project_count": len(projects_list),
        "total_rooms": total_rooms,
        "bright_room_ratio": round(total_bright_rooms / total_rooms, 4) if total_rooms else 0,
        "average_estimated_entry_cost": round(average_entry_cost),
        "no_transfer_fee_count": no_transfer_fee_count,
        "operating_count": operating_count,
        "district_distribution": dict(sorted(district_counts.items())),
    }


def shortlist_by_customer(
    results: Iterable[MatchResult], top_n: int, customer_id: str | None = None
) -> dict[str, list[MatchResult]]:
    """Group the best project recommendations for each customer."""
    grouped: dict[str, list[MatchResult]] = defaultdict(list)
    for result in results:
        if customer_id and result.customer_id != customer_id:
            continue
        grouped[result.customer_id].append(result)

    return {
        grouped_customer_id: sorted(
            customer_results,
            key=lambda item: (item.recommendation_level, -item.total_score, item.estimated_entry_cost),
        )[:top_n]
        for grouped_customer_id, customer_results in sorted(grouped.items())
    }


def recommendation_to_dict(result: MatchResult) -> dict[str, object]:
    """Convert a match into a CRM/JSON friendly payload."""
    return {
        "project_id": result.project_id,
        "recommendation_level": result.recommendation_level,
        "total_score": result.total_score,
        "estimated_entry_cost": round(result.estimated_entry_cost),
        "single_room_rent_cost": round(result.single_room_rent_cost, 2),
        "matched_reasons": list(result.matched_reasons),
        "risk_warnings": list(result.risk_warnings),
        "missing_due_diligence_items": list(result.missing_due_diligence_items),
        "recommended_next_action": result.recommended_next_action,
    }


def build_property_insights(
    projects: Iterable[HotelProject], results: Iterable[MatchResult]
) -> list[PropertyInsight]:
    """Score listing health from demand, risk, and transaction readiness."""
    matches_by_project: dict[str, list[MatchResult]] = defaultdict(list)
    for result in results:
        matches_by_project[result.project_id].append(result)

    insights: list[PropertyInsight] = []
    for project in projects:
        matches = matches_by_project.get(project.project_id, [])
        high_priority_matches = [match for match in matches if match.recommendation_level in HIGH_PRIORITY_LEVELS]
        average_score = sum(match.total_score for match in matches) / len(matches) if matches else 0
        demand_bonus = min(20, len(high_priority_matches) * 5)
        marketability_score = max(0, min(100, round(average_score + demand_bonus)))

        blockers: list[str] = []
        if project.lease_years_remaining < 3:
            blockers.append("剩余租期不足3年")
        if project.landlord_written_consent != "是":
            blockers.append("缺少业主书面同意")
        if project.commission_clause_locked != "是":
            blockers.append("佣金条款未锁定")
        for label, status in (
            ("证照", project.license_status),
            ("消防", project.fire_safety_status),
            ("特行", project.special_industry_license_status),
        ):
            if status in {"不明", "待确认", "未知", "需核验"}:
                blockers.append(f"{label}状态需核验")

        key_selling_points: list[str] = []
        if project.transfer_fee == 0:
            key_selling_points.append("无转让费，可包装为直租机会")
        if project.is_operating == "是":
            key_selling_points.append("营业中，可现场核验经营状态")
        if project.room_count and project.bright_room_count / project.room_count >= 0.85:
            key_selling_points.append("明房占比较高")
        if project.lease_years_remaining >= 5:
            key_selling_points.append("剩余租期较长")

        if marketability_score >= 82 and not blockers:
            listing_health = "热推"
            next_action = "制作重点项目页并邀约A/B级客户集中看店"
        elif high_priority_matches:
            listing_health = "可推"
            next_action = "先处理关键阻碍，再推送给高匹配客户"
        else:
            listing_health = "培育"
            next_action = "补齐资料、优化价格或转让条件后再扩大推荐"

        insights.append(
            PropertyInsight(
                project_id=project.project_id,
                project_name=project.project_name,
                marketability_score=marketability_score,
                listing_health=listing_health,
                target_customer_ids=tuple(match.customer_id for match in high_priority_matches),
                key_selling_points=tuple(key_selling_points or ["需进一步提炼卖点"]),
                blockers=tuple(blockers or ["暂无硬性阻碍"]),
                next_action=next_action,
            )
        )

    return sorted(insights, key=lambda insight: (-insight.marketability_score, insight.project_id))


def build_broker_tasks(
    customers: Iterable[CustomerRequirement], results: Iterable[MatchResult], top_n: int
) -> list[BrokerTask]:
    """Generate a prioritized broker work queue from matching results."""
    customer_stage = {customer.customer_id: customer.current_stage for customer in customers}
    grouped = shortlist_by_customer(results, top_n=top_n)
    tasks: list[BrokerTask] = []

    for grouped_customer_id, customer_results in grouped.items():
        for rank, result in enumerate(customer_results, start=1):
            priority = rank * 10 + (0 if result.recommendation_level == "A" else 5)
            if result.missing_due_diligence_items:
                tasks.append(
                    BrokerTask(
                        priority=priority,
                        owner_role="尽调专员",
                        customer_id=grouped_customer_id,
                        project_id=result.project_id,
                        task_type="补齐尽调",
                        action="；".join(result.missing_due_diligence_items),
                        reason=f"客户阶段：{customer_stage.get(grouped_customer_id, '未知')}；推荐等级{result.recommendation_level}",
                    )
                )
            elif result.risk_warnings:
                tasks.append(
                    BrokerTask(
                        priority=priority,
                        owner_role="交易顾问",
                        customer_id=grouped_customer_id,
                        project_id=result.project_id,
                        task_type="风险澄清",
                        action="；".join(result.risk_warnings[:2]),
                        reason=f"评分{result.total_score}，推进前需书面化关键条件",
                    )
                )
            else:
                tasks.append(
                    BrokerTask(
                        priority=priority,
                        owner_role="客户经理",
                        customer_id=grouped_customer_id,
                        project_id=result.project_id,
                        task_type="邀约带看",
                        action=result.recommended_next_action,
                        reason=f"评分{result.total_score}，匹配理由：{'；'.join(result.matched_reasons[:3])}",
                    )
                )

    return sorted(tasks, key=lambda task: (task.priority, task.customer_id, task.project_id))


def build_report(top_n: int, customer_id: str | None = None) -> AiSystemReport:
    projects = load_projects()
    customers = load_customers()
    results = match_customers(customers, projects)
    shortlisted_results = shortlist_by_customer(results, top_n=top_n, customer_id=customer_id)
    flattened_shortlist = [result for customer_results in shortlisted_results.values() for result in customer_results]

    return AiSystemReport(
        inventory_summary=build_inventory_summary(projects),
        customer_recommendations={
            grouped_customer_id: [recommendation_to_dict(result) for result in customer_results]
            for grouped_customer_id, customer_results in shortlisted_results.items()
        },
        property_insights=build_property_insights(projects, results),
        broker_tasks=build_broker_tasks(customers, flattened_shortlist, top_n=top_n),
    )


def print_text_report(report: AiSystemReport) -> None:
    summary = report.inventory_summary
    print("商业地产中介 AI 智能系统")
    print("=" * 34)
    print("\n[库存概览]")
    print(f"- 项目数: {summary['project_count']}")
    print(f"- 总房间数: {summary['total_rooms']}")
    print(f"- 明房占比: {summary['bright_room_ratio']:.1%}")
    print(f"- 平均估算接手成本: {format_money(float(summary['average_estimated_entry_cost']))}")
    print(f"- 无转让费项目数: {summary['no_transfer_fee_count']}")
    print(f"- 营业中项目数: {summary['operating_count']}")
    print("- 区域分布: " + "；".join(f"{district}{count}个" for district, count in summary["district_distribution"].items()))

    print("\n[客户推荐]")
    if not report.customer_recommendations:
        print("- 暂无匹配客户。")
    for customer_id, recommendations in report.customer_recommendations.items():
        print(f"\n{customer_id}:")
        for item in recommendations:
            print(
                f"- {item['project_id']} | 等级{item['recommendation_level']} | "
                f"评分{item['total_score']} | 接手成本{format_money(float(item['estimated_entry_cost']))} | "
                f"下一步：{item['recommended_next_action']}"
            )
            if item["risk_warnings"]:
                print("  风险: " + "；".join(item["risk_warnings"][:3]))
            if item["missing_due_diligence_items"]:
                print("  尽调: " + "；".join(item["missing_due_diligence_items"][:3]))

    print("\n[项目洞察]")
    for insight in report.property_insights:
        print(
            f"- {insight.project_id} {insight.project_name}: {insight.listing_health} "
            f"({insight.marketability_score})；目标客户: {', '.join(insight.target_customer_ids) or '待培育'}"
        )
        print(f"  卖点: {'；'.join(insight.key_selling_points)}")
        print(f"  阻碍: {'；'.join(insight.blockers)}")
        print(f"  动作: {insight.next_action}")

    print("\n[经纪人任务队列]")
    for task in report.broker_tasks:
        print(
            f"- P{task.priority:02d} [{task.owner_role}/{task.task_type}] "
            f"{task.customer_id}->{task.project_id}: {task.action} ({task.reason})"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the commercial real-estate broker AI console.")
    parser.add_argument("--top-n", type=int, default=3, help="number of recommendations per customer")
    parser.add_argument("--customer-id", help="only show recommendations for one customer")
    parser.add_argument("--json", action="store_true", help="emit JSON for CRM/BI integration")
    args = parser.parse_args()

    report = build_report(top_n=args.top_n, customer_id=args.customer_id)
    if args.json:
        print(
            json.dumps(
                {
                    "inventory_summary": report.inventory_summary,
                    "customer_recommendations": report.customer_recommendations,
                    "property_insights": [asdict(insight) for insight in report.property_insights],
                    "broker_tasks": [asdict(task) for task in report.broker_tasks],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print_text_report(report)


if __name__ == "__main__":
    main()
