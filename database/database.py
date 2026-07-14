from difflib import SequenceMatcher
import datetime
import re
import time

import streamlit as st
import psycopg2
import psycopg2.pool
import bcrypt
from psycopg2.extras import RealDictCursor, execute_values

from database.storage import (
    ReportImageNotFoundError,
    delete_report_image,
    download_report_image,
    report_image_url,
    upload_report_image,
)
from config import SETTINGS
from logging_config import get_logger


DATABASE_URL = st.secrets["DATABASE_URL"]
LOGGER = get_logger(__name__)
TASK_COLUMNS = (
    "id, technician, task_number, subscription_number, task_type, task_status, "
    "city, notes, execution_date, created_at, updated_at"
)
ASSIGNED_COLUMNS = (
    "id, technician, task_number, subscription_number, task_type, task_status, "
    "city, notes, assigned_date, assigned_by, created_at, updated_at"
)
CITIES = ["جدة", "مكة"]

# القيم الفعلية المعروفة لنوع وحالة المهمة (تُستخدم في التعرف على الأعمدة بالمحتوى)
TASK_TYPE_VALUES = ["تقني", "زيرا"]
TASK_STATUS_VALUES = ["عائق", "تم الفحص", "مزال"]


TITLE_PREFIXES = ["المهندس", "مهندس", "م.", "الفني", "فني", "الأستاذ", "أ.", "السيد", "eng.", "eng", "mr."]


def _clean_text(value):
    value = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", value)


def normalize_calendar_date(value):
    """Normalize UI/date/string values to a timezone-free ``date`` object."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip().split("T", 1)[0].split(" ", 1)[0]
    try:
        year, month, day = (int(part) for part in text.split("-"))
        return datetime.date(year, month, day)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid calendar date: {value!r}") from exc


def _text_tokens(value):
    return [token for token in value.split(" ") if token]


def _normalize_person_name(name):
    n = _clean_text(name)
    for prefix in TITLE_PREFIXES:
        p = prefix.lower()
        if n == p:
            return ""
        if n.startswith(p + " "):
            n = n[len(p):].strip()
    return n


def resolve_known_technician(raw_name, known_names, threshold=0.85):
    """Fuzzy-match an imported technician name against the list of
    technician names already known to the system, so near-identical
    spellings ("هاني" / "هاني صلاح" / "م. هاني صلاح" / مسافات إضافية /
    اختلاف بسيط في الكتابة) resolve to the same existing technician
    instead of creating a new distinct name. If nothing matches well
    enough, the original name is returned as-is.
    """
    raw_name = str(raw_name or "").strip()
    if not raw_name:
        return raw_name
    normalized_raw = _normalize_person_name(raw_name)
    best_name, best_score = raw_name, 0.0
    for known in known_names:
        known = str(known or "").strip()
        if not known:
            continue
        score = _fuzzy_ratio(normalized_raw, _normalize_person_name(known))
        if score > best_score:
            best_score = score
            best_name = known
    return best_name if best_score >= threshold else raw_name


COLUMN_SYNONYMS = {
    "الفني": ["الفني", "اسم الفني", "الموظف", "technician", "employee", "engineer"],
    "رقم المهمة": ["رقم المهمة", "المهمة", "task number", "task", "رقم أمر العمل", "work order", "order number"],
    "رقم الاشتراك": ["رقم الاشتراك", "الاشتراك", "subscription", "subscription number"],
    "نوع المهمة": ["نوع المهمة", "النوع", "task type", "type"],
    "حالة المهمة": ["حالة المهمة", "الحالة", "task status", "status"],
    "المدينة": ["المدينة", "city"],
    "الملاحظات": ["الملاحظات", "ملاحظات", "notes", "note"],
}

# أعمدة يمكن التعرف عليها من خلال محتواها إذا فشلت المطابقة بالاسم
CONTENT_BASED_COLUMNS = {
    "نوع المهمة": TASK_TYPE_VALUES,
    "حالة المهمة": TASK_STATUS_VALUES,
}


def _column_content_match_ratio(values, known_values):
    cleaned = [_clean_text(v) for v in values]
    cleaned = [v for v in cleaned if v]
    if not cleaned:
        return 0.0
    matched = 0
    for value in cleaned:
        best = max(_fuzzy_ratio(value, known) for known in known_values)
        if best >= 0.8:
            matched += 1
    return matched / len(cleaned)


def resolve_column_mapping(columns, dataframe=None, threshold=0.8):
    """Map arbitrary Excel column headers to the canonical column names
    already used across the app (e.g. "Task Number" / "المهمة" -> "رقم المهمة"),
    based on meaning rather than exact spelling. If a column's name isn't
    recognized but its actual values match a known set (e.g. a column
    named "الإفادة" containing only "تقني"/"زيرا"), it is still mapped
    based on that content.
    """
    mapping = {}
    used_targets = set()
    for column in columns:
        column_norm = _clean_text(column)
        best_target, best_score = None, 0.0
        for target, synonyms in COLUMN_SYNONYMS.items():
            for synonym in synonyms:
                synonym_norm = _clean_text(synonym)
                score = 1.0 if column_norm == synonym_norm else _fuzzy_ratio(column_norm, synonym_norm)
                if score > best_score:
                    best_target, best_score = target, score
            if best_score == 1.0:
                break
        if best_target and best_score >= threshold:
            mapping[column] = best_target
            used_targets.add(best_target)

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


def _invalidate_cache():
    """Clear cached read results after any write so data stays correct
    while still benefiting from caching on repeated reads."""
    get_all_users.clear()
    get_all_materials.clear()
    get_all_tasks.clear()
    search_tasks.clear()
    _search_by_field.clear()
    _search_assigned_tasks_cached.clear()
    _search_completed_tasks_cached.clear()
    daily_report_exists.clear()
    get_daily_report.clear()
    get_daily_report_image_bytes.clear()
    get_system_counts.clear()
    get_tasks_breakdown.clear()
    get_security_overview.clear()
    get_audit_log.clear()
    get_error_log.clear()
    get_database_info.clear()


def _fuzzy_ratio(a, b):
    a = _clean_text(a)
    b = _clean_text(b)
    if not a or not b:
        return 0.0
    if a == b or a in b or b in a:
        return 1.0
    a_tokens, b_tokens = _text_tokens(a), _text_tokens(b)
    if a_tokens and b_tokens:
        shorter, longer = (a_tokens, b_tokens) if len(a_tokens) <= len(b_tokens) else (b_tokens, a_tokens)
        if all(
            any(token == other or SequenceMatcher(None, token, other).ratio() >= 0.82 for other in longer)
            for token in shorter
        ):
            return 0.95
    return SequenceMatcher(None, a, b).ratio()


def _fuzzy_match_rows(rows, keyword, fields, threshold=0.6):
    """Approximate (typo-tolerant) matching used only as a fallback when
    an exact ILIKE search finds nothing, so exact-match behavior is
    unchanged and this only adds extra results in the "no match" case."""
    keyword = str(keyword or "").strip()
    if not keyword:
        return []
    scored = []
    for row in rows:
        best = 0.0
        for field in fields:
            best = max(best, _fuzzy_ratio(keyword, row.get(field)))
        if best >= threshold:
            scored.append((best, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored]


@st.cache_resource(show_spinner=False)
def _connection_pool():
    # اتصال مُعاد استخدامه بدل فتح اتصال TCP/TLS جديد بكل استعلام
    # (ThreadedConnectionPool لأن Streamlit يخدم كل جلسة مستخدم في Thread خاص بها)
    return psycopg2.pool.ThreadedConnectionPool(
        SETTINGS.database_pool_min_connections,
        SETTINGS.database_pool_max_connections,
        dsn=DATABASE_URL,
        cursor_factory=RealDictCursor,
    )


def get_connection():
    return _connection_pool().getconn()


def _release_connection(conn):
    try:
        _connection_pool().putconn(conn)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


_QUERY_STATS = {"count": 0, "total_ms": 0.0, "slowest": []}  # slowest: [(ms, query_snippet)], newest-bounded


def _record_query_stat(query, elapsed_ms):
    _QUERY_STATS["count"] += 1
    _QUERY_STATS["total_ms"] += elapsed_ms
    snippet = " ".join(query.split())[:120]
    _QUERY_STATS["slowest"].append((elapsed_ms, snippet))
    _QUERY_STATS["slowest"].sort(key=lambda item: item[0], reverse=True)
    del _QUERY_STATS["slowest"][10:]


def get_query_stats():
    """إحصاءات أداء خفيفة الوزن (في الذاكرة، بلا أي تكلفة على قاعدة البيانات)
    تُستخدم في تبويبي الأداء ومساعد المطور بمركز المطور."""
    count = _QUERY_STATS["count"]
    avg_ms = (_QUERY_STATS["total_ms"] / count) if count else 0.0
    return {"count": count, "avg_ms": avg_ms, "slowest": list(_QUERY_STATS["slowest"])}


def _with_connection(action):
    """Run `action(conn)` using a pooled connection. If the pooled
    connection turned out to be stale (e.g. closed by the server after
    being idle), the pool is reset and the action retried once with a
    fresh connection, so pooling for speed doesn't introduce errors."""
    attempts = 0
    last_error = None
    while attempts < 2:
        conn = get_connection()
        try:
            result = action(conn)
            _release_connection(conn)
            return result
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
            last_error = exc
            try:
                conn.close()
            except Exception:
                pass
            _connection_pool.clear()
            attempts += 1
        except Exception:
            _release_connection(conn)
            raise
    raise last_error


def execute(query, params=()):
    def _action(conn):
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()

    started = time.perf_counter()
    try:
        _with_connection(_action)
    finally:
        _record_query_stat(query, (time.perf_counter() - started) * 1000)


def fetch_one(query, params=()):
    def _action(conn):
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        cur.close()
        return row

    started = time.perf_counter()
    try:
        return _with_connection(_action)
    finally:
        _record_query_stat(query, (time.perf_counter() - started) * 1000)


def fetch_all(query, params=()):
    def _action(conn):
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        return rows

    started = time.perf_counter()
    try:
        return _with_connection(_action)
    finally:
        _record_query_stat(query, (time.perf_counter() - started) * 1000)


def hash_password(password):
    """يُنتج hash آمناً (bcrypt) لكلمة مرور نصية عادية."""
    return bcrypt.hashpw((password or "").encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, hashed):
    """يقارن كلمة مرور نصية بـ hash محفوظ. يُعيد False بأمان لأي قيمة غير صالحة
    بدل رفع استثناء (مثلاً كلمة مرور قديمة غير مشفّرة قبل انتهاء الـ Migration)."""
    if not hashed:
        return False
    try:
        return bcrypt.checkpw((password or "").encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def is_password_strong(password):
    """قواعد بسيطة وواضحة لمنع كلمات المرور الضعيفة عند الإنشاء أو التغيير."""
    password = password or ""
    if len(password) < 8:
        return False, "يجب ألا تقل كلمة المرور عن 8 أحرف."
    if password.isdigit():
        return False, "لا يمكن أن تتكون كلمة المرور من أرقام فقط."
    if password.lower() in {"password", "12345678", "qwertyui", "11111111", "abcdefgh"}:
        return False, "كلمة المرور شائعة جداً وضعيفة، اختر كلمة مرور أقوى."
    return True, ""


def create_tables():
    """Create tables if missing and migrate existing tables with any
    new columns required. Never drops tables or data - only additive
    ALTER TABLE ... ADD COLUMN IF NOT EXISTS migrations are used."""
    conn = get_connection()
    cur = conn.cursor()

    # --- base tables (created only if they don't already exist) ---
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fullname TEXT NOT NULL,
            role TEXT NOT NULL,
            city TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            technician TEXT NOT NULL,
            task_number TEXT NOT NULL,
            subscription_number TEXT NOT NULL,
            task_type TEXT NOT NULL,
            task_status TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --- إسناد المهام / المهام اليومية: جداول جديدة إضافية فقط ---
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS assigned_tasks (
            id SERIAL PRIMARY KEY,
            technician TEXT NOT NULL,
            task_number TEXT NOT NULL,
            subscription_number TEXT NOT NULL,
            task_type TEXT NOT NULL,
            task_status TEXT NOT NULL,
            city TEXT,
            notes TEXT,
            assigned_date DATE NOT NULL,
            assigned_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_reports (
            id SERIAL PRIMARY KEY,
            technician TEXT NOT NULL,
            report_date DATE NOT NULL,
            image_data BYTEA,
            image_mime TEXT NOT NULL,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            UNIQUE (technician, report_date)
        )
        """
    )

    # --- migrations: add any missing columns without touching existing data ---
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS city TEXT")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_attempts INTEGER DEFAULT 0")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP")

    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS city TEXT")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS notes TEXT")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS execution_date DATE")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS created_by TEXT")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS updated_by TEXT")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP")

    cur.execute("ALTER TABLE materials ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    cur.execute("ALTER TABLE materials ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP")
    cur.execute("ALTER TABLE assigned_tasks ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP")
    cur.execute("ALTER TABLE daily_reports ADD COLUMN IF NOT EXISTS image_url TEXT")
    cur.execute("ALTER TABLE daily_reports ALTER COLUMN image_data DROP NOT NULL")

    # سجل العمليات وسجل الأخطاء (جداول إضافية جديدة فقط، لا تمس أي جدول قائم)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            username TEXT,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS error_log (
            id SERIAL PRIMARY KEY,
            error_type TEXT,
            file_name TEXT,
            function_name TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # المهام اليومية يجب أن تعتمد بالكامل على execution_date بدون أي احتياج
    # لـ created_at كـ fallback. نُعبّئ السجلات القديمة (قبل إضافة العمود) مرة
    # واحدة فقط، حتى يصبح فهرس execution_date قابلاً للاستخدام مباشرة في البحث.
    cur.execute("UPDATE tasks SET execution_date = created_at::date WHERE execution_date IS NULL")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_task_number ON tasks(task_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_subscription_number ON tasks(subscription_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_type_status ON tasks(task_type, task_status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_city ON tasks(city)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_execution_date ON tasks(execution_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_technician_execution ON tasks(technician, execution_date)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_assigned_tasks_technician_date ON assigned_tasks(technician, assigned_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_assigned_tasks_task_number ON assigned_tasks(task_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_reports_technician_date ON daily_reports(technician, report_date)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_username ON audit_log(username)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_error_log_created_at ON error_log(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_reports_image_url ON daily_reports(image_url) WHERE image_url IS NOT NULL")

    # Trigram indexes make the existing ILIKE search scale to large task
    # tables.  The extension is optional in managed PostgreSQL deployments,
    # so a permission failure must not prevent the application from starting.
    cur.execute("SAVEPOINT optional_trigram")
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_task_number_trgm ON tasks USING GIN (task_number gin_trgm_ops)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_subscription_number_trgm ON tasks USING GIN (subscription_number gin_trgm_ops)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_technician_trgm ON tasks USING GIN (technician gin_trgm_ops)")
    except psycopg2.Error:
        cur.execute("ROLLBACK TO SAVEPOINT optional_trigram")
        LOGGER.warning("pg_trgm is unavailable; ILIKE search will use the standard indexes.")
    finally:
        cur.execute("RELEASE SAVEPOINT optional_trigram")

    # Add database-level duplicate protection only when legacy data is
    # already clean.  Existing records are never deleted or changed merely
    # to create a constraint.
    cur.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM tasks GROUP BY task_number HAVING COUNT(*) > 1) THEN
                CREATE UNIQUE INDEX IF NOT EXISTS uq_tasks_task_number ON tasks(task_number);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM assigned_tasks GROUP BY task_number HAVING COUNT(*) > 1) THEN
                CREATE UNIQUE INDEX IF NOT EXISTS uq_assigned_tasks_task_number ON assigned_tasks(task_number);
            END IF;
        END $$;
        """
    )

    # Migration لمرة واحدة: تشفير أي كلمات مرور قديمة لا تزال نصاً عادياً
    # (كلمات مرور bcrypt تبدأ دائماً بـ $2). لا تُفقَد بيانات أي مستخدم، ولا
    # يتعطل تسجيل الدخول لاحقاً لأن login_user يتحقق عبر verify_password.
    cur.execute("SELECT id, password FROM users WHERE password IS NOT NULL AND password NOT LIKE '$2%'")
    plaintext_users = cur.fetchall()
    for u in plaintext_users:
        new_hash = bcrypt.hashpw(u["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, u["id"]))

    conn.commit()
    cur.close()
    _release_connection(conn)


def login_user(username, password):
    """يتحقق من بيانات الدخول عبر bcrypt، مع قفل الحساب تلقائياً بعد 5 محاولات
    فاشلة متتالية لمدة 15 دقيقة. يُعيد قاموساً موحداً دائماً:
    - {"ok": True, "user": {...}} عند نجاح الدخول
    - {"ok": False, "locked": True, "locked_until": <datetime>} إذا كان الحساب مقفلاً
    - {"ok": False, "locked": False} لبيانات دخول خاطئة أو مستخدم غير موجود
    """
    username = (username or "").strip()
    user = fetch_one(
        """
        SELECT id, username, password, fullname, role, city, failed_attempts, locked_until
        FROM users WHERE username = %s
        """,
        (username,),
    )
    if not user:
        return {"ok": False, "locked": False}

    now = datetime.datetime.now()
    locked_until = user.get("locked_until")
    if locked_until and locked_until > now:
        return {"ok": False, "locked": True, "locked_until": locked_until}

    if not verify_password(password, user["password"]):
        attempts = (user.get("failed_attempts") or 0) + 1
        new_locked_until = (
            now + datetime.timedelta(minutes=SETTINGS.account_lock_minutes)
            if attempts >= SETTINGS.max_login_attempts else None
        )
        execute(
            "UPDATE users SET failed_attempts = %s, locked_until = %s WHERE id = %s",
            (attempts, new_locked_until, user["id"]),
        )
        _invalidate_cache()
        if new_locked_until:
            return {"ok": False, "locked": True, "locked_until": new_locked_until}
        return {"ok": False, "locked": False}

    execute(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP WHERE id = %s",
        (user["id"],),
    )
    _invalidate_cache()
    return {
        "ok": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "fullname": user["fullname"],
            "role": user["role"],
            "city": user["city"],
        },
    }


def check_current_password(username, current_password):
    user = fetch_one("SELECT password FROM users WHERE username = %s", (username,))
    return bool(user) and verify_password(current_password, user["password"])


def add_user(username, password, fullname, role, city=""):
    execute(
        """
        INSERT INTO users (username, password, fullname, role, city)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username.strip(), hash_password(password.strip()), fullname.strip(), role, (city or "").strip()),
    )
    _invalidate_cache()


def delete_user(user_id):
    execute("DELETE FROM users WHERE id = %s", (int(user_id),))
    _invalidate_cache()


@st.cache_data(ttl=SETTINGS.cache_ttl_reference_seconds, show_spinner=False)
def get_all_users():
    return fetch_all(
        """
        SELECT id, username, fullname, role, city, created_at
        FROM users
        ORDER BY fullname
        """
    )


def change_password(username, new_password):
    execute(
        "UPDATE users SET password = %s WHERE username = %s",
        (hash_password(new_password), username),
    )
    _invalidate_cache()


def update_user(user_id, fullname, password, role, city=None):
    if password and city is not None:
        execute(
            """
            UPDATE users
            SET fullname = %s, password = %s, role = %s, city = %s
            WHERE id = %s
            """,
            (fullname.strip(), hash_password(password.strip()), role, city, int(user_id)),
        )
        _invalidate_cache()
        return
    if password:
        execute(
            """
            UPDATE users
            SET fullname = %s, password = %s, role = %s
            WHERE id = %s
            """,
            (fullname.strip(), hash_password(password.strip()), role, int(user_id)),
        )
        _invalidate_cache()
        return
    if city is not None:
        execute(
            """
            UPDATE users
            SET fullname = %s, role = %s, city = %s
            WHERE id = %s
            """,
            (fullname.strip(), role, city, int(user_id)),
        )
        _invalidate_cache()
        return
    execute(
        """
        UPDATE users
        SET fullname = %s, role = %s
        WHERE id = %s
        """,
        (fullname.strip(), role, int(user_id)),
    )
    _invalidate_cache()


def task_exists(task_number, exclude_id=None):
    if exclude_id:
        return fetch_one(
            "SELECT id FROM tasks WHERE task_number = %s AND id <> %s",
            (task_number.strip(), int(exclude_id)),
        ) is not None
    return fetch_one(
        "SELECT id FROM tasks WHERE task_number = %s",
        (task_number.strip(),),
    ) is not None


def add_task(technician, task_number, subscription_number, task_type, task_status, city="", notes="", execution_date=None):
    # يُحسب تاريخ التنفيذ بلغة Python (نفس مصدر التاريخ المستخدم في اختيار
    # اليوم/الشهر/السنة بالواجهة) بدل الاعتماد على CURRENT_DATE في قاعدة
    # البيانات، لتفادي أي فارق توقيت بين خادم القاعدة والتطبيق يمنع ظهور
    # المهمة في نفس اليوم داخل صفحة المهام اليومية.
    execution_date = normalize_calendar_date(execution_date) or datetime.date.today()
    execute(
        """
        INSERT INTO tasks (technician, task_number, subscription_number, task_type, task_status, city, notes, execution_date, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            technician.strip(),
            task_number.strip(),
            subscription_number.strip(),
            task_type,
            task_status,
            (city or "").strip(),
            (notes or "").strip(),
            execution_date,
        ),
    )
    _invalidate_cache()


def bulk_add_tasks(rows):
    """إدراج جماعي دفعة واحدة (INSERT متعدد الصفوف) بدل استعلام منفصل لكل
    مهمة، لتسريع استيراد ملفات Excel الكبيرة بشكل ملحوظ. rows: قائمة tuples
    بالترتيب: (technician, task_number, subscription_number, task_type,
    task_status, city, notes, execution_date)."""
    if not rows:
        return

    def _action(conn):
        cur = conn.cursor()
        execute_values(
            cur,
            """
            INSERT INTO tasks
                (technician, task_number, subscription_number, task_type, task_status, city, notes, execution_date, created_at, updated_at)
            VALUES %s
            """,
            rows,
            template="(%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        )
        conn.commit()
        cur.close()

    _with_connection(_action)
    _invalidate_cache()


def update_task(task_id, task_number, subscription_number, task_type, task_status, city=None, notes=None):
    if city is not None or notes is not None:
        execute(
            """
            UPDATE tasks
            SET task_number = %s,
                subscription_number = %s,
                task_type = %s,
                task_status = %s,
                city = COALESCE(%s, city),
                notes = COALESCE(%s, notes),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                task_number.strip(),
                subscription_number.strip(),
                task_type,
                task_status,
                city,
                notes,
                int(task_id),
            ),
        )
        _invalidate_cache()
        return
    execute(
        """
        UPDATE tasks
        SET task_number = %s,
            subscription_number = %s,
            task_type = %s,
            task_status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (
            task_number.strip(),
            subscription_number.strip(),
            task_type,
            task_status,
            int(task_id),
        ),
    )
    _invalidate_cache()


def delete_task(task_id):
    execute("DELETE FROM tasks WHERE id = %s", (int(task_id),))
    _invalidate_cache()


def delete_tasks(task_ids):
    execute(
        "DELETE FROM tasks WHERE id = ANY(%s)",
        (list(map(int, task_ids)),),
    )
    _invalidate_cache()


@st.cache_data(ttl=SETTINGS.cache_ttl_search_seconds, show_spinner=False)
def get_all_tasks():
    return fetch_all(f"SELECT {TASK_COLUMNS} FROM tasks ORDER BY id DESC")


def _task_filter_clause(technician="", task_type="", task_status="", city=""):
    clauses = []
    params = []
    if technician and technician != "الكل":
        clauses.append("technician = %s")
        params.append(technician)
    if task_type and task_type != "الكل":
        clauses.append("task_type = %s")
        params.append(task_type)
    if task_status and task_status != "الكل":
        clauses.append("task_status = %s")
        params.append(task_status)
    if city and city != "الكل":
        clauses.append("city = %s")
        params.append(city)
    return clauses, params


@st.cache_data(ttl=SETTINGS.cache_ttl_search_seconds, show_spinner=False)
def _search_by_field(field, keyword, technician="", task_type="", task_status="", city="", limit=None):
    clauses, params = _task_filter_clause(technician, task_type, task_status, city)
    clauses.append(f"{field} ILIKE %s")
    params.append(f"%{keyword.strip()}%")
    query = f"SELECT {TASK_COLUMNS} FROM tasks WHERE {' AND '.join(clauses)} ORDER BY id DESC"
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    return fetch_all(query, params)


@st.cache_data(ttl=SETTINGS.cache_ttl_search_seconds, show_spinner=False)
def search_tasks(keyword="", technician="", task_type="", task_status="", city=""):
    """Sequential smart search.

    When a keyword is supplied it is tried, in order, against:
    رقم المهمة -> رقم الاشتراك -> نوع المهمة -> حالة المهمة -> اسم الفني
    The first field that returns an exact (ILIKE) match wins - this exact
    behavior is unchanged. Only if none of those fields match anything at
    all does an approximate/typo-tolerant fallback search run, so smart
    (fuzzy) matches now show up instead of "no results" when the user's
    spelling is slightly off.
    """
    keyword = keyword.strip()
    if keyword:
        for field in ["task_number", "subscription_number", "task_type", "task_status", "technician"]:
            rows = _search_by_field(field, keyword, technician, task_type, task_status, city)
            if rows:
                return rows

        # لا يوجد تطابق حرفي: جرّب بحثاً ذكياً (تقريبياً) بدل إظهار نتيجة فارغة
        clauses, params = _task_filter_clause(technician, task_type, task_status, city)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        candidate_rows = fetch_all(f"SELECT {TASK_COLUMNS} FROM tasks {where} ORDER BY id DESC", params)
        return _fuzzy_match_rows(
            candidate_rows,
            keyword,
            ["task_number", "subscription_number", "task_type", "task_status", "technician", "city"],
        )

    clauses, params = _task_filter_clause(technician, task_type, task_status, city)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return fetch_all(f"SELECT {TASK_COLUMNS} FROM tasks {where} ORDER BY id DESC", params)


def material_exists(name, exclude_id=None):
    if exclude_id:
        return fetch_one(
            "SELECT id FROM materials WHERE LOWER(name) = LOWER(%s) AND id <> %s",
            (name.strip(), int(exclude_id)),
        ) is not None
    return fetch_one(
        "SELECT id FROM materials WHERE LOWER(name) = LOWER(%s)",
        (name.strip(),),
    ) is not None


def add_material(name, quantity, unit, notes):
    execute(
        """
        INSERT INTO materials (name, quantity, unit, notes)
        VALUES (%s, %s, %s, %s)
        """,
        (name.strip(), int(quantity), unit, notes.strip()),
    )
    _invalidate_cache()


@st.cache_data(ttl=SETTINGS.cache_ttl_reference_seconds, show_spinner=False)
def get_all_materials():
    return fetch_all("SELECT * FROM materials ORDER BY name")


def update_material(material_id, name, unit, notes):
    execute(
        """
        UPDATE materials
        SET name = %s, unit = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (name.strip(), unit, notes.strip(), int(material_id)),
    )
    _invalidate_cache()


def increase_material(material_id, quantity):
    execute(
        """
        UPDATE materials
        SET quantity = quantity + %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (int(quantity), int(material_id)),
    )
    _invalidate_cache()


def decrease_material(material_id, quantity):
    material = fetch_one("SELECT quantity FROM materials WHERE id = %s", (int(material_id),))
    if not material or int(material["quantity"]) < int(quantity):
        return False
    execute(
        """
        UPDATE materials
        SET quantity = quantity - %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (int(quantity), int(material_id)),
    )
    _invalidate_cache()
    return True


def delete_material(material_id):
    execute("DELETE FROM materials WHERE id = %s", (int(material_id),))
    _invalidate_cache()


# =========================================================
# إسناد المهام (assigned_tasks)
# =========================================================

def _assigned_task_filter_clause(technician="", assigned_date=None):
    clauses = []
    params = []
    if technician and technician != "الكل":
        clauses.append("technician = %s")
        params.append(technician)
    if assigned_date:
        clauses.append("assigned_date = %s")
        params.append(assigned_date)
    return clauses, params


def assigned_task_number_exists(task_number):
    """يمنع إسناد نفس رقم المهمة مرتين، سواء كان لا يزال مسنداً أو تم تنفيذه بالفعل."""
    task_number = task_number.strip()
    if fetch_one("SELECT id FROM assigned_tasks WHERE task_number = %s", (task_number,)):
        return True
    return fetch_one("SELECT id FROM tasks WHERE task_number = %s", (task_number,)) is not None


def assign_task(technician, task_number, subscription_number, assigned_date=None, task_type="تقني", task_status="عائق", city="", notes="", assigned_by=""):
    # المدير لم يعد يختار نوع/حالة/تاريخ المهمة، لذا لها قيم افتراضية معقولة
    # (نفس الافتراضات المستخدمة أصلاً عند استيراد Excel بدون هذه الأعمدة)
    assigned_date = normalize_calendar_date(assigned_date) or datetime.date.today()
    execute(
        """
        INSERT INTO assigned_tasks
            (technician, task_number, subscription_number, task_type, task_status, city, notes, assigned_date, assigned_by, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            technician.strip(),
            task_number.strip(),
            subscription_number.strip(),
            task_type,
            task_status,
            (city or "").strip(),
            (notes or "").strip(),
            assigned_date,
            (assigned_by or "").strip(),
        ),
    )
    _invalidate_cache()


def get_assigned_task_by_number(technician, task_number):
    """يُستخدم في صفحة الفني لمعرفة إن كانت المهمة المسجَّلة موجودة أصلاً ضمن مهامه المسندة."""
    return fetch_one(
        f"SELECT {ASSIGNED_COLUMNS} FROM assigned_tasks WHERE technician = %s AND task_number = %s",
        (technician.strip(), task_number.strip()),
    )


def complete_assigned_task(assigned_id, subscription_number=None, task_type=None, task_status=None, notes=None, city=None, execution_date=None):
    """ينقل مهمة واحدة من جدول المهام المسندة إلى جدول المهام المنفذة بشكل ذري
    (بنفس الاتصال)، ويسجل تاريخ التنفيذ، حتى لا يختل تطابق الجدولين أبداً."""
    execution_date = normalize_calendar_date(execution_date) or datetime.date.today()

    def _action(conn):
        cur = conn.cursor()
        cur.execute(f"SELECT {ASSIGNED_COLUMNS} FROM assigned_tasks WHERE id = %s", (int(assigned_id),))
        row = cur.fetchone()
        if not row:
            cur.close()
            return False
        final_subscription = (subscription_number or row["subscription_number"]).strip()
        final_type = task_type or row["task_type"]
        final_status = task_status or row["task_status"]
        final_notes = notes if notes is not None else (row.get("notes") or "")
        final_city = city if city is not None else (row.get("city") or "")
        cur.execute(
            """
            INSERT INTO tasks (technician, task_number, subscription_number, task_type, task_status, city, notes, execution_date, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (row["technician"], row["task_number"], final_subscription, final_type, final_status, final_city, final_notes, execution_date),
        )
        cur.execute("DELETE FROM assigned_tasks WHERE id = %s", (int(assigned_id),))
        conn.commit()
        cur.close()
        return True

    result = _with_connection(_action)
    if result:
        _invalidate_cache()
    return result


@st.cache_data(ttl=SETTINGS.cache_ttl_search_seconds, show_spinner=False)
def _search_assigned_tasks_cached(technician, assigned_date):
    clauses, params = _assigned_task_filter_clause(technician, assigned_date)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return fetch_all(f"SELECT {ASSIGNED_COLUMNS} FROM assigned_tasks {where} ORDER BY id DESC", params)


def search_assigned_tasks(technician="", assigned_date=None):
    """Search assigned tasks using one normalized, timezone-free cache key."""
    return _search_assigned_tasks_cached(technician, normalize_calendar_date(assigned_date))


# اسم بديل مطلوب لنفس الوظيفة (عرض المهام المسندة حسب الفني/التاريخ)
get_assigned_tasks = search_assigned_tasks


# =========================================================
# المهام اليومية / المهام المنفذة (تُقرأ من جدول tasks الحالي)
# =========================================================

@st.cache_data(ttl=SETTINGS.cache_ttl_search_seconds, show_spinner=False)
def _search_completed_tasks_cached(technician, target_date):
    clauses = []
    params = []
    if technician and technician != "الكل":
        clauses.append("technician = %s")
        params.append(technician)
    if target_date:
        clauses.append("execution_date = %s")
        params.append(target_date)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return fetch_all(f"SELECT {TASK_COLUMNS} FROM tasks {where} ORDER BY id DESC", params)


def search_completed_tasks(technician="", target_date=None):
    """Search completed tasks using one normalized, timezone-free cache key."""
    return _search_completed_tasks_cached(technician, normalize_calendar_date(target_date))


# اسم بديل مطلوب لنفس الوظيفة (عرض المهام المنفذة حسب الفني/التاريخ)
get_daily_completed_tasks = search_completed_tasks


# =========================================================
# تقارير المهام (daily_reports)
# =========================================================

@st.cache_data(ttl=SETTINGS.cache_ttl_operational_seconds, show_spinner=False)
def daily_report_exists(technician, report_date):
    return fetch_one(
        "SELECT id FROM daily_reports WHERE technician = %s AND report_date = %s",
        (technician.strip(), report_date),
    ) is not None


@st.cache_data(ttl=SETTINGS.cache_ttl_operational_seconds, show_spinner=False)
def get_daily_report(technician, report_date):
    row = fetch_one(
        """
        SELECT id, technician, report_date, image_data, image_mime, image_url, created_at, updated_at
        FROM daily_reports WHERE technician = %s AND report_date = %s
        """,
        (technician.strip(), report_date),
    )
    if row is None:
        return None
    # psycopg2 يُرجع أعمدة BYTEA كـ memoryview، وهو نوع غير قابل للـ Pickle
    # فيفشل @st.cache_data. نحوّله هنا إلى dict عادي وbytes صريحة قبل التخزين.
    row = dict(row)
    if row.get("image_data") is not None:
        row["image_data"] = bytes(row["image_data"])
    return row


def update_daily_report(report_id, image_url, image_mime, invalidate_cache=True):
    execute(
        """
        UPDATE daily_reports
        SET image_data = NULL, image_url = %s, image_mime = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (image_url, image_mime, int(report_id)),
    )
    if invalidate_cache:
        _invalidate_cache()


def save_daily_report(technician, report_date, image_bytes, image_mime):
    """إضافة تقرير جديد، أو استبدال التقرير الموجود لنفس الفني ونفس التاريخ (تقرير واحد فقط لكل يوم)."""
    existing = fetch_one(
        "SELECT id, image_url FROM daily_reports WHERE technician = %s AND report_date = %s",
        (technician.strip(), report_date),
    )
    object_key = upload_report_image(technician, report_date, image_bytes, image_mime)
    try:
        if existing:
            update_daily_report(existing["id"], object_key, image_mime, invalidate_cache=False)
        else:
            execute(
                """
                INSERT INTO daily_reports (technician, report_date, image_data, image_mime, image_url, created_at, updated_at)
                VALUES (%s, %s, NULL, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (technician.strip(), report_date, image_mime, object_key),
            )
    except Exception:
        # A failed database write must not leave an unreferenced upload.
        try:
            delete_report_image(object_key)
        except Exception:
            LOGGER.exception("Could not remove an unreferenced report upload.")
        raise

    if existing and existing.get("image_url") and existing["image_url"] != object_key:
        try:
            delete_report_image(existing["image_url"])
        except Exception:
            # The new report is already safely committed. Keep serving it and
            # record the cleanup failure for the scheduled orphan sweep.
            LOGGER.exception("Could not remove the replaced report image.")
    _invalidate_cache()


@st.cache_data(ttl=SETTINGS.cache_ttl_operational_seconds, show_spinner=False)
def get_daily_report_image_bytes(object_key):
    """Return the original Storage object bytes for a download button."""
    return download_report_image(object_key)


def daily_report_download_bytes(report):
    """Return original bytes for both Storage-backed and legacy BYTEA reports."""
    if not report:
        return None
    if report.get("image_url"):
        return get_daily_report_image_bytes(report["image_url"])
    return report.get("image_data")


def delete_daily_report(report_id, object_key=None):
    """Delete a report image and its database reference.

    Storage is removed first. A missing Storage object is treated as a stale
    reference and the database row is still removed. Other Storage failures
    stop the operation so the database does not silently lose a valid link.
    """
    storage_was_missing = False
    if object_key:
        try:
            delete_report_image(object_key)
        except ReportImageNotFoundError:
            storage_was_missing = True
    def _delete_reference(conn):
        cur = conn.cursor()
        cur.execute("DELETE FROM daily_reports WHERE id = %s RETURNING id", (int(report_id),))
        deleted = cur.fetchone() is not None
        conn.commit()
        cur.close()
        return deleted

    database_row_deleted = _with_connection(_delete_reference)
    if database_row_deleted:
        _invalidate_cache()
    return {
        "storage_was_missing": storage_was_missing,
        "database_was_missing": not database_row_deleted,
    }


def daily_report_display_source(report):
    """Return a URL for new reports or bytes for legacy BYTEA reports."""
    if report and report.get("image_url"):
        return report_image_url(report["image_url"])
    return report.get("image_data") if report else None


# =========================================================
# سجل العمليات (Audit Log) وسجل الأخطاء (Error Log)
# =========================================================

def log_action(username, action, details="", ip_address=""):
    """تسجيل عملية في سجل العمليات. لا يُفشل أي عملية أساسية أبداً إذا تعذّر
    تسجيلها؛ الأخطاء هنا تُبتلع بصمت بعد محاولة تسجيلها في error_log."""
    try:
        execute(
            """
            INSERT INTO audit_log (username, action, details, ip_address, created_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            ((username or "").strip(), action, (details or "").strip(), (ip_address or "").strip()),
        )
        get_audit_log.clear()
    except Exception as exc:
        log_error("AuditLogError", "database.py", "log_action", str(exc))


@st.cache_data(ttl=SETTINGS.cache_ttl_operational_seconds, show_spinner=False)
def get_audit_log(limit=500):
    return fetch_all(
        "SELECT id, username, action, details, ip_address, created_at FROM audit_log ORDER BY id DESC LIMIT %s",
        (limit,),
    )


def log_error(error_type, file_name, function_name, message):
    """تسجيل خطأ في error_log. مُصمَّمة لعدم رفع أي استثناء بنفسها أبداً حتى
    لا يتسبب فشل تسجيل الخطأ في كسر العملية الأصلية."""
    try:
        execute(
            """
            INSERT INTO error_log (error_type, file_name, function_name, message, created_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            ((error_type or "")[:200], (file_name or "")[:200], (function_name or "")[:200], (message or "")[:2000]),
        )
        get_error_log.clear()
    except Exception:
        pass


@st.cache_data(ttl=SETTINGS.cache_ttl_operational_seconds, show_spinner=False)
def get_error_log(limit=200):
    return fetch_all(
        "SELECT id, error_type, file_name, function_name, message, created_at FROM error_log ORDER BY id DESC LIMIT %s",
        (limit,),
    )


# =========================================================
# مركز المطور: إحصاءات النظام
# =========================================================

@st.cache_data(ttl=SETTINGS.cache_ttl_diagnostics_seconds, show_spinner=False)
def get_system_counts():
    """عدّادات خفيفة لكل الكيانات الرئيسية بقراءة واحدة مجمَّعة لكل جدول،
    بدل تحميل كل الصفوف ثم عدّها في Python (أسرع ويبقى سريعاً مع نمو البيانات)."""
    row = fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM users) AS users,
            (SELECT COUNT(*) FROM users WHERE role = 'admin') AS admins,
            (SELECT COUNT(*) FROM users WHERE role = 'technician') AS technicians,
            (SELECT COUNT(*) FROM tasks) AS tasks,
            (SELECT COUNT(*) FROM assigned_tasks) AS assigned_tasks,
            (SELECT COUNT(*) FROM daily_reports) AS reports,
            (SELECT COUNT(*) FROM materials) AS materials,
            (SELECT COUNT(*) FROM materials WHERE quantity <= 5) AS low_stock_materials
        """
    )
    return dict(row)


@st.cache_data(ttl=SETTINGS.cache_ttl_diagnostics_seconds, show_spinner=False)
def get_tasks_breakdown():
    """توزيع المهام حسب المدينة/الحالة/النوع، باستعلامات GROUP BY مجمَّعة
    (لا تُحمَّل كل صفوف الجدول إلى Python)."""
    return {
        "by_city": fetch_all("SELECT COALESCE(NULLIF(city, ''), 'غير محدد') AS label, COUNT(*) AS n FROM tasks GROUP BY 1 ORDER BY 2 DESC"),
        "by_status": fetch_all("SELECT task_status AS label, COUNT(*) AS n FROM tasks GROUP BY 1 ORDER BY 2 DESC"),
        "by_type": fetch_all("SELECT task_type AS label, COUNT(*) AS n FROM tasks GROUP BY 1 ORDER BY 2 DESC"),
    }


def test_db_connection():
    """اختبار اتصال حي بقاعدة البيانات مع قياس زمن الاستجابة الفعلي. غير
    مخزَّن مؤقتاً عمداً لأنه يجب أن يعكس حالة الاتصال الآن بالضبط."""
    started = time.perf_counter()
    try:
        fetch_one("SELECT 1 AS ok")
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {"connected": True, "response_ms": round(elapsed_ms, 1), "error": None}
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {"connected": False, "response_ms": round(elapsed_ms, 1), "error": str(exc)}


@st.cache_data(ttl=SETTINGS.cache_ttl_reference_seconds, show_spinner=False)
def get_database_info():
    """حجم قاعدة البيانات وإصدار PostgreSQL وعدد الاتصالات النشطة حالياً،
    من دوال PostgreSQL الرسمية الخفيفة الوزن (لا تفحص أي جدول بيانات)."""
    try:
        size_row = fetch_one("SELECT pg_size_pretty(pg_database_size(current_database())) AS size")
        version_row = fetch_one("SHOW server_version")
        connections_row = fetch_one(
            "SELECT COUNT(*) AS n FROM pg_stat_activity WHERE datname = current_database()"
        )
        return {
            "size": size_row["size"] if size_row else "غير متاح",
            "version": version_row["server_version"] if version_row else "غير متاح",
            "active_connections": connections_row["n"] if connections_row else None,
        }
    except Exception:
        return {"size": "غير متاح", "version": "غير متاح", "active_connections": None}


@st.cache_data(ttl=SETTINGS.cache_ttl_operational_seconds, show_spinner=False)
def get_security_overview():
    """نظرة أمنية سريعة لمركز المطور: حسابات مقفلة حالياً، حسابات عليها
    محاولات دخول فاشلة، وآخر عمليات دخول (تُستخدم أيضاً كتقدير لعدد
    المستخدمين المتصلين حالياً عبر آخر تسجيل دخول خلال 15 دقيقة)."""
    now = datetime.datetime.now()
    return {
        "locked": fetch_all(
            "SELECT username, fullname, locked_until FROM users WHERE locked_until IS NOT NULL AND locked_until > %s ORDER BY locked_until DESC",
            (now,),
        ),
        "failed_attempts": fetch_all(
            "SELECT username, fullname, failed_attempts FROM users WHERE failed_attempts > 0 ORDER BY failed_attempts DESC"
        ),
        "recent_logins": fetch_all(
            "SELECT username, fullname, last_login FROM users WHERE last_login IS NOT NULL ORDER BY last_login DESC LIMIT 15"
        ),
        "online_now": fetch_all(
            "SELECT username, fullname, last_login FROM users WHERE last_login IS NOT NULL AND last_login > %s ORDER BY last_login DESC",
            (now - datetime.timedelta(minutes=SETTINGS.online_user_window_minutes),),
        ),
    }


def cleanup_cache():
    """مسح كل الكاش يدوياً من تبويب الصيانة بمركز المطور."""
    _invalidate_cache()
