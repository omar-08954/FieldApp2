import datetime
import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from database.storage import StorageOperationError


class _FakeCacheDecorator:
    def __call__(self, func=None, **_kwargs):
        def decorate(target):
            target.clear = Mock()
            return target

        return decorate(func) if func is not None else decorate


def _load_database_module():
    fake_streamlit = types.ModuleType("streamlit")
    fake_streamlit.secrets = {"DATABASE_URL": "postgresql://unused-for-unit-tests"}
    fake_streamlit.cache_data = _FakeCacheDecorator()
    fake_streamlit.cache_resource = _FakeCacheDecorator()
    previous_streamlit = sys.modules.get("streamlit")
    try:
        sys.modules["streamlit"] = fake_streamlit
        sys.modules.pop("database.database", None)
        return importlib.import_module("database.database")
    finally:
        if previous_streamlit is None:
            sys.modules.pop("streamlit", None)
        else:
            sys.modules["streamlit"] = previous_streamlit


db = _load_database_module()


class CalendarDateTests(unittest.TestCase):
    def test_padded_and_unpadded_dates_normalize_identically(self):
        expected = datetime.date(2025, 6, 15)
        self.assertEqual(db.normalize_calendar_date("2025-06-15"), expected)
        self.assertEqual(db.normalize_calendar_date("2025-6-15"), expected)
        self.assertEqual(db.normalize_calendar_date(expected), expected)

    def test_datetime_keeps_calendar_day_without_timezone_conversion(self):
        source = datetime.datetime(
            2025, 6, 15, 23, 30, tzinfo=datetime.timezone(datetime.timedelta(hours=-7))
        )
        self.assertEqual(db.normalize_calendar_date(source), datetime.date(2025, 6, 15))

    def test_searches_use_one_normalized_date_cache_key(self):
        expected = datetime.date(2025, 6, 15)
        with patch.object(db, "_search_completed_tasks_cached", return_value=["completed"]) as completed:
            self.assertEqual(db.search_completed_tasks("فني", "2025-6-15"), ["completed"])
            completed.assert_called_once_with("فني", expected)
        with patch.object(db, "_search_assigned_tasks_cached", return_value=["assigned"]) as assigned:
            self.assertEqual(db.search_assigned_tasks("فني", "2025-06-15"), ["assigned"])
            assigned.assert_called_once_with("فني", expected)

    def test_completed_and_assigned_queries_filter_directly_by_date(self):
        selected = datetime.date(2025, 6, 15)
        with patch.object(db, "fetch_all", return_value=[]) as fetch:
            db._search_completed_tasks_cached("فني", selected)
            query, params = fetch.call_args.args
            self.assertIn("execution_date = %s", query)
            self.assertEqual(params, ["فني", selected])
        with patch.object(db, "fetch_all", return_value=[]) as fetch:
            db._search_assigned_tasks_cached("فني", selected)
            query, params = fetch.call_args.args
            self.assertIn("assigned_date = %s", query)
            self.assertEqual(params, ["فني", selected])


class DailyReportStorageTests(unittest.TestCase):
    def test_download_returns_original_storage_bytes(self):
        report = {"image_url": "daily-reports/f/date.jpg", "image_data": b"legacy"}
        with patch.object(db, "get_daily_report_image_bytes", return_value=b"original") as downloader:
            self.assertEqual(db.daily_report_download_bytes(report), b"original")
            downloader.assert_called_once_with(report["image_url"])

    def test_download_supports_legacy_database_image(self):
        report = {"image_url": None, "image_data": b"legacy-original"}
        self.assertEqual(db.daily_report_download_bytes(report), b"legacy-original")

    def test_missing_storage_object_still_removes_stale_database_reference(self):
        with (
            patch.object(db, "delete_report_image", side_effect=db.ReportImageNotFoundError("missing")),
            patch.object(db, "_with_connection", return_value=True) as transaction,
            patch.object(db, "_invalidate_cache") as invalidate,
        ):
            result = db.delete_daily_report(42, "daily-reports/missing.jpg")
        self.assertTrue(result["storage_was_missing"])
        self.assertFalse(result["database_was_missing"])
        transaction.assert_called_once()
        invalidate.assert_called_once()

    def test_storage_failure_preserves_database_reference_and_cache(self):
        with (
            patch.object(db, "delete_report_image", side_effect=StorageOperationError("failed")),
            patch.object(db, "_with_connection") as transaction,
            patch.object(db, "_invalidate_cache") as invalidate,
        ):
            with self.assertRaises(StorageOperationError):
                db.delete_daily_report(42, "daily-reports/failure.jpg")
        transaction.assert_not_called()
        invalidate.assert_not_called()

    def test_missing_database_row_does_not_clear_cache(self):
        with (
            patch.object(db, "delete_report_image"),
            patch.object(db, "_with_connection", return_value=False),
            patch.object(db, "_invalidate_cache") as invalidate,
        ):
            result = db.delete_daily_report(999, "daily-reports/already-gone.jpg")
        self.assertTrue(result["database_was_missing"])
        invalidate.assert_not_called()


class InterfaceStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")

    def test_assignment_is_a_manager_tab_not_a_standalone_page(self):
        self.assertIn('"📌 إسناد مهمة"', self.app_source)
        self.assertNotIn("def assign_task_page", self.app_source)
        self.assertNotIn('current_page == "assign_task"', self.app_source)

    def test_required_views_use_shared_calendar_component(self):
        self.assertIn('date_selector("assign_task_date"', self.app_source)
        self.assertIn('date_selector(f"{key_prefix}_date", label="تاريخ الإسناد")', self.app_source)
        self.assertIn('date_selector(f"{key_prefix}_date", label="تاريخ التنفيذ")', self.app_source)

    def test_report_buttons_are_present(self):
        self.assertIn('"💾 حفظ الصورة"', self.app_source)
        self.assertIn('"🗑 حذف الصورة"', self.app_source)


if __name__ == "__main__":
    unittest.main()
