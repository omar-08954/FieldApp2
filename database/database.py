from difflib import SequenceMatcher
import re

import streamlit as st
import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor


DATABASE_URL = st.secrets["DATABASE_URL"]
TASK_COLUMNS = (
    "id, technician, task_number, subscription_number, task_type, task_status, "
    "city, notes, created_at, updated_at"
)
CITIES = ["جدة", "مكة"]

# القيم الفعلية المعروفة لنوع وحالة المهمة (تُستخدم في التعرف على الأعمدة بالمحتوى)
TASK_TYPE_VALUES = ["تقني", "زيرا"]
TASK_STATUS_VALUES = ["عائق", "تم الفحص", "مزال"]


TITLE_PREFIXES = ["المهندس", "مهندس", "م.", "الفني", "فني", "الأستاذ", "أ.", "السيد", "eng.", "eng", "mr."]


def _clean_text(value):
    value = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", value)


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
    return psycopg2.pool.ThreadedConnectionPool(1, 10, dsn=DATABASE_URL, cursor_factory=RealDictCursor)


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

    _with_connection(_action)


def fetch_one(query, params=()):
    def _action(conn):
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        cur.close()
        return row

    return _with_connection(_action)


def fetch_all(query, params=()):
    def _action(conn):
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        return rows

    return _with_connection(_action)


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

    # --- migrations: add any missing columns without touching existing data ---
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS city TEXT")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS city TEXT")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS notes TEXT")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")

    cur.execute("ALTER TABLE materials ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_task_number ON tasks(task_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_subscription_number ON tasks(subscription_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_type_status ON tasks(task_type, task_status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_city ON tasks(city)")

    conn.commit()
    cur.close()
    _release_connection(conn)


def login_user(username, password):
    return fetch_one(
        """
        SELECT id, username, fullname, role, city
        FROM users
        WHERE username = %s AND password = %s
        """,
        (username, password),
    )


def check_current_password(username, current_password):
    return fetch_one(
        "SELECT id FROM users WHERE username = %s AND password = %s",
        (username, current_password),
    ) is not None


def add_user(username, password, fullname, role, city=""):
    execute(
        """
        INSERT INTO users (username, password, fullname, role, city)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username.strip(), password.strip(), fullname.strip(), role, (city or "").strip()),
    )
    _invalidate_cache()


def delete_user(user_id):
    execute("DELETE FROM users WHERE id = %s", (int(user_id),))
    _invalidate_cache()


@st.cache_data(ttl=20, show_spinner=False)
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
        (new_password, username),
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
            (fullname.strip(), password.strip(), role, city, int(user_id)),
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
            (fullname.strip(), password.strip(), role, int(user_id)),
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


def add_task(technician, task_number, subscription_number, task_type, task_status, city="", notes=""):
    execute(
        """
        INSERT INTO tasks (technician, task_number, subscription_number, task_type, task_status, city, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            technician.strip(),
            task_number.strip(),
            subscription_number.strip(),
            task_type,
            task_status,
            (city or "").strip(),
            (notes or "").strip(),
        ),
    )
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


@st.cache_data(ttl=20, show_spinner=False)
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


@st.cache_data(ttl=20, show_spinner=False)
def _search_by_field(field, keyword, technician="", task_type="", task_status="", city="", limit=None):
    clauses, params = _task_filter_clause(technician, task_type, task_status, city)
    clauses.append(f"{field} ILIKE %s")
    params.append(f"%{keyword.strip()}%")
    query = f"SELECT {TASK_COLUMNS} FROM tasks WHERE {' AND '.join(clauses)} ORDER BY id DESC"
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    return fetch_all(query, params)


@st.cache_data(ttl=20, show_spinner=False)
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


def create_materials_table():
    create_tables()


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


@st.cache_data(ttl=20, show_spinner=False)
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
