"""Fast, fault-isolated Excel import with batched database writes."""
    import json
    import logging
    from datetime import date
    from io import BytesIO
    from typing import Any

    from openpyxl import load_workbook
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session

    from app.models import ImportBatch, ImportReview, Task

    logger = logging.getLogger(__name__)
    DEFAULT_SUBSCRIPTION = "غير مسجل"
    DEFAULT_STATUS = "تم الفحص"
    BATCH_SIZE = 250
    ALIASES = {
      "technician_name": {"الفني", "اسم الفني", "technician", "employee"},
      "task_number": {"رقم المهمة", "المهمة", "task number", "task", "work order"},
      "subscription_number": {"رقم الاشتراك", "الاشتراك", "subscription", "subscription number"},
      "task_type": {"نوع المهمة", "النوع", "task type", "type"},
      "task_status": {"حالة المهمة", "الحالة", "task status", "status"},
      "city": {"المدينة", "city", "المنطقة"},
      "notes": {"الملاحظات", "notes", "comment"},
    }


    def _text(value: Any) -> str:
      return "" if value is None else str(value).strip()


    def _mapping(headers: list[Any]) -> dict[str, int]:
      normalized = {_text(header).casefold(): index for index, header in enumerate(headers) if _text(header)}
      result: dict[str, int] = {}
      for field, aliases in ALIASES.items():
          for alias in aliases:
              if alias.casefold() in normalized:
                  result[field] = normalized[alias.casefold()]
                  break
      return result


    def _review(
      db: Session,
      batch: ImportBatch,
      row_number: int,
      raw: list[Any],
      exc: Exception,
      action: str,
      values: dict[str, str] | None = None,
    ) -> None:
      values = values or {}
      db.add(
          ImportReview(
              batch_id=batch.id,
              source_row=row_number,
              task_number=values.get("task_number"),
              technician_name=values.get("technician_name"),
              subscription_number=values.get("subscription_number"),
              task_type=values.get("task_type"),
              exception_type=type(exc).__name__,
              error_message=str(exc)[:4000],
              postgres_message=str(exc)[:4000] if isinstance(exc, SQLAlchemyError) else None,
              action_taken=action,
              raw_payload=json.dumps(raw, ensure_ascii=False, default=str),
          )
      )


    def task_values(values: dict[str, str]) -> dict[str, Any]:
      """Build a Task payload without ever accepting a spreadsheet primary key."""
      return {
          "technician_name": values.get("technician_name") or "غير مسجل",
          "task_number": values.get("task_number", ""),
          "subscription_number": values.get("subscription_number") or DEFAULT_SUBSCRIPTION,
          "task_type": values.get("task_type") or "تقني",
          "task_status": values.get("task_status") or DEFAULT_STATUS,
          "city": values.get("city") or None,
          "notes": values.get("notes") or None,
          "execution_date": date.today(),
      }


    def _insert_task_batch(
      db: Session,
      batch: ImportBatch,
      rows: list[tuple[int, list[Any], dict[str, str]]],
    ) -> None:
      """Insert valid rows efficiently and split only failed batches to isolate bad rows."""
      if not rows:
          return
      try:
          with db.begin_nested():
              db.bulk_insert_mappings(Task, [task_values(values) for _, _, values in rows])
      except Exception as exc:
          if len(rows) == 1:
              row_number, raw, values = rows[0]
              logger.warning("Excel row moved to review", extra={"row_number": row_number})
              _review(db, batch, row_number, raw, exc, "moved_to_import_review", values)
              batch.review_rows += 1
              return
          midpoint = len(rows) // 2
          _insert_task_batch(db, batch, rows[:midpoint])
          _insert_task_batch(db, batch, rows[midpoint:])
      else:
          batch.imported_rows += len(rows)


    def import_workbook(db: Session, contents: bytes, filename: str, imported_by_id: int | None) -> ImportBatch:
      """Process an Excel workbook in batches while isolating invalid rows."""
      batch = ImportBatch(filename=filename[:255], imported_by_id=imported_by_id)
      db.add(batch)
      db.flush()
      pending: list[tuple[int, list[Any], dict[str, str]]] = []
      try:
          workbook = load_workbook(BytesIO(contents), read_only=True, data_only=True)
          try:
              rows = workbook.active.iter_rows(values_only=True)
              headers = list(next(rows, ()))
              mapping = _mapping(headers)
              if "task_number" not in mapping:
                  raise ValueError("لم يتم العثور على عمود رقم المهمة في الملف")
              for row_number, raw_tuple in enumerate(rows, start=2):
                  raw = list(raw_tuple)
                  batch.total_rows += 1
                  values: dict[str, str] = {}
                  try:
                      values = {
                          field: _text(raw[index]) if index < len(raw) else ""
                          for field, index in mapping.items()
                      }
                      if not values.get("task_number", ""):
                          raise ValueError("رقم المهمة مطلوب")
                      pending.append((row_number, raw, values))
                  except Exception as exc:
                      _review(db, batch, row_number, raw, exc, "moved_to_import_review", values)
                      batch.review_rows += 1
                  if len(pending) >= BATCH_SIZE:
                      _insert_task_batch(db, batch, pending)
                      pending.clear()
              _insert_task_batch(db, batch, pending)
          finally:
              workbook.close()
          db.commit()
      except Exception as exc:
          logger.exception("Excel file processing failed safely", extra={"import_filename": filename})
          _review(db, batch, 1, [], exc, "file_moved_to_import_review")
          batch.review_rows += 1
          db.commit()
      return batch
    