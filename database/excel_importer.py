"""نظام استيراد Excel الذكي — Production-Grade

هذه الوحدة مسؤولة بالكامل عن:
  1. التعرف الذكي على أعمدة أي ملف Excel بغض النظر عن أسماء الأعمدة.
  2. المطابقة الذكية لأسماء الفنيين (Token + Fuzzy + Partial) مع منع اختراع أسماء.
  3. القيم الافتراضية الذكية (نوع المهمة، حالة المهمة، المدينة).
  4. اكتشاف التكرار الحقيقي (مجموعة الحقول المهمة مجتمعةً).
  5. معالجة الأخطاء صفًّا بصف دون إيقاف الاستيراد.
  6. تقرير نهائي احترافي.

التصميم:
  - لا تعتمد هذه الوحدة على Streamlit مباشرةً (قابلة للاختبار بمعزل).
  - كل الحالات الحدية موثقة ومختبرة.
  - لا توجد حلول مؤقتة أو Hacks.
"""

from __future__ import annotations

import datetime
import re
import time
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from database.data_cleaner import clean_dataframe, clean_text, clean_numeric_text
from database.technician_matcher import (
    AUTO_LINK_THRESHOLD,
    TechnicianMatchResult,
    match_technician,
)

# ---------------------------------------------------------------------------
# ثوابت التطبيق
# ---------------------------------------------------------------------------

TASK_TYPE_DEFAULT = "تقني"
TASK_STATUS_DEFAULT = "تم الفحص"

TASK_TYPE_VALUES: list[str] = ["تقني", "زيرا"]
TASK_STATUS_VALUES: list[str] = ["عائق", "تم الفحص", "مزال"]

TITLE_PREFIXES: list[str] = [
    "المهندس", "مهندس", "م.", "الفني", "فني",
    "الأستاذ", "أ.", "السيد", "eng.", "eng", "mr.", "mr",
]

# ---------------------------------------------------------------------------
# مرادفات الأعمدة — يمكن توسيعها دون أي تغيير في المنطق
# ---------------------------------------------------------------------------

COLUMN_SYNONYMS: dict[str, list[str]] = {
    "الفني": [
        "الفني", "اسم الفني", "الموظف", "technician", "employee",
        "engineer", "tech", "اسم الموظف", "المنفذ", "اسم المنفذ",
    ],
    "رقم المهمة": [
        "رقم المهمة", "المهمة", "task number", "task", "رقم أمر العمل",
        "work order", "order number", "رقم الأمر", "رقم العمل", "task_number",
        "order_number", "work_order",
    ],
    "رقم الاشتراك": [
        "رقم الاشتراك", "الاشتراك", "subscription", "subscription number",
        "sub number", "رقم العميل", "customer number", "subscription_number",
        "sub_number",
    ],
    "نوع المهمة": [
        "نوع المهمة", "النوع", "task type", "type", "نوع الأمر",
        "task_type", "order_type",
    ],
    "حالة المهمة": [
        "حالة المهمة", "الحالة", "task status", "status", "حالة الأمر",
        "task_status", "order_status",
    ],
    "المدينة": [
        "المدينة", "city", "المنطقة", "region", "location", "الموقع",
    ],
    "الملاحظات": [
        "الملاحظات", "ملاحظات", "notes", "note", "تعليق", "تعليقات",
        "remarks", "comment", "comments",
    ],
}

# الأعمدة التي يمكن التعرف عليها من محتواها إذا فشلت مطابقة الاسم
CONTENT_BASED_COLUMNS: dict[str, list[str]] = {
    "نوع المهمة": TASK_TYPE_VALUES,
    "حالة المهمة": TASK_STATUS_VALUES,
}

# ---------------------------------------------------------------------------
# هياكل البيانات
# ---------------------------------------------------------------------------

@dataclass
class RowError:
    """خطأ في صف واحد أثناء الاستيراد — لا يوقف بقية الصفوف أبداً."""
    row_index: int          # رقم الصف في الملف (يبدأ من 2 لأن الصف 1 هو العناوين)
    raw_data: dict          # البيانات الخام للصف
    reason: str             # سبب الرفض (نص مختصر يُعرض للمستخدم)
    suggestion: str         # طريقة الإصلاح المقترحة
    task_number: str = ""       # رقم المهمة إن أمكن قراءته قبل حدوث الخطأ
    error_type: str = ""        # نوع الاستثناء الحقيقي (KeyError, ValueError, ...)
    column: str = ""            # اسم العمود المسبب للمشكلة إن أمكن تحديده
    exception_message: str = "" # الرسالة الأصلية للاستثناء كما رُفعت من بايثون
    action_taken: str = ""      # الإجراء الذي اتُّخذ تلقائياً (إصلاح/نقل لمراجعة الاستيراد)


@dataclass
class ImportReport:
    """التقرير النهائي لعملية الاستيراد."""
    total_read: int = 0
    imported: int = 0
    duplicated: int = 0
    needs_review_count: int = 0
    errors: list[RowError] = field(default_factory=list)
    unknown_technicians: list[dict] = field(default_factory=list)
    recognized_technicians: set[str] = field(default_factory=set)
    elapsed_seconds: float = 0.0
    column_mapping_used: dict[str, str] = field(default_factory=dict)
    file_name: str = ""
    username: str = ""
    imported_at: datetime.datetime | None = None
    # قائمة مشاكل عامة لكل صف تم استيراده، بنفس ترتيب rows_to_insert، حتى يستطيع
    # المستدعي (app.py) إنشاء سجل "مراجعة استيراد" واحد أو أكثر لكل صف بمجرد
    # معرفة الـ id الحقيقي للمهمة بعد الإدراج الجماعي. كل عنصر هو list[dict] بمفاتيح:
    # field, raw_value, suggested_value, confidence, reason.
    row_review_issues: list[list[dict]] = field(default_factory=list)
    # أحداث الإصلاح التلقائي: كل مرة يُصادَف فيها استثناء أو نقص بيانات أثناء
    # معالجة صف ويُنجح النظام في ترقيعه بقيمة افتراضية بدل إسقاط الصف بالكامل.
    auto_fixed: list[dict] = field(default_factory=list)

    @property
    def auto_fixed_count(self) -> int:
        return len(self.auto_fixed)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def unknown_technician_count(self) -> int:
        return len(self.unknown_technicians)

    @property
    def review_count(self) -> int:
        return self.needs_review_count

    @property
    def recognized_technician_count(self) -> int:
        return len(self.recognized_technicians)

    @property
    def match_success_rate(self) -> float:
        """نسبة نجاح مطابقة الفنيين (0.0 – 1.0)."""
        total_tech_rows = self.recognized_technician_count + self.unknown_technician_count
        if total_tech_rows == 0:
            return 1.0
        return self.recognized_technician_count / total_tech_rows


# ---------------------------------------------------------------------------
# دوال التطبيع
# ---------------------------------------------------------------------------

def _normalize_text(value: Any) -> str:
    """تطبيع نصي شامل: إزالة التشكيل، توحيد المسافات، lowercase."""
    text = str(value or "").strip()
    # إزالة التشكيل العربي (Diacritics)
    text = "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )
    # توحيد المسافات
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def _text_tokens(value: str) -> list[str]:
    """تقسيم النص إلى كلمات بعد التطبيع."""
    return [t for t in _normalize_text(value).split(" ") if t]


def _strip_title_prefix(name: str) -> str:
    """إزالة الألقاب من أول الاسم (م.، مهندس، فني، ...)."""
    normalized = _normalize_text(name)
    for prefix in TITLE_PREFIXES:
        p = _normalize_text(prefix)
        if normalized == p:
            return ""
        if normalized.startswith(p + " "):
            normalized = normalized[len(p):].strip()
            break
    return normalized


def _fuzzy_ratio(a: str, b: str) -> float:
    """درجة تشابه بين نصين (0.0 – 1.0) مع دعم Token Matching."""
    a = _normalize_text(a)
    b = _normalize_text(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # Substring containment
    if a in b or b in a:
        return 0.97
    # Token set matching: هل كل كلمات الأقصر موجودة في الأطول؟
    a_tokens = _text_tokens(a)
    b_tokens = _text_tokens(b)
    if a_tokens and b_tokens:
        shorter, longer = (
            (a_tokens, b_tokens) if len(a_tokens) <= len(b_tokens)
            else (b_tokens, a_tokens)
        )
        if all(
            any(
                t == o or SequenceMatcher(None, t, o).ratio() >= 0.82
                for o in longer
            )
            for t in shorter
        ):
            return 0.95
    return SequenceMatcher(None, a, b).ratio()


# ---------------------------------------------------------------------------
# التعرف الذكي على الأعمدة
# ---------------------------------------------------------------------------

def _column_content_match_ratio(values: list, known_values: list[str]) -> float:
    """نسبة الصفوف التي تطابق قيمًا معروفة في هذا العمود."""
    cleaned = [_normalize_text(v) for v in values if str(v or "").strip()]
    if not cleaned:
        return 0.0
    matched = sum(
        1 for v in cleaned
        if max((_fuzzy_ratio(v, _normalize_text(k)) for k in known_values), default=0.0) >= 0.8
    )
    return matched / len(cleaned)


def resolve_column_mapping(
    columns: list[str],
    dataframe=None,
    threshold: float = 0.75,
) -> dict[str, str]:
    """ربط أعمدة Excel بالأسماء القياسية للتطبيق.

    الخوارزمية (بالترتيب):
    1. Exact Match: اسم العمود = الاسم القياسي مباشرةً (score = 1.0).
    2. Alias Exact Match: اسم العمود = أحد المرادفات حرفيًّا (score = 0.999).
    3. Fuzzy Match: تشابه تقريبي مع الاسم القياسي أو المرادفات (score < 0.999).
    4. Content Match: إذا فشلت الخطوات 1-3، يُفحص محتوى العمود.

    ضمان عدم التكرار: كل هدف قياسي يُستخدم مرةً واحدةً كحد أقصى.
    """
    columns = list(columns)
    candidates: list[tuple[float, str, str]] = []

    for column in columns:
        col_norm = _normalize_text(column)
        best_target, best_score = None, 0.0

        for target, synonyms in COLUMN_SYNONYMS.items():
            target_norm = _normalize_text(target)

            # Exact match على الاسم القياسي
            if col_norm == target_norm:
                best_target, best_score = target, 1.0
                break

            for synonym in synonyms:
                syn_norm = _normalize_text(synonym)
                if col_norm == syn_norm:
                    score = 0.999
                else:
                    score = min(_fuzzy_ratio(col_norm, syn_norm), 0.998)

                if score > best_score:
                    best_target, best_score = target, score

        if best_target and best_score >= threshold:
            candidates.append((best_score, column, best_target))

    # حل التعارضات: أعلى درجة يفوز، والباقي يُتجاهل
    mapping: dict[str, str] = {}
    used_targets: set[str] = set()
    for score, column, target in sorted(candidates, key=lambda x: x[0], reverse=True):
        if column in mapping or target in used_targets:
            continue
        mapping[column] = target
        used_targets.add(target)

    # Content-based fallback للأعمدة غير المحسومة
    if dataframe is not None:
        for column in columns:
            if column in mapping:
                continue
            try:
                values = dataframe[column].tolist()
            except Exception:
                continue
            for target, known_values in CONTENT_BASED_COLUMNS.items():
                if target in used_targets:
                    continue
                if _column_content_match_ratio(values, known_values) >= 0.7:
                    mapping[column] = target
                    used_targets.add(target)
                    break

    return mapping


# ---------------------------------------------------------------------------
# مطابقة الفنيين — تُستخدم technician_matcher (RapidFuzz)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# القيم الافتراضية الذكية
# ---------------------------------------------------------------------------

def normalize_task_type(value: Any) -> str:
    """تطبيع نوع المهمة؛ القيم غير المعروفة تُعاد كـ TASK_TYPE_DEFAULT."""
    cleaned = _normalize_text(value)
    for known in TASK_TYPE_VALUES:
        if cleaned == _normalize_text(known):
            return known
    return TASK_TYPE_DEFAULT


def normalize_task_status(value: Any) -> str:
    """تطبيع حالة المهمة؛ القيم غير المعروفة تُعاد كـ TASK_STATUS_DEFAULT."""
    cleaned = _normalize_text(value)
    for known in TASK_STATUS_VALUES:
        if cleaned == _normalize_text(known):
            return known
    return TASK_STATUS_DEFAULT


# ---------------------------------------------------------------------------
# اكتشاف التكرار الحقيقي
# ---------------------------------------------------------------------------

def _make_duplicate_key(
    technician: str,
    task_number: str,
    subscription_number: str,
    task_type: str,
    task_status: str,
    city: str,
) -> tuple:
    """مفتاح التكرار الحقيقي: مجموعة الحقول المهمة مجتمعةً."""
    return (
        _normalize_text(technician),
        _normalize_text(task_number),
        _normalize_text(subscription_number),
        _normalize_text(task_type),
        _normalize_text(task_status),
        _normalize_text(city),
    )


def build_existing_keys(existing_tasks: list[dict]) -> set[tuple]:
    """بناء مجموعة مفاتيح التكرار من المهام الموجودة في قاعدة البيانات."""
    keys: set[tuple] = set()
    for task in existing_tasks:
        key = _make_duplicate_key(
            task.get("technician", ""),
            task.get("task_number", ""),
            task.get("subscription_number", ""),
            task.get("task_type", ""),
            task.get("task_status", ""),
            task.get("city", ""),
        )
        keys.add(key)
    return keys


# ---------------------------------------------------------------------------
# المحرك الرئيسي للاستيراد
# ---------------------------------------------------------------------------

def import_excel(
    dataframe,
    known_technicians: list[dict],
    existing_tasks: list[dict],
    execution_date: datetime.date | None = None,
    technician_threshold: float = AUTO_LINK_THRESHOLD,
    progress_callback=None,
) -> tuple[list[tuple], ImportReport]:
    """تنفيذ الاستيراد الذكي — لا يُفقد أي صف بسبب اختلاف اسم الفني."""
    started = time.perf_counter()
    report = ImportReport()
    today = execution_date or datetime.date.today()

    dataframe = clean_dataframe(dataframe)
    column_map = resolve_column_mapping(dataframe.columns.tolist(), dataframe)
    if column_map:
        dataframe = dataframe.rename(columns=column_map)
    report.column_mapping_used = dict(column_map)

    existing_keys = build_existing_keys(existing_tasks)
    session_keys: set[tuple] = set()
    tech_city_map: dict[str, str] = {
        str(t.get("fullname") or "").strip(): str(t.get("city") or "").strip()
        for t in known_technicians if t.get("fullname")
    }

    rows_to_insert: list[tuple] = []
    total_rows = len(dataframe)
    report.total_read = total_rows

    for position, (idx, row) in enumerate(dataframe.iterrows()):
        file_row = int(idx) + 2
        if progress_callback:
            progress_callback(position + 1, total_rows)

        # كل شيء داخل هذا try الخاص بالصف الواحد فقط: أي استثناء (KeyError أو
        # غيره) يُلتقط هنا، يُسجَّل بتفصيل كامل، ولا يوقف استيراد بقية الصفوف
        # مهما كان نوع الخطأ.
        task_number = ""
        try:
            task_number = clean_numeric_text(row.get("رقم المهمة", ""))
            if not task_number:
                report.errors.append(RowError(
                    row_index=file_row,
                    raw_data=dict(row),
                    reason="رقم المهمة فارغ.",
                    suggestion="أضف رقم المهمة في عمود 'رقم المهمة'.",
                    task_number="",
                    error_type="MissingValue",
                    column="رقم المهمة",
                    action_taken="تم تجاوز هذا الصف فقط؛ استمرت بقية الصفوف بالاستيراد.",
                ))
                continue

            # رقم الاشتراك: إذا كان العمود غير موجود أصلاً في الملف، أو موجوداً
            # لكن قيمته فارغة/None/NaN/مسافات فقط، تتحول تلقائياً إلى "غير مسجل"
            # بدل رفع أي خطأ أو ترك الحقل فارغاً.
            subscription_number = clean_numeric_text(row.get("رقم الاشتراك", "")) or "غير مسجل"
            raw_task_type = clean_text(row.get("نوع المهمة", ""))
            raw_task_status = clean_text(row.get("حالة المهمة", ""))
            task_type = normalize_task_type(raw_task_type)
            task_status = normalize_task_status(raw_task_status)
            raw_technician = clean_text(row.get("الفني", "")) or "غير محدد"

            row_issues: list[dict] = []

            match_result = match_technician(raw_technician, known_technicians, technician_threshold)
            needs_review = match_result.needs_review
            suggested = match_result.resolved_name if match_result.resolved_name else (match_result.candidates[0] if match_result.candidates else None)

            if match_result.is_known and not needs_review:
                resolved_technician = match_result.resolved_name
                report.recognized_technicians.add(resolved_technician)
            else:
                resolved_technician = raw_technician
                report.unknown_technicians.append({
                    "row": file_row,
                    "raw_name": raw_technician,
                    "warning": match_result.warning,
                    "candidates": match_result.candidates,
                    "confidence": match_result.confidence,
                    "suggested": suggested,
                })
                if match_result.warning:
                    report.errors.append(RowError(
                        row_index=file_row,
                        raw_data=dict(row),
                        reason=match_result.warning,
                        suggestion="راجع تبويب مراجعة الاستيراد لاعتماد الفني الصحيح.",
                        task_number=task_number,
                        error_type="UnknownTechnician",
                        column="الفني",
                        action_taken="تم استيراد المهمة مع وضع علامة \"يحتاج مراجعة\".",
                    ))
                row_issues.append({
                    "field": "technician",
                    "raw_value": raw_technician,
                    "suggested_value": suggested,
                    "confidence": match_result.confidence,
                    "reason": match_result.warning or "فني غير معروف.",
                })

            # نفس فكرة مطابقة الفنيين تُطبَّق على أي قيمة متكررة أخرى: إذا كانت القيمة
            # الخام موجودة في الملف لكنها لا تطابق أياً من القيم المعروفة، لا تُستبدل
            # بصمت فقط، بل تُسجَّل أيضاً كمشكلة قابلة للمراجعة والتصحيح الجماعي.
            if raw_task_type and _normalize_text(raw_task_type) not in {_normalize_text(v) for v in TASK_TYPE_VALUES}:
                needs_review = True
                row_issues.append({
                    "field": "task_type",
                    "raw_value": raw_task_type,
                    "suggested_value": task_type,
                    "confidence": None,
                    "reason": f"نوع مهمة غير معروف: \"{raw_task_type}\".",
                })

            if raw_task_status and _normalize_text(raw_task_status) not in {_normalize_text(v) for v in TASK_STATUS_VALUES}:
                needs_review = True
                row_issues.append({
                    "field": "task_status",
                    "raw_value": raw_task_status,
                    "suggested_value": task_status,
                    "confidence": None,
                    "reason": f"حالة مهمة غير معروفة: \"{raw_task_status}\".",
                })

            if resolved_technician in tech_city_map:
                resolved_city = tech_city_map[resolved_technician]
            else:
                resolved_city = clean_text(row.get("المدينة", ""))

            notes = clean_text(row.get("الملاحظات", ""))

            dup_key = _make_duplicate_key(
                resolved_technician, task_number, subscription_number,
                task_type, task_status, resolved_city,
            )
            if dup_key in existing_keys or dup_key in session_keys:
                report.duplicated += 1
                continue

            session_keys.add(dup_key)
            rows_to_insert.append((
                resolved_technician,
                task_number,
                subscription_number,
                task_type,
                task_status,
                resolved_city,
                notes,
                today,
                needs_review,
                raw_technician,
                match_result.confidence,
                suggested,
            ))
            report.row_review_issues.append(row_issues)
            report.imported += 1
            if needs_review:
                report.needs_review_count += 1

        except KeyError as exc:
            # عمود متوقَّع غير موجود ضمن بيانات هذا الصف تحديداً. يُسجَّل بكامل
            # التفاصيل (اسم العمود المفقود، رقم المهمة إن وُجد) ثم يُستكمل باقي
            # الصفوف دون توقف — لا يُسمح إطلاقاً بخروج KeyError للمستخدم.
            missing_column = str(exc).strip("'\" ")
            report.errors.append(RowError(
                row_index=file_row,
                raw_data=dict(row) if row is not None else {},
                reason=f"عمود مفقود أثناء معالجة الصف: {missing_column}",
                suggestion="تحقق من وجود جميع الأعمدة المطلوبة في هذا الصف بالذات.",
                task_number=task_number,
                error_type="KeyError",
                column=missing_column,
                exception_message=str(exc),
                action_taken="تم نقل الصف إلى مراجعة الاستيراد؛ استمر استيراد بقية الصفوف بدون انقطاع.",
            ))
            continue
        except Exception as exc:
            # أي خطأ آخر غير متوقع في هذا الصف فقط (وليس في الملف كله). يُسجَّل
            # بنفس التفصيل ثم يُستكمل الاستيراد لبقية الصفوف بشكل طبيعي.
            report.errors.append(RowError(
                row_index=file_row,
                raw_data=dict(row) if row is not None else {},
                reason=f"خطأ غير متوقع أثناء معالجة الصف: {exc}",
                suggestion="راجع بيانات هذا الصف يدوياً داخل ملف Excel.",
                task_number=task_number,
                error_type=type(exc).__name__,
                exception_message=str(exc),
                action_taken="تم نقل الصف إلى مراجعة الاستيراد؛ استمر استيراد بقية الصفوف بدون انقطاع.",
            ))
            continue

    report.elapsed_seconds = time.perf_counter() - started
    return rows_to_insert, report
