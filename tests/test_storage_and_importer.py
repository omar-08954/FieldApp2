"""اختبارات شاملة لنظامَي رفع الصور واستيراد Excel.

تُغطي:
  - build_object_key: التحقق من أن المفتاح دائماً ASCII آمن
  - resolve_column_mapping: التعرف الذكي على الأعمدة
  - match_technician: مطابقة أسماء الفنيين
  - import_excel: الاستيراد الكامل مع التكرار والأخطاء
"""

import datetime
import sys
import os
import unittest

# إضافة مسار المشروع إلى sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.storage import build_object_key
from database.excel_importer import (
    build_existing_keys,
    import_excel,
    match_technician,
    normalize_task_status,
    normalize_task_type,
    resolve_column_mapping,
)


# ---------------------------------------------------------------------------
# اختبارات build_object_key
# ---------------------------------------------------------------------------

class TestBuildObjectKey(unittest.TestCase):
    """التحقق من أن Object Key دائماً ASCII آمن بغض النظر عن المدخلات."""

    SAFE_RE = __import__("re").compile(r"^[A-Za-z0-9\-_./]+$")

    def _assert_safe(self, key: str):
        self.assertTrue(
            self.SAFE_RE.match(key),
            f"Object Key غير آمن: {key!r}",
        )

    def test_arabic_technician_id_is_safe(self):
        """معرف رقمي + اسم عربي → مفتاح آمن."""
        key = build_object_key(42, "2026-07-20", b"\xff\xd8\xff" + b"x" * 100, "image/jpeg")
        self._assert_safe(key)
        self.assertIn("42", key)

    def test_english_name_is_safe(self):
        key = build_object_key(7, "2026-07-20", b"\x89PNG\r\n\x1a\n" + b"x" * 100, "image/png")
        self._assert_safe(key)

    def test_spaces_in_id_stripped(self):
        """مسافات في المعرف تُزال."""
        key = build_object_key("user 99", "2026-07-20", b"\xff\xd8\xff" + b"x", "image/jpeg")
        self._assert_safe(key)
        self.assertNotIn(" ", key)

    def test_special_chars_stripped(self):
        """رموز خاصة تُزال من المعرف."""
        key = build_object_key("user@#99!", "2026-07-20", b"\xff\xd8\xff" + b"x", "image/jpeg")
        self._assert_safe(key)

    def test_empty_id_fallback(self):
        """معرف فارغ → يُستخدم 'unknown'."""
        key = build_object_key("", "2026-07-20", b"\xff\xd8\xff" + b"x", "image/jpeg")
        self._assert_safe(key)
        self.assertIn("unknown", key)

    def test_jpeg_extension(self):
        key = build_object_key(1, "2026-07-20", b"\xff\xd8\xff" + b"x", "image/jpeg")
        self.assertTrue(key.endswith(".jpg"), f"Expected .jpg, got: {key}")

    def test_png_extension(self):
        key = build_object_key(1, "2026-07-20", b"\x89PNG\r\n\x1a\n" + b"x", "image/png")
        self.assertTrue(key.endswith(".png"), f"Expected .png, got: {key}")

    def test_same_bytes_same_key(self):
        """نفس البايتات → نفس المفتاح (idempotent)."""
        data = b"\xff\xd8\xff" + b"abc" * 50
        k1 = build_object_key(5, "2026-07-20", data, "image/jpeg")
        k2 = build_object_key(5, "2026-07-20", data, "image/jpeg")
        self.assertEqual(k1, k2)

    def test_different_bytes_different_key(self):
        """بايتات مختلفة → مفاتيح مختلفة."""
        k1 = build_object_key(5, "2026-07-20", b"\xff\xd8\xff" + b"a" * 50, "image/jpeg")
        k2 = build_object_key(5, "2026-07-20", b"\xff\xd8\xff" + b"b" * 50, "image/jpeg")
        self.assertNotEqual(k1, k2)

    def test_key_starts_with_daily_reports(self):
        key = build_object_key(10, "2026-07-20", b"\xff\xd8\xff" + b"x", "image/jpeg")
        self.assertTrue(key.startswith("daily-reports/"), key)


# ---------------------------------------------------------------------------
# اختبارات resolve_column_mapping
# ---------------------------------------------------------------------------

class TestResolveColumnMapping(unittest.TestCase):

    def test_exact_arabic_match(self):
        mapping = resolve_column_mapping(["الفني", "رقم المهمة", "رقم الاشتراك"])
        self.assertEqual(mapping.get("الفني"), "الفني")
        self.assertEqual(mapping.get("رقم المهمة"), "رقم المهمة")

    def test_english_synonym(self):
        mapping = resolve_column_mapping(["technician", "task number", "subscription number"])
        self.assertEqual(mapping.get("technician"), "الفني")
        self.assertEqual(mapping.get("task number"), "رقم المهمة")

    def test_no_duplicate_targets(self):
        """لا يجوز أن يُعيَّن هدفان لنفس الاسم القياسي."""
        mapping = resolve_column_mapping(["الفني", "اسم الفني", "الموظف"])
        targets = list(mapping.values())
        self.assertEqual(len(targets), len(set(targets)), "هناك هدف مكرر في الخريطة")

    def test_fuzzy_match(self):
        """تطابق تقريبي: 'technicians' يجب أن يُطابق 'الفني'."""
        mapping = resolve_column_mapping(["technicians"])
        self.assertIn("technicians", mapping)

    def test_unknown_column_not_mapped(self):
        """عمود غير معروف لا يُضاف إلى الخريطة."""
        mapping = resolve_column_mapping(["xyz_unknown_col_123"])
        self.assertNotIn("xyz_unknown_col_123", mapping)


# ---------------------------------------------------------------------------
# اختبارات match_technician
# ---------------------------------------------------------------------------

class TestMatchTechnician(unittest.TestCase):

    TECHNICIANS = [
        {"fullname": "أرسلان سجاد", "city": "جدة"},
        {"fullname": "هاني صلاح", "city": "مكة"},
        {"fullname": "محمد أحمد", "city": "جدة"},
        {"fullname": "محمد علي", "city": "مكة"},
    ]

    def test_exact_match(self):
        r = match_technician("أرسلان سجاد", self.TECHNICIANS)
        self.assertTrue(r.is_known)
        self.assertEqual(r.resolved_name, "أرسلان سجاد")
        self.assertAlmostEqual(r.confidence, 1.0)

    def test_with_title_prefix(self):
        """م. أرسلان سجاد → أرسلان سجاد."""
        r = match_technician("م. أرسلان سجاد", self.TECHNICIANS)
        self.assertTrue(r.is_known)
        self.assertEqual(r.resolved_name, "أرسلان سجاد")

    def test_partial_first_name_only(self):
        """أرسلان فقط → يجب أن يجد أرسلان سجاد (فني وحيد بهذا الاسم الأول)."""
        r = match_technician("أرسلان", self.TECHNICIANS)
        self.assertTrue(r.is_known)
        self.assertEqual(r.resolved_name, "أرسلان سجاد")

    def test_ambiguous_first_name(self):
        """محمد فقط → غامض (محمد أحمد ومحمد علي)."""
        r = match_technician("محمد", self.TECHNICIANS)
        self.assertFalse(r.is_known)
        self.assertGreater(len(r.candidates), 1)

    def test_second_token_disambiguation(self):
        """محمد أحمد → يُفصل بين محمد أحمد ومحمد علي بالاسم الثاني."""
        r = match_technician("محمد أحمد", self.TECHNICIANS)
        self.assertTrue(r.is_known)
        self.assertEqual(r.resolved_name, "محمد أحمد")

    def test_unknown_name_returns_none(self):
        """اسم غير موجود إطلاقاً → is_known=False."""
        r = match_technician("خالد بن فلان", self.TECHNICIANS)
        self.assertFalse(r.is_known)
        self.assertIsNone(r.resolved_name)

    def test_empty_name(self):
        r = match_technician("", self.TECHNICIANS)
        self.assertFalse(r.is_known)
        self.assertIsNone(r.resolved_name)

    def test_no_new_technician_invented(self):
        """يجب ألا يُعيد اسماً غير موجود في القائمة."""
        r = match_technician("علي حسن", self.TECHNICIANS)
        if r.is_known:
            self.assertIn(r.resolved_name, [t["fullname"] for t in self.TECHNICIANS])


# ---------------------------------------------------------------------------
# اختبارات القيم الافتراضية
# ---------------------------------------------------------------------------

class TestNormalization(unittest.TestCase):

    def test_task_type_default(self):
        self.assertEqual(normalize_task_type(""), "تقني")
        self.assertEqual(normalize_task_type(None), "تقني")
        self.assertEqual(normalize_task_type("unknown"), "تقني")

    def test_task_type_known(self):
        self.assertEqual(normalize_task_type("تقني"), "تقني")
        self.assertEqual(normalize_task_type("زيرا"), "زيرا")

    def test_task_status_default(self):
        self.assertEqual(normalize_task_status(""), "تم الفحص")
        self.assertEqual(normalize_task_status(None), "تم الفحص")

    def test_task_status_known(self):
        self.assertEqual(normalize_task_status("عائق"), "عائق")
        self.assertEqual(normalize_task_status("مزال"), "مزال")
        self.assertEqual(normalize_task_status("تم الفحص"), "تم الفحص")


# ---------------------------------------------------------------------------
# اختبارات اكتشاف التكرار الحقيقي
# ---------------------------------------------------------------------------

class TestDuplicateDetection(unittest.TestCase):

    def test_same_all_fields_is_duplicate(self):
        existing = [
            {"technician": "أرسلان سجاد", "task_number": "T001",
             "subscription_number": "S001", "task_type": "تقني",
             "task_status": "تم الفحص", "city": "جدة"},
        ]
        keys = build_existing_keys(existing)
        self.assertEqual(len(keys), 1)

    def test_different_status_not_duplicate(self):
        """نفس رقم المهمة لكن حالة مختلفة → ليس تكراراً."""
        existing = [
            {"technician": "أرسلان سجاد", "task_number": "T001",
             "subscription_number": "S001", "task_type": "تقني",
             "task_status": "عائق", "city": "جدة"},
        ]
        keys = build_existing_keys(existing)
        from database.excel_importer import _make_duplicate_key
        new_key = _make_duplicate_key("أرسلان سجاد", "T001", "S001", "تقني", "تم الفحص", "جدة")
        self.assertNotIn(new_key, keys)


# ---------------------------------------------------------------------------
# اختبارات import_excel الشاملة
# ---------------------------------------------------------------------------

class TestImportExcel(unittest.TestCase):

    def _make_df(self, rows):
        import pandas as pd
        return pd.DataFrame(rows)

    TECHNICIANS = [
        {"fullname": "أرسلان سجاد", "city": "جدة"},
        {"fullname": "هاني صلاح", "city": "مكة"},
    ]

    def test_basic_import(self):
        df = self._make_df([
            {"الفني": "أرسلان سجاد", "رقم المهمة": "T001", "رقم الاشتراك": "S001",
             "نوع المهمة": "تقني", "حالة المهمة": "تم الفحص"},
        ])
        rows, report = import_excel(df, self.TECHNICIANS, [])
        self.assertEqual(report.imported, 1)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(len(rows), 1)

    def test_unknown_technician_not_imported(self):
        """فني غير معروف لا يُستورد ويُضاف إلى قائمة الفنيين غير المعروفين."""
        df = self._make_df([
            {"الفني": "خالد بن فلان", "رقم المهمة": "T002", "رقم الاشتراك": "S002"},
        ])
        rows, report = import_excel(df, self.TECHNICIANS, [])
        self.assertEqual(report.imported, 0)
        self.assertEqual(report.unknown_technician_count, 1)
        self.assertEqual(len(rows), 0)

    def test_duplicate_skipped(self):
        """مهمة مكررة تُتجاهل."""
        existing = [
            {"technician": "أرسلان سجاد", "task_number": "T001",
             "subscription_number": "S001", "task_type": "تقني",
             "task_status": "تم الفحص", "city": "جدة"},
        ]
        df = self._make_df([
            {"الفني": "أرسلان سجاد", "رقم المهمة": "T001", "رقم الاشتراك": "S001",
             "نوع المهمة": "تقني", "حالة المهمة": "تم الفحص"},
        ])
        rows, report = import_excel(df, self.TECHNICIANS, existing)
        self.assertEqual(report.imported, 0)
        self.assertEqual(report.duplicated, 1)

    def test_different_status_not_duplicate(self):
        """نفس رقم المهمة لكن حالة مختلفة → يُستورد."""
        existing = [
            {"technician": "أرسلان سجاد", "task_number": "T001",
             "subscription_number": "S001", "task_type": "تقني",
             "task_status": "عائق", "city": "جدة"},
        ]
        df = self._make_df([
            {"الفني": "أرسلان سجاد", "رقم المهمة": "T001", "رقم الاشتراك": "S001",
             "نوع المهمة": "تقني", "حالة المهمة": "تم الفحص"},
        ])
        rows, report = import_excel(df, self.TECHNICIANS, existing)
        self.assertEqual(report.imported, 1)

    def test_empty_task_number_is_error(self):
        """رقم مهمة فارغ → خطأ، لا يوقف الاستيراد."""
        df = self._make_df([
            {"الفني": "أرسلان سجاد", "رقم المهمة": "", "رقم الاشتراك": "S001"},
            {"الفني": "هاني صلاح", "رقم المهمة": "T003", "رقم الاشتراك": "S003"},
        ])
        rows, report = import_excel(df, self.TECHNICIANS, [])
        self.assertEqual(report.imported, 1)
        self.assertEqual(report.error_count, 1)

    def test_default_task_type_and_status(self):
        """نوع وحالة المهمة الافتراضيان يُطبَّقان عند الغياب."""
        df = self._make_df([
            {"الفني": "أرسلان سجاد", "رقم المهمة": "T010", "رقم الاشتراك": "S010"},
        ])
        rows, report = import_excel(df, self.TECHNICIANS, [])
        self.assertEqual(report.imported, 1)
        task_type = rows[0][3]
        task_status = rows[0][4]
        self.assertEqual(task_type, "تقني")
        self.assertEqual(task_status, "تم الفحص")

    def test_city_from_db_overrides_excel(self):
        """مدينة الفني من قاعدة البيانات تُقدَّم على مدينة الملف."""
        df = self._make_df([
            {"الفني": "أرسلان سجاد", "رقم المهمة": "T020", "رقم الاشتراك": "S020",
             "المدينة": "الرياض"},  # مدينة خاطئة في الملف
        ])
        rows, report = import_excel(df, self.TECHNICIANS, [])
        self.assertEqual(report.imported, 1)
        city = rows[0][5]
        self.assertEqual(city, "جدة")  # من قاعدة البيانات

    def test_report_timing(self):
        df = self._make_df([
            {"الفني": "هاني صلاح", "رقم المهمة": "T030", "رقم الاشتراك": "S030"},
        ])
        _, report = import_excel(df, self.TECHNICIANS, [])
        self.assertGreater(report.elapsed_seconds, 0)

    def test_column_mapping_applied(self):
        """أعمدة بأسماء إنجليزية تُعيَّن تلقائياً."""
        df = self._make_df([
            {"technician": "أرسلان سجاد", "task number": "T040", "subscription number": "S040"},
        ])
        rows, report = import_excel(df, self.TECHNICIANS, [])
        self.assertEqual(report.imported, 1)

    def test_no_import_when_no_technicians(self):
        """لا فنيون في قاعدة البيانات → كل الصفوف تُرفض."""
        df = self._make_df([
            {"الفني": "أرسلان سجاد", "رقم المهمة": "T050", "رقم الاشتراك": "S050"},
        ])
        rows, report = import_excel(df, [], [])
        self.assertEqual(report.imported, 0)
        self.assertEqual(report.unknown_technician_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
