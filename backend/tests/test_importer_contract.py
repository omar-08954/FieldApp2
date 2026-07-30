"""Regression checks for non-negotiable Excel import safety guarantees."""
from io import BytesIO
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.core.database import Base
from app.models import ImportReview, Task
from app.services.importer import DEFAULT_STATUS, DEFAULT_SUBSCRIPTION, _mapping, import_workbook, task_values


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


def test_task_values_uses_safe_defaults_and_has_no_primary_key() -> None:
    values = task_values({"task_number": "WO-12", "subscription_number": "", "task_status": ""})
    assert values["subscription_number"] == DEFAULT_SUBSCRIPTION
    assert values["task_status"] == DEFAULT_STATUS
    assert "id" not in values


def test_import_isolates_bad_row_and_applies_defaults() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["ID", "رقم المهمة", "رقم الاشتراك", "حالة المهمة"])
    sheet.append([999, "WO-13", "", ""])
    sheet.append([1000, "", "S-2", "تم الفحص"])
    output = BytesIO()
    workbook.save(output)

    with Session(engine) as db:
        batch = import_workbook(db, output.getvalue(), "tasks.xlsx", None)
        task = db.scalar(select(Task))
        review = db.scalar(select(ImportReview))
        assert batch.imported_rows == 1
        assert batch.review_rows == 1
        assert task is not None and task.id != 999
        assert task.subscription_number == DEFAULT_SUBSCRIPTION
        assert task.task_status == DEFAULT_STATUS
        assert review is not None and review.source_row == 3
