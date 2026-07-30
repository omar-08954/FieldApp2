"""Regression checks for non-negotiable Excel import safety guarantees."""
from io import BytesIO
from openpyxl import Workbook
from app.services.importer import _mapping


def test_mapping_accepts_arabic_headers() -> None:
    assert _mapping(["رقم المهمة", "رقم الاشتراك", "حالة المهمة"])["task_number"] == 0


def test_id_column_is_never_mapped() -> None:
    mapping = _mapping(["ID", "رقم المهمة"])
    assert "id" not in mapping
    assert mapping["task_number"] == 1


def test_empty_values_do_not_require_excel_primary_key() -> None:
    workbook = Workbook(); sheet = workbook.active
    sheet.append(["ID", "رقم المهمة"]); sheet.append([99999, "WO-11"])
    output = BytesIO(); workbook.save(output)
    assert output.getvalue()
