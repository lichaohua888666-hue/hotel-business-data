"""Export helpers for normalized Ctrip hotel records."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Sequence

from .models import HotelRecord


def export_csv(records: Iterable[HotelRecord], path: str | Path) -> Path:
    """Export records to UTF-8-SIG CSV using the required Chinese headers."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(HotelRecord.EXPORT_HEADERS))
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_export_row())
    return output_path


def export_xlsx(records: Sequence[HotelRecord], path: str | Path) -> Path:
    """Export records to XLSX when ``openpyxl`` is available."""
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("XLSX export requires the optional 'openpyxl' package") from exc

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ctrip重庆3钻酒店"
    sheet.append(list(HotelRecord.EXPORT_HEADERS))
    for record in records:
        row = record.to_export_row()
        sheet.append([row[header] for header in HotelRecord.EXPORT_HEADERS])
    workbook.save(output_path)
    return output_path


def export_records(records: Sequence[HotelRecord], path: str | Path) -> Path:
    """Export records based on the file extension: CSV by default, XLSX optionally."""
    output_path = Path(path)
    if output_path.suffix.lower() == ".xlsx":
        return export_xlsx(records, output_path)
    return export_csv(records, output_path)
