"""Data models and cleaning helpers for Ctrip hotel records."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping

_CHINESE_NUMBER_UNITS = {"万": Decimal("10000")}


def _clean_text(value: Any) -> str | None:
    """Normalize blank-ish text to ``None`` while preserving meaningful content."""
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text or text in {"-", "--", "暂无", "无", "未知", "null", "None"}:
        return None
    return text


def parse_int(value: Any) -> int | None:
    """Parse integers from common Ctrip-style labels such as ``1,234条点评``."""
    text = _clean_text(value)
    if text is None:
        return None

    unit_multiplier = Decimal("1")
    for unit, multiplier in _CHINESE_NUMBER_UNITS.items():
        if unit in text:
            unit_multiplier = multiplier
            break

    match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", text)
    if not match:
        return None

    number = Decimal(match.group(0).replace(",", "")) * unit_multiplier
    return int(number)


def parse_float(value: Any) -> float | None:
    """Parse a floating-point value from text such as ``4.8分``."""
    text = _clean_text(value)
    if text is None:
        return None
    match = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    return float(match.group(0))


def parse_decimal(value: Any) -> Decimal | None:
    """Parse a money-like value from text such as ``¥398起``."""
    text = _clean_text(value)
    if text is None:
        return None
    match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return Decimal(match.group(0).replace(",", ""))
    except InvalidOperation:
        return None


def parse_diamond_level(value: Any) -> int | None:
    """Parse the Ctrip diamond level from text or numeric input."""
    return parse_int(value)


@dataclass(frozen=True)
class HotelRecord:
    """Normalized hotel record for Chongqing main-city 3-diamond hotels."""

    name: str
    district: str | None = None
    building_name: str | None = None
    opened_at: str | None = None
    renovated_at: str | None = None
    diamond_level: int | None = None
    room_count: int | None = None
    review_count: int | None = None
    rating: float | None = None
    price: Decimal | None = None

    EXPORT_HEADERS = (
        "酒店名称",
        "区域",
        "所在楼栋名称",
        "开业时间",
        "最近装修时间",
        "钻级",
        "房间数",
        "评价数",
        "评分",
        "卖价",
    )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "HotelRecord":
        """Build a normalized record from English or Chinese source field names."""
        def pick(*names: str) -> Any:
            for name in names:
                if name in payload:
                    return payload[name]
            return None

        name = _clean_text(pick("name", "hotel_name", "酒店名称"))
        if name is None:
            raise ValueError("hotel name is required")

        return cls(
            name=name,
            district=_clean_text(pick("district", "area", "区域")),
            building_name=_clean_text(pick("building_name", "building", "所在楼栋名称")),
            opened_at=_clean_text(pick("opened_at", "open_time", "开业时间")),
            renovated_at=_clean_text(pick("renovated_at", "renovation_time", "最近装修时间")),
            diamond_level=parse_diamond_level(pick("diamond_level", "diamond", "钻级")),
            room_count=parse_int(pick("room_count", "rooms", "房间数")),
            review_count=parse_int(pick("review_count", "reviews", "评价数")),
            rating=parse_float(pick("rating", "score", "评分")),
            price=parse_decimal(pick("price", "sale_price", "卖价")),
        )

    def to_export_row(self) -> dict[str, str]:
        """Return a CSV/Excel-friendly row with stable Chinese headers."""
        return {
            "酒店名称": self.name,
            "区域": self.district or "",
            "所在楼栋名称": self.building_name or "",
            "开业时间": self.opened_at or "",
            "最近装修时间": self.renovated_at or "",
            "钻级": "" if self.diamond_level is None else str(self.diamond_level),
            "房间数": "" if self.room_count is None else str(self.room_count),
            "评价数": "" if self.review_count is None else str(self.review_count),
            "评分": "" if self.rating is None else f"{self.rating:g}",
            "卖价": "" if self.price is None else f"{self.price.normalize():f}",
        }
