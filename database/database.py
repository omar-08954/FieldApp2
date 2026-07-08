import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = st.secrets["DATABASE_URL"]
TASK_COLUMNS = "id, technician, task_number, subscription_number, task_type, task_status"


def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def execute(query, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    cur.close()
    conn.close()


def fetch_one(query, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def fetch_all(query, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def create_tables():
    conn = get_connection()
    cur = conn.cursor()
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
    cur.execute("ALTER TABLE materials ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_task_number ON tasks(task_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_subscription_number ON tasks(subscription_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_type_status ON tasks(task_type, task_status)")
    conn.commit()
    cur.close()
    conn.close()


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


def add_user(username, password, fullname, role, city):
    execute(
        """
        INSERT INTO users (username, password, fullname, role, city)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username.strip(), password.strip(), fullname.strip(), role, city),
    )


def delete_user(user_id):
    execute("DELETE FROM users WHERE id = %s", (int(user_id),))


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


def add_task(technician, task_number, subscription_number, task_type, task_status):
    execute(
        """
        INSERT INTO tasks (technician, task_number, subscription_number, task_type, task_status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            technician.strip(),
            task_number.strip(),
            subscription_number.strip(),
            task_type,
            task_status,
        ),
    )


def update_task(task_id, task_number, subscription_number, task_type, task_status):
    execute(
        """
        UPDATE tasks
        SET task_number = %s,
            subscription_number = %s,
            task_type = %s,
            task_status = %s
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


def delete_task(task_id):
    execute("DELETE FROM tasks WHERE id = %s", (int(task_id),))


def get_all_tasks():
    return fetch_all(f"SELECT {TASK_COLUMNS} FROM tasks ORDER BY id DESC")


def _task_filter_clause(technician="", task_type="", task_status=""):
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
    return clauses, params


def _search_by_field(field, keyword, technician="", task_type="", task_status="", limit=None):
    clauses, params = _task_filter_clause(technician, task_type, task_status)
    clauses.append(f"{field} ILIKE %s")
    params.append(f"%{keyword.strip()}%")
    query = f"SELECT {TASK_COLUMNS} FROM tasks WHERE {' AND '.join(clauses)} ORDER BY id DESC"
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    return fetch_all(query, params)


def get_task_by_search(keyword):
    keyword = keyword.strip()
    if not keyword:
        return None
    for field in ["task_number", "subscription_number", "task_type", "task_status"]:
        rows = _search_by_field(field, keyword, limit=1)
        if rows:
            return rows[0]
    return None


def search_tasks(keyword="", technician="", task_type="", task_status=""):
    keyword = keyword.strip()
    if keyword:
        for field in ["task_number", "subscription_number", "task_type", "task_status"]:
            rows = _search_by_field(field, keyword, technician, task_type, task_status)
            if rows:
                return rows
        return []

    clauses, params = _task_filter_clause(technician, task_type, task_status)
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


def increase_material(material_id, quantity):
    execute(
        """
        UPDATE materials
        SET quantity = quantity + %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (int(quantity), int(material_id)),
    )


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
    return True


def delete_material(material_id):
    execute("DELETE FROM materials WHERE id = %s", (int(material_id),))
