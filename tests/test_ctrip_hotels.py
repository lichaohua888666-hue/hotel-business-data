from __future__ import annotations

import csv
from decimal import Decimal
import json
import unittest

from ctrip_hotels.crawl_chongqing import JsonFileSource, collect, load_config, normalize_records
from ctrip_hotels.export import export_csv
from ctrip_hotels.models import HotelRecord, parse_decimal, parse_float, parse_int


class CleaningTests(unittest.TestCase):
    def test_parse_common_numeric_fields(self) -> None:
        self.assertEqual(parse_int("1,234条点评"), 1234)
        self.assertEqual(parse_int("1.2万条点评"), 12000)
        self.assertEqual(parse_float("4.8分"), 4.8)
        self.assertEqual(parse_decimal("¥398起"), Decimal("398"))

    def test_missing_open_and_renovation_time_stay_empty(self) -> None:
        record = HotelRecord.from_mapping(
            {
                "酒店名称": "重庆测试酒店",
                "区域": "渝中区",
                "开业时间": "",
                "最近装修时间": "暂无",
                "钻级": "3钻",
                "房间数": "120间",
                "评价数": "88条点评",
                "评分": "4.7分",
                "卖价": "¥288",
            }
        )

        self.assertIsNone(record.opened_at)
        self.assertIsNone(record.renovated_at)
        self.assertEqual(record.to_export_row()["开业时间"], "")
        self.assertEqual(record.to_export_row()["最近装修时间"], "")

    def test_hotel_record_from_chinese_mapping(self) -> None:
        record = HotelRecord.from_mapping(
            {
                "酒店名称": "重庆主城三钻酒店",
                "区域": "江北区",
                "所在楼栋名称": "观音桥商圈A座",
                "开业时间": "2019年",
                "最近装修时间": "2023年",
                "钻级": "携程3钻",
                "房间数": "168间",
                "评价数": "2,345条点评",
                "评分": "4.6分",
                "卖价": "¥321起",
            }
        )

        self.assertEqual(record.name, "重庆主城三钻酒店")
        self.assertEqual(record.diamond_level, 3)
        self.assertEqual(record.room_count, 168)
        self.assertEqual(record.review_count, 2345)
        self.assertEqual(record.rating, 4.6)
        self.assertEqual(record.price, Decimal("321"))


class ExportTests(unittest.TestCase):
    def test_export_csv_uses_required_headers_and_values(self) -> None:
        from tempfile import TemporaryDirectory

        records = [
            HotelRecord(
                name="重庆测试酒店",
                district="南岸区",
                building_name="南坪中心",
                opened_at=None,
                renovated_at="2022年",
                diamond_level=3,
                room_count=90,
                review_count=1200,
                rating=4.5,
                price=Decimal("266.50"),
            )
        ]
        with TemporaryDirectory() as tmpdir:
            output = export_csv(records, f"{tmpdir}/hotels.csv")
            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(rows[0]["酒店名称"], "重庆测试酒店")
        self.assertEqual(rows[0]["开业时间"], "")
        self.assertEqual(rows[0]["卖价"], "266.5")


class CollectionTests(unittest.TestCase):
    def test_normalize_records_filters_to_three_diamond(self) -> None:
        records = normalize_records(
            [
                {"酒店名称": "三钻", "钻级": "3钻", "评价数": "1条", "评分": "4.1", "卖价": "100"},
                {"酒店名称": "四钻", "钻级": "4钻", "评价数": "2条", "评分": "4.9", "卖价": "500"},
            ],
            diamond_level=3,
        )

        self.assertEqual([record.name for record in records], ["三钻"])

    def test_json_source_collects_authorized_payload(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            input_path = f"{tmpdir}/hotels.json"
            with open(input_path, "w", encoding="utf-8") as handle:
                json.dump({"hotels": [{"酒店名称": "授权样例", "钻级": "3钻"}]}, handle, ensure_ascii=False)
            records = collect(JsonFileSource(input_path), {"diamond_level": 3})

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, "授权样例")

    def test_config_contains_compliance_controls(self) -> None:
        config = load_config("config/ctrip_chongqing.yaml")

        self.assertEqual(config["city"], "重庆")
        self.assertTrue(config["compliance"]["prefer_authorized_api"])
        self.assertTrue(config["compliance"]["respect_robots_txt"])
        self.assertEqual(config["diamond_level"], 3)


if __name__ == "__main__":
    unittest.main()
