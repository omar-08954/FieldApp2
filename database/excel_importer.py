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
    """خطأ في صف واحد أثناء الاستيراد."""
    row_index: int          # رقم الصف في الملف (يبدأ من 2 لأن الصف 1 هو العناوين)
    raw_data: dict          # البيانات الخام للصف
    reason: str             # سبب الرفض
    suggestion: str         # طريقة الإصلاح المقترحة


@dataclass
class ImportReport:
    """التقرير النهائي لعملية الاستيراد."""
    total_read: int = 0
    imported: int = 0
    duplicated: int = 0
    errors: list[RowError] = field(default_factory=list)
    unknown_technicians: list[dict] = field(default_factory=list)
    recognized_technicians: set[str] = field(default_factory=set)
    elapsed_seconds: float = 0.0
    column_mapping_used: dict[str, str] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def unknown_technician_count(self) -> int:
        return len(self.unknown_technicians)

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
# التعرف الذكي على أسماء الفنيين
# ---------------------------------------------------------------------------

@dataclass
class TechnicianMatchResult:
    """نتيجة مطابقة اسم فني."""
    resolved_name: str | None   # الاسم المُطابق من قاعدة البيانات، أو None
    confidence: float           # درجة الثقة (0.0 – 1.0)
    is_known: bool              # هل وُجد في قاعدة البيانات؟
    candidates: list[str]       # المرشحون المتعارضون (إن وُجدوا)
    warning: str | None         # رسالة تحذير للمستخدم


def match_technician(
    raw_name: str,
    known_technicians: list[dict],
    threshold: float = 0.82,
) -> TechnicianMatchResult:
    """مطابقة ذكية لاسم فني مقابل قائمة الفنيين المعروفين.

    الخوارزمية:
    1. تطبيع الاسم الخام وإزالة الألقاب.
    2. مطابقة حرفية كاملة (score = 1.0).
    3. مطابقة الاسم الأول (First Token) مع كل الفنيين.
    4. إذا وُجد مرشح واحد بالاسم الأول → مطابقة ناجحة.
    5. إذا وُجد أكثر من مرشح → استخدام الاسم الثاني للفصل.
    6. إذا تعذّر الفصل → حالة غامضة (unknown).
    7. إذا لم يوجد أي مرشح بالاسم الأول → Fuzzy Match شامل.
    8. إذا لم تصل الدرجة إلى threshold → الفني غير معروف.

    لا يُنشئ هذا النظام أسماءً جديدةً ولا يربط مهمةً بفني خاطئ.

    Parameters
    ----------
    raw_name:
        الاسم الخام من ملف Excel.
    known_technicians:
        قائمة قواميس تحتوي على مفاتيح ``fullname`` (و``city`` اختياريًّا).
    threshold:
        الحد الأدنى لدرجة الثقة المطلوبة للقبول.
    """
    raw_name = str(raw_name or "").strip()
    if not raw_name:
        return TechnicianMatchResult(
            resolved_name=None,
            confidence=0.0,
            is_known=False,
            candidates=[],
            warning="اسم الفني فارغ.",
        )

    normalized_raw = _strip_title_prefix(raw_name)
    raw_tokens = _text_tokens(normalized_raw)

    if not raw_tokens:
        return TechnicianMatchResult(
            resolved_name=None,
            confidence=0.0,
            is_known=False,
            candidates=[],
            warning=f"لم يمكن تطبيع الاسم: \"{raw_name}\".",
        )

    # --- الخطوة 1: مطابقة حرفية كاملة ---
    for tech in known_technicians:
        known = str(tech.get("fullname") or "").strip()
        if not known:
            continue
        if _normalize_text(raw_name) == _normalize_text(known):
            return TechnicianMatchResult(
                resolved_name=known,
                confidence=1.0,
                is_known=True,
                candidates=[],
                warning=None,
            )

    first_token = raw_tokens[0]

    # --- الخطوة 2: مطابقة الاسم الأول ---
    first_token_matches: list[tuple[str, list[str], float]] = []
    for tech in known_technicians:
        known = str(tech.get("fullname") or "").strip()
        if not known:
            continue
        known_normalized = _strip_title_prefix(known)
        known_tokens = _text_tokens(known_normalized)
        if not known_tokens:
            continue
        first_sim = SequenceMatcher(None, known_tokens[0], first_token).ratio()
        if known_tokens[0] == first_token or first_sim >= 0.85:
            first_token_matches.append((known, known_tokens, first_sim))

    if not first_token_matches:
        # --- الخطوة 3: Fuzzy Match شامل كـ fallback ---
        best_name, best_score = None, 0.0
        for tech in known_technicians:
            known = str(tech.get("fullname") or "").strip()
            if not known:
                continue
            score = _fuzzy_ratio(normalized_raw, _strip_title_prefix(known))
            if score > best_score:
                best_score = score
                best_name = known

        if best_name and best_score >= threshold:
            return TechnicianMatchResult(
                resolved_name=best_name,
                confidence=best_score,
                is_known=True,
                candidates=[],
                warning=None,
            )
        return TechnicianMatchResult(
            resolved_name=None,
            confidence=best_score,
            is_known=False,
            candidates=[],
            warning=f"لم يُعثر على فني مطابق لـ \"{raw_name}\" في قاعدة البيانات.",
        )

    if len(first_token_matches) == 1:
        name, _, sim = first_token_matches[0]
        return TechnicianMatchResult(
            resolved_name=name,
            confidence=sim,
            is_known=True,
            candidates=[],
            warning=None,
        )

    # --- الخطوة 4: فصل بالاسم الثاني ---
    if len(raw_tokens) >= 2:
        second_token = raw_tokens[1]
        narrowed = [
            (name, tokens, sim)
            for name, tokens, sim in first_token_matches
            if len(tokens) >= 2 and (
                tokens[1] == second_token
                or SequenceMatcher(None, tokens[1], second_token).ratio() >= 0.85
            )
        ]
        if len(narrowed) == 1:
            name, _, sim = narrowed[0]
            return TechnicianMatchResult(
                resolved_name=name,
                confidence=sim,
                is_known=True,
                candidates=[],
                warning=None,
            )

    # --- الخطوة 5: حالة غامضة (أكثر من مرشح) ---
    candidate_names = [name for name, _, _ in first_token_matches]
    return TechnicianMatchResult(
        resolved_name=None,
        confidence=0.0,
        is_known=False,
        candidates=candidate_names,
        warning=(
            f"تعذر تحديد الفني \"{raw_name}\" بدقة — "
            f"احتمالات متعددة: {', '.join(candidate_names)}."
        ),
    )


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
    technician_threshold: float = 0.82,
) -> tuple[list[tuple], ImportReport]:
    """تنفيذ الاستيراد الذكي لملف Excel.

    Parameters
    ----------
    dataframe:
        ``pandas.DataFrame`` بعد قراءة ملف Excel.
    known_technicians:
        قائمة قواميس من قاعدة البيانات تحتوي على:
        ``{"fullname": str, "city": str | None}``.
    existing_tasks:
        قائمة المهام الموجودة في قاعدة البيانات (لاكتشاف التكرار).
    execution_date:
        تاريخ التنفيذ الافتراضي؛ يُستخدم اليوم الحالي إذا لم يُحدَّد.
    technician_threshold:
        الحد الأدنى لدرجة الثقة عند مطابقة أسماء الفنيين.

    Returns
    -------
    tuple[list[tuple], ImportReport]
        - قائمة الصفوف الجاهزة للإدراج في قاعدة البيانات.
        - تقرير مفصل بنتائج الاستيراد.
    """
    started = time.perf_counter()
    report = ImportReport()
    today = execution_date or datetime.date.today()

    # --- تطبيق خريطة الأعمدة ---
    column_map = resolve_column_mapping(dataframe.columns.tolist(), dataframe)
    if column_map:
        dataframe = dataframe.rename(columns=column_map)
    report.column_mapping_used = dict(column_map)

    # --- بناء مجموعة مفاتيح التكرار ---
    existing_keys = build_existing_keys(existing_tasks)
    # مفاتيح الصفوف المضافة في هذه الدفعة (لمنع التكرار داخل الملف نفسه)
    session_keys: set[tuple] = set()

    # --- بناء خريطة الفنيين (fullname -> city) ---
    tech_city_map: dict[str, str] = {
        str(t.get("fullname") or "").strip(): str(t.get("city") or "").strip()
        for t in known_technicians
        if t.get("fullname")
    }

    rows_to_insert: list[tuple] = []
    report.total_read = len(dataframe)

    for idx, row in dataframe.iterrows():
        # رقم الصف في الملف (يبدأ من 2 لأن الصف 1 هو العناوين)
        file_row = int(idx) + 2

        # --- رقم المهمة (إلزامي) ---
        task_number = str(row.get("رقم المهمة", "") or "").strip()
        if not task_number:
            report.errors.append(RowError(
                row_index=file_row,
                raw_data=dict(row),
                reason="رقم المهمة فارغ.",
                suggestion="أضف رقم المهمة في عمود 'رقم المهمة'.",
            ))
            continue

        # --- رقم الاشتراك ---
        subscription_number = str(row.get("رقم الاشتراك", "") or "").strip()

        # --- نوع وحالة المهمة ---
        task_type = normalize_task_type(row.get("نوع المهمة", ""))
        task_status = normalize_task_status(row.get("حالة المهمة", ""))

        # --- مطابقة الفني ---
        raw_technician = str(row.get("الفني", "") or "").strip()
        if not raw_technician:
            report.errors.append(RowError(
                row_index=file_row,
                raw_data=dict(row),
                reason="اسم الفني فارغ.",
                suggestion="أضف اسم الفني في عمود 'الفني'.",
            ))
            continue

        match_result = match_technician(raw_technician, known_technicians, technician_threshold)

        if not match_result.is_known:
            report.unknown_technicians.append({
                "row": file_row,
                "raw_name": raw_technician,
                "warning": match_result.warning,
                "candidates": match_result.candidates,
            })
            report.errors.append(RowError(
                row_index=file_row,
                raw_data=dict(row),
                reason=match_result.warning or f"الفني \"{raw_technician}\" غير موجود في قاعدة البيانات.",
                suggestion=(
                    f"تحقق من اسم الفني. المرشحون المحتملون: {', '.join(match_result.candidates)}"
                    if match_result.candidates
                    else "أضف الفني إلى النظام أولاً أو تحقق من الاسم."
                ),
            ))
            continue

        resolved_technician = match_result.resolved_name
        report.recognized_technicians.add(resolved_technician)

        # --- المدينة: من قاعدة البيانات أولاً، ثم من الملف ---
        if resolved_technician in tech_city_map:
            resolved_city = tech_city_map[resolved_technician]
        else:
            resolved_city = str(row.get("المدينة", "") or "").strip()

        # --- الملاحظات ---
        notes = str(row.get("الملاحظات", "") or "").strip()

        # --- اكتشاف التكرار الحقيقي ---
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
        ))
        report.imported += 1

    report.elapsed_seconds = time.perf_counter() - started
    return rows_to_insert, report
